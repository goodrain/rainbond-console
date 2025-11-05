# -*- coding: utf8 -*-
"""
Gitea OAuth2 API V1 实现
支持 Gitea 私有部署的代码仓库 OAuth 认证和操作
"""
import json
import logging
import hashlib
import base64
import secrets

from console.exception.main import ServiceHandleException
from console.exception.bcode import ErrUnAuthnOauthService, ErrExpiredAuthnOauthService
from console.utils.oauth.base.exception import NoAccessKeyErr, NoOAuthServiceErr
from console.utils.oauth.base.git_oauth import GitOAuth2Interface
from console.utils.oauth.base.oauth import OAuth2User
from console.utils.urlutil import set_get_url

logger = logging.getLogger("default")


class GiteaApiV1(GitOAuth2Interface):
    """
    Gitea OAuth2 API V1 实现类

    Gitea 是一个轻量级的自托管 Git 服务，兼容 Gogs API
    官方文档: https://docs.gitea.io/
    """

    def __init__(self):
        """初始化 Gitea API 客户端"""
        super(GiteaApiV1, self).set_session()
        self.api_base = None
        self.access_token = None
        self.refresh_token = None
        self.request_params = {
            "response_type": "code",
            "scope": "repo,user:email",  # 请求的权限范围
        }
        # PKCE 相关参数
        self.pkce_code_verifier = None
        self.pkce_code_challenge = None

    def _generate_pkce_params(self):
        """
        生成 PKCE 参数

        PKCE (Proof Key for Code Exchange) 是 OAuth 2.0 的安全扩展
        用于防止授权码拦截攻击

        :return: (code_verifier, code_challenge)
        """
        # 生成 43-128 个字符的随机字符串作为 code_verifier
        # 使用 URL-safe 字符集 [A-Z, a-z, 0-9, -, ., _, ~]
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

        # 计算 code_challenge = BASE64URL(SHA256(code_verifier))
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')

        return code_verifier, code_challenge

    def get_auth_url(self, home_url=None):
        """
        获取 OAuth 授权 URL

        :param home_url: Gitea 服务器地址，如 https://gitea.example.com
        :return: 授权 URL，如 https://gitea.example.com/login/oauth/authorize
        """
        if not home_url:
            raise NoOAuthServiceErr("home_url is required")
        home_url = home_url.strip().strip("/")
        return f"{home_url}/login/oauth/authorize"

    def get_access_token_url(self, home_url=None):
        """
        获取 access_token 交换 URL

        :param home_url: Gitea 服务器地址
        :return: Token URL，如 https://gitea.example.com/login/oauth/access_token
        """
        if not home_url:
            raise NoOAuthServiceErr("home_url is required")
        home_url = home_url.strip().strip("/")
        return f"{home_url}/login/oauth/access_token"

    def get_user_url(self, home_url=None):
        """
        获取用户信息 API URL

        :param home_url: Gitea 服务器地址
        :return: 用户 API URL，如 https://gitea.example.com/api/v1/user
        """
        if not home_url:
            raise NoOAuthServiceErr("home_url is required")
        home_url = home_url.strip().strip("/")
        return f"{home_url}/api/v1/user"

    def _get_access_token(self, code=None, code_verifier=None):
        """
        获取或刷新 access_token

        :param code: OAuth 授权码（首次授权时使用）
        :param code_verifier: PKCE code_verifier（使用 PKCE 时必需）
        :return: (access_token, refresh_token)
        :raises NoOAuthServiceErr: 当 OAuth 服务未配置时
        :raises NoAccessKeyErr: 当无法获取 access_token 时
        :raises ErrUnAuthnOauthService: 当用户未授权时
        :raises ErrExpiredAuthnOauthService: 当授权已过期时
        """
        if not self.oauth_service:
            raise NoOAuthServiceErr("no found oauth service")

        if code:
            # 场景1: 使用授权码换取 access_token（首次授权）
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Connection": "close"
            }
            data = {
                "client_id": self.oauth_service.client_id,
                "client_secret": self.oauth_service.client_secret,
                "code": code,
                "redirect_uri": self.oauth_service.redirect_uri,  # 使用纯净的 redirect_uri，与 Gitea 注册的一致
                "grant_type": "authorization_code"
            }

            # 如果提供了 code_verifier，添加到请求中（PKCE）
            if code_verifier:
                data["code_verifier"] = code_verifier

            url = self.get_access_token_url(self.oauth_service.home_url)

            try:
                logger.debug(f"Requesting access token from Gitea: {url}")
                rst = self._session.post(url=url, headers=headers, json=data)
                logger.debug(f"Gitea response status: {rst.status_code}")
            except Exception as e:
                logger.exception(f"Failed to request Gitea access token: {e}")
                raise NoAccessKeyErr("can not get access key from Gitea")

            if rst.status_code == 200:
                response_data = rst.json()
                self.access_token = response_data.get("access_token")
                self.refresh_token = response_data.get("refresh_token")

                if self.access_token is None:
                    logger.error(f"No access_token in Gitea response: {response_data}")
                    return None, None

                self.api_base = self.oauth_service.home_url.strip().strip("/")
                self.update_access_token(self.access_token, self.refresh_token)
                logger.info(f"Successfully obtained Gitea access token")
                return self.access_token, self.refresh_token
            else:
                logger.error(f"Failed to get Gitea access token: {rst.status_code} - {rst.text}")
                raise NoAccessKeyErr("can not get access key from Gitea")

        else:
            # 场景2: 使用已保存的 access_token
            if self.oauth_user:
                try:
                    self.access_token = self.oauth_user.access_token
                    self.api_base = self.oauth_service.home_url.strip().strip("/")

                    # 验证 token 是否有效
                    user_info = self._request_user_info()
                    if user_info:
                        logger.debug(f"Gitea access token is valid for user: {user_info.get('login')}")
                        return self.oauth_user.access_token, self.oauth_user.refresh_token

                except Exception as e:
                    logger.warning(f"Gitea access token validation failed: {e}")

                    # token 失效，尝试使用 refresh_token 刷新
                    if self.oauth_user.refresh_token:
                        try:
                            logger.info("Attempting to refresh Gitea access token")
                            self.refresh_access_token()
                            return self.access_token, self.refresh_token
                        except Exception as refresh_error:
                            logger.error(f"Failed to refresh Gitea token: {refresh_error}")
                            self.oauth_user.delete()
                            raise ErrExpiredAuthnOauthService
                    else:
                        logger.warning("No refresh token available, deleting oauth user")
                        self.oauth_user.delete()
                        raise ErrExpiredAuthnOauthService

            raise ErrUnAuthnOauthService

    def refresh_access_token(self):
        """
        使用 refresh_token 刷新 access_token

        :raises Exception: 当刷新失败时
        """
        if not self.oauth_user or not self.oauth_user.refresh_token:
            raise Exception("No refresh token available")

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        data = {
            "refresh_token": self.oauth_user.refresh_token,
            "grant_type": "refresh_token",
            "client_id": self.oauth_service.client_id,
            "client_secret": self.oauth_service.client_secret,
        }
        url = self.get_access_token_url(self.oauth_service.home_url)

        logger.debug(f"Refreshing Gitea access token")
        rst = self._session.post(url=url, headers=headers, json=data)

        if rst.status_code == 200:
            response_data = rst.json()
            self.oauth_user.access_token = response_data.get("access_token")
            self.oauth_user.refresh_token = response_data.get("refresh_token", self.oauth_user.refresh_token)
            self.access_token = self.oauth_user.access_token
            self.refresh_token = self.oauth_user.refresh_token
            self.oauth_user.save()
            logger.info("Successfully refreshed Gitea access token")
        else:
            logger.error(f"Failed to refresh Gitea token: {rst.status_code} - {rst.text}")
            raise Exception(f"Failed to refresh token: {rst.text}")

    def _request_user_info(self):
        """
        请求用户信息（用于验证 token）

        :return: 用户信息字典，失败返回 None
        """
        if not self.access_token or not self.api_base:
            return None

        headers = {"Authorization": f"token {self.access_token}"}
        url = f"{self.api_base}/api/v1/user"

        try:
            rst = self._session.get(url=url, headers=headers, timeout=10)
            if rst.status_code == 200:
                return rst.json()
        except Exception as e:
            logger.warning(f"Failed to request Gitea user info: {e}")

        return None

    def get_user_info(self, code=None, code_verifier=None):
        """
        获取 OAuth 用户信息

        :param code: OAuth 授权码
        :param code_verifier: PKCE code_verifier（使用 PKCE 时必需）
        :return: (OAuth2User, access_token, refresh_token)
        :raises ServiceHandleException: 当无法获取用户信息时
        """
        access_token, refresh_token = self._get_access_token(code=code, code_verifier=code_verifier)
        user_data = self._request_user_info()

        if user_data:
            logger.info(f"Successfully got Gitea user info: {user_data.get('login')}")
            return OAuth2User(
                user_data.get("login"),  # 用户名
                user_data.get("id"),     # 用户ID
                user_data.get("email")   # 邮箱
            ), access_token, refresh_token

        logger.error("Failed to get Gitea user info")
        raise ServiceHandleException(msg="can not get user info from Gitea", msg_show="无法获取 Gitea 用户信息")

    def get_authorize_url(self):
        """
        生成 OAuth 授权跳转 URL (支持 PKCE)

        使用 state 参数传递 service_id 和 code_verifier
        这符合 OAuth 2.0 标准，并且可以避免 Gitea 的严格 redirect_uri 验证问题

        :return: 完整的授权 URL（包含参数）
        :raises NoOAuthServiceErr: 当 OAuth 服务未配置时
        """
        if self.oauth_service:
            # 生成 PKCE 参数
            code_verifier, code_challenge = self._generate_pkce_params()

            # 使用 state 参数传递 service_id 和 code_verifier
            # code_verifier 需要在 token 交换时使用
            state_data = {
                "service_id": str(self.oauth_service.ID),
                "code_verifier": code_verifier  # 将 code_verifier 存储在 state 中
            }
            # 使用 separators 参数生成紧凑 JSON（无空格），避免 URL 编码问题
            state = json.dumps(state_data, separators=(',', ':'))

            params = {
                "client_id": self.oauth_service.client_id,
                "redirect_uri": self.oauth_service.redirect_uri,  # 纯净的 redirect_uri，不包含 service_id
                "state": state,  # 使用 state 传递 service_id 和 code_verifier
                "code_challenge": code_challenge,  # PKCE: 授权时提供 code_challenge
                "code_challenge_method": "S256",  # PKCE: 使用 SHA256 算法
            }
            params.update(self.request_params)
            authorize_url = set_get_url(self.oauth_service.auth_url, params)
            return authorize_url
        else:
            raise NoOAuthServiceErr("no found oauth service")

    def _gitea_api_request(self, endpoint, method="GET", **kwargs):
        """
        通用 Gitea API 请求方法

        :param endpoint: API 端点，如 "user/repos"
        :param method: HTTP 方法，默认 GET
        :param kwargs: 传递给 requests 的其他参数
        :return: JSON 响应数据，失败返回 None
        """
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"token {self.access_token}"
        headers.setdefault("Accept", "application/json")

        url = f"{self.api_base}/api/v1/{endpoint}"

        try:
            rst = self._session.request(method=method, url=url, headers=headers, timeout=30, **kwargs)

            if rst.status_code == 200:
                return rst.json()
            else:
                logger.error(f"Gitea API request failed: {method} {url} - {rst.status_code} {rst.text}")
                return None
        except Exception as e:
            logger.exception(f"Gitea API request error: {method} {url} - {e}")
            return None

    def get_repos(self, *args, **kwargs):
        """
        获取用户的仓库列表

        :param page: 页码，默认 1
        :param per_page: 每页数量，默认 10
        :return: (仓库列表, 总数)
        """
        self._get_access_token()
        page = kwargs.get("page", 1)
        per_page = kwargs.get("per_page", 10)

        logger.debug(f"Getting Gitea repos: page={page}, per_page={per_page}")

        # Gitea API: GET /user/repos
        data = self._gitea_api_request(
            f"user/repos?page={page}&limit={per_page}&sort=updated"
        )

        if data:
            repo_list = []
            for repo in data:
                repo_list.append({
                    "project_id": repo.get("id"),
                    "project_full_name": repo.get("full_name"),
                    "project_name": repo.get("name"),
                    "project_description": repo.get("description", ""),
                    "project_url": repo.get("clone_url"),
                    "project_ssh_url": repo.get("ssh_url"),
                    "project_default_branch": repo.get("default_branch", "main"),
                    "updated_at": repo.get("updated_at"),
                    "created_at": repo.get("created_at")
                })

            logger.info(f"Got {len(repo_list)} Gitea repos")
            # 注意：Gitea 可能不返回总数，这里使用当前页数量作为估算
            total = len(repo_list)
            return repo_list, total

        logger.warning("No Gitea repos found or request failed")
        return [], 0

    def search_repos(self, search_key, *args, **kwargs):
        """
        搜索仓库

        :param search_key: 搜索关键词
        :param page: 页码，默认 1
        :param per_page: 每页数量，默认 10
        :return: (仓库列表, 总数)
        """
        self._get_access_token()
        page = kwargs.get("page", 1)
        per_page = kwargs.get("per_page", 10)

        logger.debug(f"Searching Gitea repos: query={search_key}, page={page}")

        # Gitea API: GET /repos/search
        data = self._gitea_api_request(
            f"repos/search?q={search_key}&page={page}&limit={per_page}&sort=updated"
        )

        if data and "data" in data:
            repo_list = []
            for repo in data["data"]:
                repo_list.append({
                    "project_id": repo.get("id"),
                    "project_full_name": repo.get("full_name"),
                    "project_name": repo.get("name"),
                    "project_description": repo.get("description", ""),
                    "project_url": repo.get("clone_url"),
                    "project_ssh_url": repo.get("ssh_url"),
                    "project_default_branch": repo.get("default_branch", "main"),
                    "updated_at": repo.get("updated_at"),
                    "created_at": repo.get("created_at")
                })

            total = data.get("total_count", len(repo_list))
            logger.info(f"Found {len(repo_list)} Gitea repos, total: {total}")
            return repo_list, total

        logger.warning("No Gitea repos found or search failed")
        return [], 0

    def get_repo_detail(self, full_name, *args, **kwargs):
        """
        获取仓库详细信息

        :param full_name: 仓库全名，格式为 "owner/repo"
        :return: 仓库详情列表（为了兼容性返回列表格式）
        """
        self._get_access_token()

        logger.debug(f"Getting Gitea repo detail: {full_name}")

        # Gitea API: GET /repos/{owner}/{repo}
        data = self._gitea_api_request(f"repos/{full_name}")

        if data:
            logger.info(f"Got Gitea repo detail: {full_name}")
            return [{
                "project_id": data.get("id"),
                "project_full_name": data.get("full_name"),
                "project_name": data.get("name"),
                "project_description": data.get("description", ""),
                "project_url": data.get("clone_url"),
                "project_ssh_url": data.get("ssh_url"),
                "project_default_branch": data.get("default_branch", "main"),
                "updated_at": data.get("updated_at"),
                "created_at": data.get("created_at")
            }]

        logger.warning(f"Failed to get Gitea repo detail: {full_name}")
        return []

    def get_branches(self, full_name):
        """
        获取仓库的分支列表

        :param full_name: 仓库全名，格式为 "owner/repo"
        :return: 分支名称列表
        """
        self._get_access_token()

        logger.debug(f"Getting Gitea branches: {full_name}")

        # Gitea API: GET /repos/{owner}/{repo}/branches
        data = self._gitea_api_request(f"repos/{full_name}/branches")

        if data:
            branches = [branch.get("name") for branch in data]
            logger.info(f"Got {len(branches)} Gitea branches for {full_name}")
            return branches

        logger.warning(f"Failed to get Gitea branches: {full_name}")
        return []

    def get_tags(self, full_name):
        """
        获取仓库的标签列表

        :param full_name: 仓库全名，格式为 "owner/repo"
        :return: 标签名称列表
        """
        self._get_access_token()

        logger.debug(f"Getting Gitea tags: {full_name}")

        # Gitea API: GET /repos/{owner}/{repo}/tags
        data = self._gitea_api_request(f"repos/{full_name}/tags")

        if data:
            tags = [tag.get("name") for tag in data]
            logger.info(f"Got {len(tags)} Gitea tags for {full_name}")
            return tags

        logger.warning(f"Failed to get Gitea tags: {full_name}")
        return []

    def get_branches_or_tags(self, type, full_name):
        """
        获取仓库的分支或标签列表

        :param type: "branches" 或 "tags"
        :param full_name: 仓库全名，格式为 "owner/repo"
        :return: 分支或标签名称列表
        """
        if type == "branches":
            return self.get_branches(full_name)
        elif type == "tags":
            return self.get_tags(full_name)
        else:
            logger.warning(f"Unknown type: {type}, expected 'branches' or 'tags'")
            return []

    def create_hook(self, host, full_name, endpoint='console/webhooks'):
        """
        创建 Webhook

        :param host: Webhook 接收地址的主机部分
        :param full_name: 仓库全名，格式为 "owner/repo"
        :param endpoint: Webhook 接收端点
        :return: Webhook 创建结果
        """
        self._get_access_token()

        webhook_url = f"{host}/{endpoint}"
        logger.debug(f"Creating Gitea webhook: {full_name} -> {webhook_url}")

        data = {
            "type": "gitea",
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "secret": ""
            },
            "events": ["push"],
            "active": True
        }

        # Gitea API: POST /repos/{owner}/{repo}/hooks
        result = self._gitea_api_request(
            f"repos/{full_name}/hooks",
            method="POST",
            json=data
        )

        if result:
            logger.info(f"Successfully created Gitea webhook for {full_name}")
        else:
            logger.error(f"Failed to create Gitea webhook for {full_name}")

        return result

    def get_clone_url(self, url):
        """
        获取带认证信息的 clone URL

        Gitea 支持在 URL 中嵌入 token 进行认证：
        https://oauth2:TOKEN@gitea.example.com/user/repo.git

        :param url: 原始仓库 URL
        :return: 带 token 的 clone URL
        :raises NoAccessKeyErr: 当没有 access_token 时
        """
        self._get_access_token()

        if not self.access_token:
            raise NoAccessKeyErr("no access token available for clone")

        # 在 URL 中嵌入认证信息
        # 格式: https://oauth2:TOKEN@gitea.example.com/user/repo.git
        if url.startswith("https://"):
            authenticated_url = url.replace("https://", f"https://oauth2:{self.access_token}@")
        elif url.startswith("http://"):
            authenticated_url = url.replace("http://", f"http://oauth2:{self.access_token}@")
        else:
            # 如果不是 http(s) 协议，返回原 URL
            logger.warning(f"Unsupported URL protocol: {url}")
            authenticated_url = url

        logger.debug(f"Generated Gitea clone URL with authentication")
        return authenticated_url

    def get_clone_user_password(self):
        """
        获取 clone 时使用的用户名和密码

        Gitea 使用 "oauth2" 作为用户名，access_token 作为密码

        :return: (username, password)
        :raises NoAccessKeyErr: 当没有 access_token 时
        """
        self._get_access_token()

        if not self.access_token:
            raise NoAccessKeyErr("no access token available")

        # Gitea 认证格式：用户名为 "oauth2"，密码为 access_token
        return "oauth2", self.access_token
