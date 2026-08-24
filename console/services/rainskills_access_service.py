# -*- coding: utf8 -*-
import logging

from console.repositories.enterprise_repo import enterprise_user_perm_repo
from console.repositories.region_repo import region_repo
from console.models.main import EnterpriseUserPerm
from console.services.license import license_service
from www.models.main import Users

logger = logging.getLogger("default")


class RainSkillsAccessService(object):
    def __init__(self,
                 license_service_instance=license_service,
                 region_repo_instance=region_repo,
                 enterprise_user_perm_repo_instance=enterprise_user_perm_repo,
                 enterprise_user_perm_model=EnterpriseUserPerm,
                 user_model=Users):
        self.license_service = license_service_instance
        self.region_repo = region_repo_instance
        self.enterprise_user_perm_repo = enterprise_user_perm_repo_instance
        self.enterprise_user_perm_model = enterprise_user_perm_model
        self.user_model = user_model

    def get_rainskills_access(self, user):
        if not user:
            return self._build_access(False, False, False, "not_authenticated")

        enterprise_id = getattr(user, "enterprise_id", "")
        if not enterprise_id:
            return self._build_access(False, False, False, "enterprise_not_found")

        license_state = self._has_valid_enterprise_license(enterprise_id)
        if license_state is None:
            return self._build_access(False, False, False, "license_check_failed")
        if license_state:
            return self._build_access(True, True, False, "")

        initial_user_id = self._get_initial_user_id(enterprise_id)
        is_initial_admin = bool(initial_user_id and initial_user_id == user.user_id)
        is_enterprise_admin = self.enterprise_user_perm_repo.is_admin(enterprise_id, user.user_id)
        if is_initial_admin and is_enterprise_admin:
            return self._build_access(True, False, True, "")

        deny_reason = "open_source_requires_enterprise" if is_enterprise_admin else "not_enterprise_admin"
        return self._build_access(False, False, is_initial_admin, deny_reason)

    def _has_valid_enterprise_license(self, enterprise_id):
        try:
            regions = self.region_repo.get_usable_regions(enterprise_id)
            regions = list(regions or [])
        except Exception as exc:
            logger.warning("failed to list usable regions for RainSkills access: %s", exc)
            return None

        lookup_failed = False
        for region in regions:
            try:
                body = self.license_service.get_license_status(enterprise_id, region.region_name)
                bean = body.get("bean", {}) if isinstance(body, dict) else {}
                if isinstance(bean, dict) and bean.get("valid") is True:
                    return True
            except Exception as exc:
                lookup_failed = True
                logger.warning(
                    "failed to get license status for RainSkills access: region=%s error=%s",
                    region.region_name,
                    exc,
                )

        if lookup_failed:
            return None
        return False

    def _get_initial_user_id(self, enterprise_id):
        marker = self.enterprise_user_perm_model.objects.filter(
            enterprise_id=enterprise_id,
            is_initial_enterprise_admin=True,
        ).first()
        if marker:
            return marker.user_id
        first_user = self.user_model.objects.filter(enterprise_id=enterprise_id).order_by(
            "create_time", "user_id").first()
        return first_user.user_id if first_user else None

    @staticmethod
    def _build_access(can_authorize, enterprise_licensed, is_initial_admin, deny_reason):
        return {
            "can_authorize_rainskills": can_authorize,
            "enterprise_licensed": enterprise_licensed,
            "is_initial_enterprise_admin": is_initial_admin,
            "deny_reason": deny_reason,
        }


rainskills_access_service = RainSkillsAccessService()
