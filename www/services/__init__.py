from .application import ApplicationGroupService, ApplicationService
from .user import UserService
from .tenant import TenantService
from .enterprise import EnterpriseService

app_svc = ApplicationService()
app_group_svc = ApplicationGroupService()
user_svc = UserService()
tenant_svc = TenantService()
enterprise_svc = EnterpriseService()

