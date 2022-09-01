#!/bin/bash
sleep 3s
if [ ! $EIP ];then
echo -e "\033[31m EIP is required, please execute the following command and restart Rainbond \033[0m "
echo -e "\033[31m  export EIP= IP address \033[0m "
        supervisorctl shutdown
        exit 0
fi

echo -e "\033[34m If there is a problem during the installation process, please refer to the troubleshooting doc (https://www.rainbond.com/docs/user-operations/deploy/install-troubleshoot/dind-install-troubleshoot) \033[0m"
echo -e "\033[34m Loading data, Estimated 3 min, Time depends on disk performance... \033[0m"
while :
do
  sleep 3s
  kubectl get node &>> /app/logs/init_rainbond_node.log
  NODE_IS_READY=$(sed -n '$p' /app/logs/init_rainbond_node.log | awk '{print $2}')
    if [ $NODE_IS_READY == "Ready" ]; then
      echo -e "\033[34m Starting Rainbond, Estimated 5 min... \033[0m"
      break
    fi
done
NODE_NAME=$(kubectl get node | sed -n '2p' | awk '{print $1}')
NODE_IP=$(kubectl get node -owide | sed -n '2p' | awk '{print $6}')
EIP=${EIP:-$NODE_IP}
IIP=${IIP:-$NODE_IP}


# 创建命名空间
(kubectl create ns rbd-system) &>> /app/logs/init_rainbond.log
# helm安装
HELM_INSTALL=$(/usr/local/bin/helm list -n rbd-system | sed -n 2p | awk '{print $1}')
if [ "$HELM_INSTALL" != "rainbond-operator" ]; then
  RBD_LIST=(rbd-api rbd-chaos rbd-eventlog rbd-gateway rbd-monitor rbd-mq rbd-node rbd-resource-proxy rbd-webcli rbd-worker rbdcluster)
  for item in "${RBD_LIST[@]}"; do
      sed -i "s/v5.6.0-release/${VERSION}/g" /app/ui/rainbond-operator/config/single_node_cr/"$item".yml
  done
  (helm install rainbond-operator /app/chart -n rbd-system --kubeconfig /root/.kube/config \
      --set operator.image.name=rainbond/rainbond-operator \
      --set operator.image.tag="${VERSION}") &>> /app/logs/init_rainbond.log
fi
# 修改yaml
sed -i "s/single_node_name/$NODE_NAME/" /app/ui/rainbond-operator/config/single_node_cr/rbdcluster.yml
sed -i "s/single_node_external_ip/$EIP/" /app/ui/rainbond-operator/config/single_node_cr/rbdcluster.yml
sed -i "s/single_node_internal_ip/$IIP/" /app/ui/rainbond-operator/config/single_node_cr/rbdcluster.yml

# 创建Pod
(kubectl apply -f /app/ui/rainbond-operator/config/single_node_cr/ -n rbd-system) &>> /app/logs/init_rainbond.log

while :
do
    sleep 3s
    (kubectl get po -l name=rbd-api -n rbd-system | sed -n '2p') &>> /app/logs/init_rainbond_api.log
    API_RUNNING=$(sed -n '$p' /app/logs/init_rainbond_api.log | awk '{print $3}')
      if [[ $API_RUNNING == "Running" ]]; then
        API_READY=$(sed -n '$p' /app/logs/init_rainbond_api.log | awk '{print $2}')
        if [[ $API_READY == "1/1" ]]; then
          echo -e "\033[32m Rainbond is successfully started, http://$EIP:7070 access Rainbond. \033[0m"
          break
        fi
      fi
done
