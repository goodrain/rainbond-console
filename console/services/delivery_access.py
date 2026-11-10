"""Source and target authorization using the existing team/application permission codes."""
from typing import Any
from console.services.delivery_manifest import DeliveryError


def team_access(user, team_name, code, app_id=None, admin=False):
    from www.models.main import Tenants, ServiceGroup
    from console.repositories.perm_repo import optimized_role_perm_repo
    team = Tenants.objects.filter(tenant_name=team_name, enterprise_id=user.enterprise_id).first()
    if not team:
        raise DeliveryError("团队不存在", 404)
    app = None
    if app_id is not None:
        app = ServiceGroup.objects.filter(ID=app_id, tenant_id=team.tenant_id).first()
        if not app:
            raise DeliveryError("应用不存在", 404)
    if admin or team.creater == user.user_id or app and user.nick_name and app.username == user.nick_name:
        return team
    permissions = optimized_role_perm_repo.get_user_team_all_perms(user_id=user.user_id, tenant_id=team.tenant_id)
    codes = set(permissions.get("global_perms", []))
    if app:
        codes.update(permissions.get("app_perms", {}).get(app.ID, []))
    if code not in codes:
        raise DeliveryError("没有执行此操作的权限", 403)
    return team


def catalog_metadata_scope(user: Any, enterprise_id: str, source: Any, admin: bool = False) -> dict[str, str]:
    if str(user.enterprise_id) != enterprise_id:
        raise DeliveryError("无权修改此企业的应用模板", 403)
    if not isinstance(source, dict) or not all(source.get(key) for key in ("team_name", "region_name", "app_id")):
        raise DeliveryError("请选择来源应用")
    scope = {"enterprise_id": enterprise_id, **{key: str(source[key]) for key in ("team_name", "region_name", "app_id")}}
    if not scope["app_id"].isdigit():
        raise DeliveryError("来源应用参数无效")
    team_access(user, scope["team_name"], 310001, scope["app_id"], admin)
    from www.models.main import ServiceGroup
    if not ServiceGroup.objects.filter(ID=scope["app_id"], region_name=scope["region_name"]).exists():
        raise DeliveryError("来源应用与集群不匹配", 404)
    return scope


def target_access(user, target, source, version, kind, admin=False):
    from www.models.main import TenantRegionInfo
    if kind == "test" and not admin:
        raise DeliveryError("仅平台管理员可以部署测试", 403)
    if not target or not all(target.get(key) for key in ("team_name", "region_name", "app_name")):
        raise DeliveryError("请选择目标团队、集群及应用名称")
    if len(target["app_name"]) > 64:
        raise DeliveryError("应用名称不能超过64个字符")
    team = team_access(user, target["team_name"], 300001, admin=admin)
    if not TenantRegionInfo.objects.filter(tenant_id=team.tenant_id, region_name=target["region_name"]).exists():
        raise DeliveryError("目标团队未开通此集群")
    if target["region_name"] != source["region_name"]:
        from console.appstore.appstore import app_store
        if app_store.is_no_multiple_region_hub(enterprise_id=user.enterprise_id):
            raise DeliveryError("跨集群安装前请先配置可被目标集群访问的共享镜像仓库")
    if kind != "test" and target["team_name"] != source["team_name"] and not version.listings.filter(
            publication_status="published").exists():
        raise DeliveryError("模板尚未上架，只能在本团队安装", 403)
    return team
