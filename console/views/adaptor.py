import base64
import json
import os
import time
import tarfile
import tempfile

import requests
import yaml
from requests.auth import HTTPBasicAuth
from rest_framework import status
import logging
import hashlib
from pathlib import Path
from urllib.parse import urljoin
from urllib.parse import urlparse
import re

from console.repositories.helm import helm_repo, region_event
from console.views.base import JWTAuthApiView
from rest_framework.response import Response
from console.utils.cache import cache
def _dockerhub_get_bearer_token(repository, username=None, password=None):
    """获取 Docker Hub 的匿名/Basic 授权 token。"""
    auth_url = "https://auth.docker.io/token"
    params = {
        "service": "registry.docker.io",
        "scope": f"repository:{repository}:pull",
    }
    auth = None
    if username and password:
        auth = (username, password)
    resp = requests.get(auth_url, params=params, auth=auth, timeout=15)
    resp.raise_for_status()
    return resp.json().get("token")


def _oci_pull_chart_to_tempfile(oci_url, username=None, password=None):
    """支持从 Docker Hub 拉取 Helm OCI chart，返回临时文件路径。"""
    # 解析 oci://host/repo[:tag]
    parsed = urlparse(oci_url)
    if parsed.scheme != 'oci':
        raise ValueError("不是 oci 链接")
    host = parsed.netloc
    path = parsed.path.lstrip('/')
    if ':' in path:
        repo, ref = path.rsplit(':', 1)
    else:
        repo, ref = path, 'latest'

    # Docker Hub registry 兼容
    if host in ("registry-1.docker.io", "index.docker.io", "docker.io"):
        repository = repo
        if repository.count('/') == 0:
            repository = f"library/{repository}"
        token = _dockerhub_get_bearer_token(repository, username, password)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": ", ".join([
                "application/vnd.oci.image.manifest.v1+json",
                "application/vnd.oci.image.index.v1+json",
                "application/vnd.docker.distribution.manifest.v2+json",
                "application/vnd.docker.distribution.manifest.list.v2+json",
            ]),
            "User-Agent": "Rainbond-Console/1.0",
        }
        # 拉取 manifest 或 manifest list
        def fetch_manifest(ref_or_digest):
            murl = f"https://registry-1.docker.io/v2/{repository}/manifests/{ref_or_digest}"
            r = requests.get(murl, headers=headers, timeout=20)
            r.raise_for_status()
            return r.json()

        manifest = fetch_manifest(ref)

        # 若为 manifest list（index），选择第一个合适的子 manifest
        if 'manifests' in manifest and isinstance(manifest['manifests'], list):
            # 优先选择 mediaType 为 oci image manifest 或 docker v2 manifest
            candidates = manifest['manifests']
            chosen = None
            for m in candidates:
                mt = m.get('mediaType', '')
                if 'manifest.v1+json' in mt or 'manifest.v2+json' in mt:
                    chosen = m
                    break
            if not chosen and candidates:
                chosen = candidates[0]
            if not chosen:
                raise ValueError("OCI 索引中没有可用的 manifest")
            digest = chosen.get('digest')
            if not digest:
                raise ValueError("OCI 索引的子 manifest 缺少 digest")
            manifest = fetch_manifest(digest)

        # 识别可能的 Helm chart 层 mediaTypes
        helm_layer_media_candidates = set([
            "application/vnd.cncf.helm.chart.content.v1+tar+gzip",
            "application/vnd.cncf.helm.chart.content.v1.tar+gzip",
            "application/tar+gzip",
            "application/gzip",
            "application/x-gzip",
            "application/x-tar",
            "application/octet-stream",
        ])

        layers = manifest.get('layers') or []
        chart_digest = None
        for layer in layers:
            media = (layer.get('mediaType') or '').lower()
            if media in helm_layer_media_candidates or 'helm.chart.content' in media:
                chart_digest = layer.get('digest')
                break
        # 兜底：如果未找到，尝试逐层探测
        try_layers = [] if chart_digest else layers
        # 下载 blob 层
        def download_blob(digest):
            burl = f"https://registry-1.docker.io/v2/{repository}/blobs/{digest}"
            r = requests.get(burl, headers=headers, stream=True, timeout=60)
            r.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tgz") as temp_file:
                for chunk in r.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                return temp_file.name

        if chart_digest:
            return download_blob(chart_digest)

        # 逐层尝试，找到第一个可被 tarfile.open 正常打开的层
        for layer in try_layers:
            digest = layer.get('digest')
            if not digest:
                continue
            try:
                tmp = download_blob(digest)
                # 快速校验是否为 tar.gz
                try:
                    with tarfile.open(tmp, "r:gz"):
                        return tmp
                except Exception:
                    os.remove(tmp)
                    continue
            except Exception:
                continue
        raise ValueError("未在 manifest 中找到 Helm chart 层")

    # 其它 OCI registry（未实现通用挑战流程）
    raise ValueError("暂不支持的 OCI registry")



class Appstores(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        appstores = helm_repo.get_all_repo()
        data = list()
        for appstore in appstores:
            data.append({
                "name": appstore.repo_name,
                "url": appstore.repo_url,
                "username": appstore.username,
                "password": appstore.password,
            })
        result = {"code": 200, "msg": "success", "msg_show": "查询成功", "data": data}
        return Response(result, status=result["code"])


class Appstore(JWTAuthApiView):
    def get(self, request, enterprise_id, name, *args, **kwargs):
        app_store = helm_repo.get_helm_repo_by_name(name)
        if not app_store:
            result = {"code": 400, "msg": "success", "msg_show": "查询成功"}
            return Response(result, status=result["code"])
        result = {"code": 200, "msg": "success", "msg_show": "查询成功"}
        return Response(result, status=result["code"])


class AppstoreCharts(JWTAuthApiView):
    def get(self, request, enterprise_id, name, *args, **kwargs):
        logger = logging.getLogger('default')
        app_store = helm_repo.get_helm_repo_by_name(name)
        if app_store:
            helm_repo_url = app_store.get("repo_url")
            repo_index_url = f"{helm_repo_url.rstrip('/')}/index.yaml"
            # 读取查询参数：分页与版本限制
            try:
                page = int(request.query_params.get('page', 1))
            except Exception:
                page = 1
            try:
                page_size = int(request.query_params.get('pageSize', 50))
            except Exception:
                page_size = 50
            try:
                versions_limit = int(request.query_params.get('versions_limit', 3))
            except Exception:
                versions_limit = 3
            # 模糊查询参数（按名称包含，忽略大小写）
            query_kw = (request.query_params.get('query', '') or '').strip()
            # 二级缓存：直接缓存分页后的响应数据，避免重复解析与组装
            result_cache_key = f"appstore:index:page:{repo_index_url}:{page}:{page_size}:{versions_limit}:{query_kw.lower()}"
            cached_result = cache.get(result_cache_key)
            if isinstance(cached_result, (bytes, bytearray)):
                cached_result = cached_result.decode('utf-8')
            if cached_result:
                try:
                    cached_payload = json.loads(cached_result)
                    return Response(cached_payload, status=cached_payload.get("code", 200))
                except Exception:
                    # 缓存格式异常则忽略
                    pass

            # 优先从缓存获取 index.yaml 文本（内存/Redis + 磁盘共享缓存）
            cache_key = f"appstore:index:{repo_index_url}"
            index_text = cache.get(cache_key)
            if isinstance(index_text, (bytes, bytearray)):
                index_text = index_text.decode('utf-8')

            # 磁盘共享缓存（跨进程），默认 TTL 600s
            disk_cache_ttl = 600
            cache_root = Path("/tmp/rainbond_helm_cache")
            cache_root.mkdir(parents=True, exist_ok=True)
            index_cache_dir = cache_root / "index"
            index_cache_dir.mkdir(parents=True, exist_ok=True)
            index_cache_file = index_cache_dir / (hashlib.sha1(repo_index_url.encode('utf-8')).hexdigest() + ".cache")
            disk_hit = False
            if not index_text and index_cache_file.exists():
                try:
                    mtime = index_cache_file.stat().st_mtime
                    if time.time() - mtime < disk_cache_ttl:
                        index_text = index_cache_file.read_text(encoding='utf-8')
                        disk_hit = True
                except Exception as e:
                    logger.warning(f"读取 index.yaml 磁盘缓存异常 path={str(index_cache_file)} err={e}")

            if not index_text:
                response = requests.get(
                    repo_index_url,
                    auth=HTTPBasicAuth(app_store.get("username"), app_store.get("password")),
                    timeout=15
                )
                if response.status_code != 200:
                    logger.warning(f"拉取 index.yaml 失败，状态={response.status_code} url={repo_index_url}")
                    return Response({"code": response.status_code, "msg": "failed", "msg_show": "仓库访问失败"}, status=response.status_code)
                index_text = response.text
                # 缓存 5 分钟
                cache.set(cache_key, index_text, 300)
                # 写入磁盘共享缓存（10 分钟）
                try:
                    index_cache_file.write_text(index_text, encoding='utf-8')
                except Exception as e:
                    logger.warning(f"写入 index.yaml 磁盘缓存异常 path={str(index_cache_file)} err={e}")

            # 使用 C 加速 Loader（若可用）
            try:
                from yaml import CSafeLoader as _SafeLoader
            except Exception:
                try:
                    from yaml import CLoader as _SafeLoader  # 兼容别名
                except Exception:
                    from yaml import SafeLoader as _SafeLoader
            try:
                index_data = yaml.load(index_text, Loader=_SafeLoader) or {}
            except Exception:
                index_data = yaml.safe_load(index_text) or {}

            # 获取所有 chart 的信息并分页
            charts = index_data.get('entries', {}) or {}
            chart_names = sorted(charts.keys())
            # 模糊查询过滤
            if query_kw:
                lowered = query_kw.lower()
                chart_names = [n for n in chart_names if lowered in n.lower()]
            total = len(chart_names)

            if page < 1:
                page = 1
            if page_size <= 0:
                page_size = 50
            start = (page - 1) * page_size
            end = start + page_size
            paged_chart_names = chart_names[start:end]

            charts_data = []
            for chart_name in paged_chart_names:
                versions = charts.get(chart_name, [])
                limited_versions = versions[:versions_limit] if versions_limit > 0 else versions
                chart_info = {
                    "name": chart_name,
                    "versions": []
                }
                for version_info in limited_versions:
                    version_data = {
                        "name": chart_name,
                        "home": version_info.get('home', ''),
                        "sources": version_info.get('sources', []),
                        "version": version_info.get('version', 'N/A'),
                        "description": version_info.get('description', 'No description available'),
                        "keywords": version_info.get('keywords', []),
                        "maintainers": version_info.get('maintainers', []),
                        "icon": version_info.get('icon', ''),
                        "apiVersion": version_info.get('apiVersion', ''),
                        "appVersion": version_info.get('appVersion', ''),
                        "urls": version_info.get('urls', []),
                        "created": version_info.get('created', ''),
                        "digest": version_info.get('digest', '')
                    }
                    chart_info["versions"].append(version_data)
                charts_data.append(chart_info)
            result = {"code": 200, "msg": "success", "msg_show": "查询成功", "data": charts_data, "page": page, "page_size": page_size, "total": total, "query": query_kw}
            # 写入分页结果缓存（300s）
            try:
                payload_text = json.dumps(result, ensure_ascii=False)
                cache.set(result_cache_key, payload_text, 300)
                # 写入分页结果磁盘共享缓存（10 分钟）
                page_cache_dir = cache_root / "page"
                page_cache_dir.mkdir(parents=True, exist_ok=True)
                page_cache_file = page_cache_dir / (hashlib.sha1(result_cache_key.encode('utf-8')).hexdigest() + ".json")
                page_cache_file.write_text(payload_text, encoding='utf-8')
            except Exception:
                pass
            return Response(result, status=result["code"])
        return Response({"code": 404, "msg": "not found", "msg_show": "未找到该应用商店"}, status=404)


class AppstoreChart(JWTAuthApiView):
    def get(self, request, enterprise_id, name, chart_name, version, *args, **kwargs):
        app_store = helm_repo.get_helm_repo_by_name(name)
        if not app_store:
            return Response({"code": 400, "msg": "bad request", "msg_show": "无此应用商店"}, status=400)
        logger = logging.getLogger('default')
        base_repo_url = app_store["repo_url"].rstrip("/")
        chart_url = f"{base_repo_url}/charts/{chart_name}-{version}.tgz"
        try:
            # 下载 tgz 文件
            headers = {
                'User-Agent': 'Rainbond-Console/1.0 (+https://www.rainbond.com) Mozilla/5.0',
                'Accept': '*/*'
            }
            response = requests.get(
                chart_url,
                stream=True,
                auth=HTTPBasicAuth(app_store.get("username"), app_store.get("password")),
                timeout=20,
                headers=headers,
                allow_redirects=True
            )
            response.raise_for_status()

            # 创建临时文件来保存下载的 .tgz 包
            with tempfile.NamedTemporaryFile(delete=False, suffix=".tgz") as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            # 初始化返回数据结构
            readme_content = None
            questions_content = None
            values_content = {}

            # 读取 .tgz 文件并提取需要的文件内容
            with tarfile.open(temp_file_path, "r:gz") as tar:
                for member in tar.getmembers():
                    # 提取 README.md 并编码为 base64
                    if "README.md" in member.name and readme_content is None:
                        readme_file = tar.extractfile(member)
                        readme_content = base64.b64encode(readme_file.read()).decode("utf-8") if readme_file else None
                    # 提取 questions.yaml 并编码为 base64
                    elif "questions.yaml" in member.name and questions_content is None:
                        questions_file = tar.extractfile(member)
                        questions_content = base64.b64encode(questions_file.read()).decode(
                            "utf-8") if questions_file else None
                    # 提取所有 values.yaml 并编码为 base64
                    elif member.name.endswith("values.yaml"):
                        values_file = tar.extractfile(member)
                        values_content[member.name] = base64.b64encode(values_file.read()).decode(
                            "utf-8") if values_file else ""

            # 删除临时文件
            os.remove(temp_file_path)

            # 构造返回数据
            data = {
                "readme": readme_content or "",
                "questions": questions_content or "",
                "values": dict(reversed(list(values_content.items()))),
            }

            # 成功返回数据
            return Response({"code": 200, "msg": "success", "msg_show": "操作成功", "data": data})

        except requests.RequestException as e:
            # 主 URL 失败时，尝试通过 index.yaml 查找该 chart/version 的精确 URL 再次下载
            try:
                repo_index_url = f"{base_repo_url}/index.yaml"
                cache_key = f"appstore:index:{repo_index_url}"
                index_text = cache.get(cache_key)
                if isinstance(index_text, (bytes, bytearray)):
                    index_text = index_text.decode('utf-8')
                if not index_text:
                    # 磁盘缓存兜底
                    cache_root = Path("/tmp/rainbond_helm_cache")
                    index_cache_dir = cache_root / "index"
                    index_cache_file = index_cache_dir / (hashlib.sha1(repo_index_url.encode('utf-8')).hexdigest() + ".cache")
                    if index_cache_file.exists():
                        index_text = index_cache_file.read_text(encoding='utf-8')
                if index_text:
                    try:
                        from yaml import CSafeLoader as _SafeLoader
                    except Exception:
                        try:
                            from yaml import CLoader as _SafeLoader
                        except Exception:
                            from yaml import SafeLoader as _SafeLoader
                    try:
                        index_data = yaml.load(index_text, Loader=_SafeLoader) or {}
                    except Exception:
                        index_data = yaml.safe_load(index_text) or {}
                    entries = (index_data or {}).get('entries', {}) or {}
                    versions = entries.get(chart_name, [])
                    matched = None
                    for v in versions:
                        if str(v.get('version')) == str(version):
                            matched = v
                            break
                    if matched:
                        urls = matched.get('urls') or []
                        if urls:
                            u = urls[0]
                            if u.startswith('oci://'):
                                try:
                                    temp_file_path = _oci_pull_chart_to_tempfile(
                                        u,
                                        username=os.getenv('DOCKERHUB_USERNAME'),
                                        password=os.getenv('DOCKERHUB_PASSWORD')
                                    )
                                except Exception as eoci:
                                    logger.warning(f"OCI chart 拉取失败 url={u} err={eoci}")
                                    return Response({
                                        "code": 400,
                                        "msg": "oci pull failed",
                                        "msg_show": "OCI chart 拉取失败，请检查仓库访问与权限，或配置 HTTP chart 仓库",
                                    }, status=400)
                                # 直接解析返回
                                readme_content = None
                                questions_content = None
                                values_content = {}
                                with tarfile.open(temp_file_path, "r:gz") as tar:
                                    for member in tar.getmembers():
                                        if "README.md" in member.name and readme_content is None:
                                            readme_file = tar.extractfile(member)
                                            readme_content = base64.b64encode(readme_file.read()).decode("utf-8") if readme_file else None
                                        elif "questions.yaml" in member.name and questions_content is None:
                                            questions_file = tar.extractfile(member)
                                            questions_content = base64.b64encode(questions_file.read()).decode("utf-8") if questions_file else None
                                        elif member.name.endswith("values.yaml"):
                                            values_file = tar.extractfile(member)
                                            values_content[member.name] = base64.b64encode(values_file.read()).decode("utf-8") if values_file else ""
                                os.remove(temp_file_path)
                                data = {
                                    "readme": readme_content or "",
                                    "questions": questions_content or "",
                                    "values": dict(reversed(list(values_content.items()))),
                                }
                                return Response({"code": 200, "msg": "success", "msg_show": "操作成功", "data": data})
                            if not u.startswith('http://') and not u.startswith('https://'):
                                u = urljoin(base_repo_url + '/', u)
                            try:
                                resp2 = requests.get(
                                    u,
                                    stream=True,
                                    auth=HTTPBasicAuth(app_store.get("username"), app_store.get("password")),
                                    timeout=20,
                                    headers=headers,
                                    allow_redirects=True
                                )
                                resp2.raise_for_status()
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".tgz") as temp_file:
                                    for chunk in resp2.iter_content(chunk_size=8192):
                                        temp_file.write(chunk)
                                    temp_file_path = temp_file.name
                                readme_content = None
                                questions_content = None
                                values_content = {}
                                with tarfile.open(temp_file_path, "r:gz") as tar:
                                    for member in tar.getmembers():
                                        if "README.md" in member.name and readme_content is None:
                                            readme_file = tar.extractfile(member)
                                            readme_content = base64.b64encode(readme_file.read()).decode("utf-8") if readme_file else None
                                        elif "questions.yaml" in member.name and questions_content is None:
                                            questions_file = tar.extractfile(member)
                                            questions_content = base64.b64encode(questions_file.read()).decode("utf-8") if questions_file else None
                                        elif member.name.endswith("values.yaml"):
                                            values_file = tar.extractfile(member)
                                            values_content[member.name] = base64.b64encode(values_file.read()).decode("utf-8") if values_file else ""
                                os.remove(temp_file_path)
                                data = {
                                    "readme": readme_content or "",
                                    "questions": questions_content or "",
                                    "values": dict(reversed(list(values_content.items()))),
                                }
                                return Response({"code": 200, "msg": "success", "msg_show": "操作成功", "data": data})
                            except Exception as e2:
                                logger.warning(f"通过 index.yaml URL 重试下载失败 url={u} err={e2}")
                logger.warning(f"下载 chart 包失败 url={chart_url} err={e}")
            except Exception as e3:
                logger.warning(f"版本详情回退逻辑异常 err={e3}")
            return Response({"code": 500, "msg": "request failed", "msg_show": "请求失败，请检查网络连接"}, status=500)
        except tarfile.TarError:
            return Response({"code": 500, "msg": "invalid tgz", "msg_show": "无法解析 tgz 文件"}, status=500)


class HelmRegionInstall(JWTAuthApiView):
    def get(self, request, enterprise_id, *args, **kwargs):
        """
        获取 Helm 安装区域事件信息
        """
        try:
            # 根据企业ID和任务类型查询事件
            events = region_event.list_event(eid=enterprise_id, task_id="helm_install_region")

            if events.exists():
                event = events.first()
                try:
                    # 反序列化事件消息
                    event_data = json.loads(event.message)
                    response_data = {
                        "create_status": True,
                        "token": event_data.get("token"),
                        "api_host": event_data.get("api_host")
                    }
                except json.JSONDecodeError as e:
                    return Response({"detail": "Error decoding event message"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                response_data = {"create_status": False}
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, enterprise_id, *args, **kwargs):
        """
        初始化 Helm 安装区域事件
        """
        try:
            token = request.data.get('token', "")
            api_host = request.data.get('api_host', "")
            event_data = {
                "token": token,
                "api_host": api_host,
            }
            # 创建新的事件
            message = json.dumps(event_data)
            event = {
                "task_id": "helm_install_region",
                "enterprise_id": enterprise_id,
                "message": message,
            }
            region_event.create_region_event(**event)

            response_data = {"create_status": True}
            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, enterprise_id, *args, **kwargs):
        """
        删除 Helm 安装区域事件
        """
        try:
            # 删除事件
            region_event.delete_event(eid=enterprise_id, task_id="helm_install_region")
            return Response({"detail": "Event deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
