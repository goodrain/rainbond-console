from www.services.apppublish import PublishAppService
from .application import ApplicationGroupService, ApplicationService
from .user import UserService
from .tenant import TenantService
from .enterprise import EnterpriseService
from .plugin import PluginService, PluginShareInfoServie

app_svc = ApplicationService()
app_group_svc = ApplicationGroupService()
user_svc = UserService()
tenant_svc = TenantService()
enterprise_svc = EnterpriseService()
plugin_svc = PluginService()
plugin_share_svc = PluginShareInfoServie()

publish_app_svc = PublishAppService()
