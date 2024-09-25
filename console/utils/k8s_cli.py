import base64
import logging
import subprocess
import yaml
from datetime import datetime
from kubernetes import client, config

logger = logging.getLogger('default')


class K8sClient:
    def __init__(self, kubeconfig_content):
        # 从 kubeconfig 字符串内容加载配置
        self.kube_config = kubeconfig_content
        kubeconfig_dict = yaml.safe_load(kubeconfig_content)
        loader = config.kube_config.KubeConfigLoader(config_dict=kubeconfig_dict)

        # 创建一个空的配置对象
        configuration = client.Configuration()

        # 将配置加载到 Configuration 对象中
        loader.load_and_set(client_configuration=configuration)
        configuration.timeout = 10
        # 跳过证书验证
        configuration.verify_ssl = False

        # 创建 API 客户端
        self.api_client = client.ApiClient(configuration=configuration)
        self.core_v1_api = client.CoreV1Api(api_client=self.api_client)
        self.custom_api = client.CustomObjectsApi(api_client=self.api_client)
        self.storage_v1_api = client.StorageV1Api(api_client=self.api_client)

    def _write_file(self, filename, content):
        """写入文件"""
        try:
            with open(filename, 'w') as f:
                f.write(content)
            logger.info(f"Successfully wrote {filename}")
        except Exception as e:
            error_message = f"Failed to write {filename}: {e}"
            logger.error(error_message)
            raise Exception(error_message)

    def _run_subprocess(self, command_list):
        """运行 subprocess 命令并检查返回码"""
        try:
            result = subprocess.run(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                return result.stdout.decode('utf-8')
            else:
                error_message = f"Command '{' '.join(command_list)}' failed: {result.stderr.decode('utf-8')}"
                logger.error(error_message)
                raise Exception(error_message)
        except Exception as e:
            error_message = f"Error running command '{' '.join(command_list)}': {str(e)}"
            logger.error(error_message)
            raise Exception(error_message)

    def get_nodes(self):
        """获取所有节点的信息"""
        try:
            node_list = self.core_v1_api.list_node()
            nodes_dict = {}
            for node in node_list.items:
                status = self._get_node_status(node)
                name = node.metadata.name
                internal_ip, external_ip = self._get_node_ips(node)
                os_image = node.status.node_info.os_image
                roles = self._get_node_roles(node)
                uptime = self._calculate_uptime(node.metadata.creation_timestamp)
                installation_status = self._get_installation_status(name)
                if installation_status:
                    status = "NotReady"
                nodes_dict[name] = {
                    'status': status,
                    'name': name,
                    'internal_ip': internal_ip,
                    'external_ip': external_ip,
                    'os_image': os_image,
                    'roles': ", ".join(roles),
                    'uptime': uptime,
                    'installation_status': installation_status
                }

            return nodes_dict

        except Exception as e:
            logger.error(f"Failed to retrieve nodes info: {str(e)}")
            return {"error": str(e)}

    def nodes_add_worker_rule(self, nodes):
        """
        为指定的节点增加 worker 标签
        :param nodes: 节点名称列表
        :return: 操作结果
        """
        try:
            results = []
            for node in nodes:
                node_name = node.node_name
                # 准备需要添加的标签，注意标签需要是字典形式
                body = {
                    "metadata": {
                        "labels": {
                            "node-role.kubernetes.io/worker": "true"
                        }
                    }
                }
                # 调用 Kubernetes API 进行节点的标签更新
                self.core_v1_api.patch_node(node_name, body)
                results.append({
                    "node": node_name,
                    "status": "success",
                    "message": f"Worker label added to node {node_name}"
                })
            return results
        except Exception as e:
            logger.error(f"Failed to add worker label to nodes: {str(e)}")
            return {"error": str(e)}

    def _get_node_status(self, node):
        """获取节点状态"""
        status = "Unknown"
        for condition in node.status.conditions:
            if condition.type == "Ready":
                status = "Ready" if condition.status == "True" else "NotReady"
        return status

    def _get_node_ips(self, node):
        """获取节点 IP 地址"""
        internal_ip, external_ip = None, None
        for address in node.status.addresses:
            if address.type == "InternalIP":
                internal_ip = address.address
            elif address.type == "ExternalIP":
                external_ip = address.address
        return internal_ip, external_ip

    def _get_node_roles(self, node):
        """获取节点角色"""
        roles = []
        labels = node.metadata.labels
        if "node-role.kubernetes.io/control-plane" in labels:
            roles.append("control-plane")
        if "node-role.kubernetes.io/etcd" in labels:
            roles.append("etcd")
        if "node-role.kubernetes.io/worker" in labels:
            roles.append("worker")
        if "node-role.kubernetes.io/master" in labels:
            roles.append("master")
        if not roles:
            roles.append("None")
        return roles

    def _calculate_uptime(self, creation_time):
        """计算节点的存活时间"""
        current_time = datetime.now(creation_time.tzinfo)
        return str(current_time - creation_time).split('.')[0]  # 去除微秒部分

    def _get_installation_status(self, node_name):
        """获取节点的安装状态"""
        try:
            pod_list = self.core_v1_api.list_namespaced_pod(namespace="kube-system",
                                                            field_selector=f"spec.nodeName={node_name}")
            no_run_pods = [pod.metadata.name for pod in pod_list.items if pod.status.phase != "Running" and pod.status.phase != "Succeeded"]
            if no_run_pods:
                if len(no_run_pods) > 2:
                    return "Waiting for pod start: {}...".format(",".join(no_run_pods[:2]))
                return "Waiting for pod start: {}".format(",".join(no_run_pods))
            else:
                return ""
        except Exception as e:
            return f"Error retrieving installation status: {str(e)}"

    def install_rainbond(self, values_content):
        """安装 Rainbond"""
        try:
            self._write_file('kube.config', self.kube_config)
            self._write_file('values.yaml', values_content)

            # self._run_subprocess(
            #     ["helm", "repo", "add", "rainbond", "https://openchart.goodrain.com/goodrain/rainbond"])
            # self._run_subprocess(["helm", "repo", "update"])

            self._run_subprocess([
                "helm", "install", "rainbond",
                # "rainbond/rainbond-cluster",
                "./rainbond-chart",
                "-n", "rbd-system",
                "--create-namespace",
                "--kubeconfig", "kube.config",
                "-f", "values.yaml"
            ])
            logger.info("Successfully installed Rainbond using Helm")

        except Exception as e:
            self.uninstall_rainbond()
            return str(e)

    def uninstall_rainbond(self):
        """卸载 Rainbond"""
        try:
            self._run_subprocess([
                "helm", "uninstall", "rainbond",
                "-n", "rbd-system",
                "--kubeconfig", "kube.config"
            ])
            logger.info("Successfully uninstalled Rainbond.")
        except Exception as e:
            logger.error(f"Failed to uninstall Rainbond: {str(e)}")

        # Step 2: Delete PVCs in rbd-system namespace using CoreV1Api
        logger.info("Deleting PVCs in rbd-system namespace...")
        try:
            pvcs = self.core_v1_api.list_namespaced_persistent_volume_claim(namespace="rbd-system")
            for pvc in pvcs.items:
                self.core_v1_api.delete_namespaced_persistent_volume_claim(name=pvc.metadata.name,
                                                                           namespace="rbd-system")
            logger.info("Successfully deleted PVCs.")
        except Exception as e:
            logger.error(f"Failed to delete PVCs: {str(e)}")

        # Step 3: Delete PVs related to rbd-system using CoreV1Api
        logger.info("Deleting PVs related to rbd-system...")
        try:
            pvs = self.core_v1_api.list_persistent_volume()
            for pv in pvs.items:
                if pv.spec.claim_ref and pv.spec.claim_ref.namespace == "rbd-system":
                    self.core_v1_api.delete_persistent_volume(name=pv.metadata.name)
            logger.info("Successfully deleted PVs.")
        except Exception as e:
            logger.error(f"Failed to delete PVs: {str(e)}")

        # Step 4: Delete CRDs related to Rainbond using CustomObjectsApi
        logger.info("Deleting Rainbond-related CRDs...")
        crds = [
            "componentdefinitions.rainbond.io",
            "helmapps.rainbond.io",
            "rainbondclusters.rainbond.io",
            "rainbondpackages.rainbond.io",
            "rainbondvolumes.rainbond.io",
            "rbdcomponents.rainbond.io",
            "servicemonitors.monitoring.coreos.com",
            "thirdcomponents.rainbond.io",
            "rbdabilities.rainbond.io",
            "rbdplugins.rainbond.io",
            "servicemeshclasses.rainbond.io",
            "servicemeshes.rainbond.io"
        ]
        for crd in crds:
            try:
                self.custom_api.delete_cluster_custom_object(
                    group="apiextensions.k8s.io", version="v1", plural="customresourcedefinitions", name=crd
                )
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    logger.warning(f"CRD {crd} not found.")
                else:
                    logger.error(f"Failed to delete CRD {crd}: {str(e)}")

        logger.info("Successfully deleted CRDs.")

    def rb_components_status(self):
        """获取命名空间 `rbd-system` 中所有相关服务的状态"""
        try:
            pod_list = self.core_v1_api.list_namespaced_pod(namespace="rbd-system")
            services = [
                "minio", "local-path-provisioner", "rainbond-operator", "rbd-gateway", "rbd-api", "rbd-chaos", "rbd-db", "rbd-eventlog",
                "rbd-hub", "rbd-monitor", "rbd-mq", "rbd-worker"
            ]

            service_status = {service: [] for service in services}
            rb_installed = True
            for pod in pod_list.items:
                for service in services:
                    if pod.metadata.name.startswith(service):
                        pod_info = self._get_pod_info(pod)
                        service_status[service].append(pod_info)
                        if pod_info.get("status") != "Running":
                            rb_installed = False

            # 对没有找到的服务，填充"不存在"的状态
            for service in services:
                if not service_status[service]:
                    rb_installed = False
                    service_status[service].append(self._get_missing_service_status())
            return service_status, rb_installed

        except Exception as e:
            logger.error(f"Failed to retrieve services status: {str(e)}")
            return {"error": str(e)}

    def _get_pod_info(self, pod):
        """获取 Pod 的信息"""
        container_statuses = pod.status.container_statuses or []
        container_detailed_status = pod.status.phase  # Default status if no issues
        for container_status in container_statuses:
            state = container_status.state
            if state.waiting and state.waiting.reason:
                container_detailed_status = state.waiting.reason
                break
            elif state.terminated and state.terminated.reason:
                container_detailed_status = state.terminated.reason
                break
            elif state.running:
                container_detailed_status = "Running"

        if pod.status.container_statuses:
            container_status = pod.status.container_statuses[0]
            image = container_status.image
            image_status = "正常" if image else "镜像缺失"
        else:
            image = ""
            image_status = "镜像缺失"

        return {
            "pod_name": pod.metadata.name,
            "status": container_detailed_status,
            "node": pod.spec.node_name,
            "start_time": str(pod.status.start_time) if pod.status.start_time else "",
            "restarts": pod.status.container_statuses[0].restart_count if pod.status.container_statuses else 0,
            "image": image,
            "image_status": image_status
        }

    def _get_missing_service_status(self):
        """返回服务不存在的状态"""
        return {
            "pod_name": "",
            "status": "UnExist",
            "node_name": "",
            "start_time": "",
            "restarts": 0,
            "image": "",
            "image_status": "不存在"
        }

    def rb_component_event(self, component_name):
        """获取单个服务的状态和事件信息"""
        try:
            pod = self.core_v1_api.read_namespaced_pod(name=component_name, namespace="rbd-system")
            containers_info = [self._get_container_info(container_status) for container_status in
                               pod.status.container_statuses]

            pod_status_info = {
                "pod_name": pod.metadata.name,
                "status": self._get_pod_status(pod),
                "node_name": pod.spec.node_name,
                "start_time": str(pod.status.start_time) if pod.status.start_time else "",
                "pod_ip": pod.status.pod_ip,
                "host_ip": pod.status.host_ip,
                "containers": containers_info,
                "namespace": "rbd-system",
            }

            event_list = self.core_v1_api.list_namespaced_event(
                namespace="rbd-system",
                field_selector=f"involvedObject.name={component_name}"
            )

            events_info = [self._get_event_info(event) for event in event_list.items]

            return {
                "pod_status": pod_status_info,
                "events": events_info
            }

        except Exception as e:
            logger.error(f"Failed to retrieve status for component {component_name}: {str(e)}")
            return {"error": str(e)}

    def rb_region_config(self):
        """获取单个服务的状态和事件信息"""
        try:
            region_config_dict = dict()
            region_config = self.core_v1_api.read_namespaced_config_map(name="region-config", namespace="rbd-system")
            if region_config:
                client_pem_str = region_config.binary_data.get("client.pem", "")
                client_pem_bytes = base64.b64decode(client_pem_str)
                client_pem = client_pem_bytes.decode('utf-8')

                client_key_pem_str = region_config.binary_data.get("client.key.pem", "")
                client_key_pem_bytes = base64.b64decode(client_key_pem_str)
                client_key_pem = client_key_pem_bytes.decode('utf-8')

                ca_pem_str = region_config.binary_data.get("ca.pem", "")
                ca_pem_bytes = base64.b64decode(ca_pem_str)
                ca_pem = ca_pem_bytes.decode('utf-8')

                region_config_dict = {
                    "client.pem": client_pem,
                    "client.key.pem": client_key_pem,
                    "ca.pem": ca_pem,
                    "apiAddress": region_config.data.get("apiAddress", ""),
                    "websocketAddress": region_config.data.get("websocketAddress", ""),
                    "defaultDomainSuffix": region_config.data.get("defaultDomainSuffix", ""),
                    "defaultTCPHost": region_config.data.get("defaultTCPHost", "")
                }
            return region_config_dict
        except Exception as e:
            logger.error(f"Failed to retrieve region config: {str(e)}")
            return {"error": str(e)}


    def _get_container_info(self, container_status):
        """获取容器的信息"""
        image = container_status.image
        image_status = "正常" if image else "镜像缺失"

        return {
            "container_name": container_status.name,
            "status": container_status.state.waiting.reason if container_status.state.waiting else
            container_status.state.terminated.reason if container_status.state.terminated else
            "Running" if container_status.state.running else "Unknown",
            "restart_count": container_status.restart_count,
            "image": image,
            "image_status": image_status
        }

    def _get_pod_status(self, pod):
        """获取 Pod 的状态"""
        container_statuses = pod.status.container_statuses or []
        container_detailed_status = pod.status.phase  # Default status if no issues
        for container_status in container_statuses:
            state = container_status.state
            if state.waiting and state.waiting.reason:
                container_detailed_status = state.waiting.reason
                break
            elif state.terminated and state.terminated.reason:
                container_detailed_status = state.terminated.reason
                break
            elif state.running:
                container_detailed_status = "Running"
        return container_detailed_status

    def _get_event_info(self, event):
        """获取事件的信息"""
        return {
            "event_type": event.type,
            "reason": event.reason,
            "message": event.message,
            "first_timestamp": str(event.first_timestamp) if event.first_timestamp else "",
            "last_timestamp": str(event.last_timestamp) if event.last_timestamp else "",
            "count": event.count
        }
