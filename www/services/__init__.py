from www.services.apppublish import PublishAppService
from .user import UserService
from .plugin import PluginService, PluginShareInfoServie

user_svc = UserService()
plugin_svc = PluginService()
plugin_share_svc = PluginShareInfoServie()

publish_app_svc = PublishAppService()
