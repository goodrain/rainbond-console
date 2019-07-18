from www.services.apppublish import PublishAppService
from .user import UserService
from .tenant import TenantService
from .plugin import PluginService, PluginShareInfoServie

user_svc = UserService()
tenant_svc = TenantService()
plugin_svc = PluginService()
plugin_share_svc = PluginShareInfoServie()

publish_app_svc = PublishAppService()
