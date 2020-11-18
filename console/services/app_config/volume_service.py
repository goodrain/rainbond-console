# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""
import logging
import re

from console.constants import AppConstants, ServiceLanguageConstants
from console.enum.component_enum import ComponentType
from console.enum.component_enum import is_state
from console.exception.main import ServiceHandleException, ErrVolumePath
from console.repositories.app_config import mnt_repo
from console.repositories.app_config import volume_repo
from console.services.exception import ErrVolumeTypeDoNotAllowMultiNode
from console.services.exception import ErrVolumeTypeNotFound
from console.services.app_config.label_service import LabelService
from console.utils import runner_util
from console.utils.urlutil import is_path_legal
from www.apiclient.regionapi import RegionInvokeApi
from www.utils.crypt import make_uuid

region_api = RegionInvokeApi()
label_service = LabelService()
logger = logging.getLogger("default")

volume_bound = "bound"
volume_not_bound = "not_bound"
volume_ready = "READY"


class AppVolumeService(object):
    SYSDIRS = [
        "/",
        "/bin",
        "/boot",
        "/dev",
        "/etc",
        "/lib",
        "/lib64",
        "/proc",
        "/sbin",
        "/sys",
        "/var",
        "/usr/sbin",
        "/usr/bin",
    ]

    default_volume_type = "share-file"
    simple_volume_type = [default_volume_type, "config-file", "memoryfs", "local"]

    def is_simple_volume_type(self, volume_type):
        if volume_type in self.simple_volume_type:
            return True
        return False

    def ensure_volume_share_policy(self, tenant, service):
        volumes = self.get_service_volumes(tenant, service)
        for vo in volumes:
            if vo["access_mode"] is None or vo["access_mode"] == "":
                vo["access_mode"] = "RWO"
            vo["access_mode"] = vo["access_mode"].upper()
            if vo["access_mode"] == "RWO" or vo["access_mode"] == "ROX":
                return False
        return True

    def get_service_support_volume_options(self, tenant, service):
        base_opts = [{"volume_type": "share-file", "name_show": "共享存储（文件）"}, {"volume_type": "memoryfs", "name_show": "临时存储"}]
        state = False
        # state service
        if is_state(service.extend_method):
            state = True
            base_opts.append({"volume_type": "local", "name_show": "本地存储"})
        body = region_api.get_volume_options(service.service_region, tenant.tenant_name)
        for opt in body.list:
            if len(opt["access_mode"]) > 0 and opt["access_mode"][0] == "RWO":
                if state:
                    base_opts.append(opt)
            else:
                base_opts.append(opt)
        return base_opts

    def get_best_suitable_volume_settings(self,
                                          tenant,
                                          service,
                                          volume_type,
                                          access_mode=None,
                                          share_policy=None,
                                          backup_policy=None,
                                          reclaim_policy=None,
                                          provider_name=None):
        """
        settings 结构
        volume_type: string 新的存储类型，没有合适的相同的存储则返回新的存储
        changed: bool 是否有合适的相同的存储
        ... 后续待补充
        """
        settings = {}
        if volume_type in self.simple_volume_type:
            settings["changed"] = False
            return settings
        opts = self.get_service_support_volume_options(tenant, service)
        """
        1、先确定是否有相同的存储类型
        2、再确定是否有相同的存储提供方
        """
        for opt in opts:
            if opt["volume_type"] == volume_type:
                # get the same volume type
                settings["changed"] = False
                return settings

        if access_mode:
            # get the same access_mode volume type
            # TODO fanyangyang more access_mode support, if no rwo, use rwx
            for opt in opts:
                if access_mode == opt.get("access_mode", ""):
                    settings["volume_type"] = access_mode
                    settings["changed"] = True
                    return settings
        # raise volume type not found error, if no suitable volume type
        raise ErrVolumeTypeNotFound

    def get_service_volumes(self, tenant, service, is_config_file=False):
        volumes = []
        if is_config_file:
            volumes = volume_repo.get_service_volumes_about_config_file(service.service_id)
        else:
            volumes = volume_repo.get_service_volumes(service.service_id)
        vos = []
        res = None
        body = None
        if service.create_status != "complete":
            for volume in volumes:
                vo = volume.to_dict()
                vo["status"] = volume_not_bound
                vos.append(vo)
            return vos
        res, body = region_api.get_service_volumes(service.service_region, tenant.tenant_name, service.service_alias,
                                                   tenant.enterprise_id)
        if body and body.list:
            status = {}
            for volume in body.list:
                status[volume["volume_name"]] = volume["status"]

            for volume in volumes:
                vo = volume.to_dict()
                vo_status = status.get(vo["volume_name"], None)
                vo["status"] = volume_not_bound
                if vo_status and vo_status == volume_ready:
                    vo["status"] = volume_bound
                vos.append(vo)
        else:
            for volume in volumes:
                vo = volume.to_dict()
                vo["status"] = volume_not_bound
                vos.append(vo)
        return vos

    def check_volume_name(self, service, volume_name):
        r = re.compile(u'^[a-zA-Z0-9_]+$')
        if not r.match(volume_name):
            if service.service_source != AppConstants.MARKET:
                raise ServiceHandleException(msg="volume name illegal", msg_show="持久化名称只支持数字字母下划线")
            volume_name = service.service_cname + make_uuid()[-3:]
        volume = volume_repo.get_service_volume_by_name(service.service_id, volume_name)

        if volume:
            raise ServiceHandleException(msg="volume name already exists", msg_show="持久化名称[{0}]已存在".format(volume_name))
        return volume_name

    def check_volume_path(self, service, volume_path, local_path=[]):
        os_type = label_service.get_service_os_name(service)
        if os_type == "windows":
            if not runner_util.is_runner(service.image):
                if re.match('[a-zA-Z]', volume_path[0]) and volume_path[1] == ':':
                    if len(volume_path) == 3:
                        raise ErrVolumePath(msg_show="路径不能为系统路径")
                return
            else:
                return

        for path in local_path:
            if volume_path.startswith(path + "/"):
                raise ErrVolumePath(msg="path error", msg_show="持久化路径不能再挂载共享路径下")
        volume = volume_repo.get_service_volume_by_path(service.service_id, volume_path)
        if volume:
            raise ErrVolumePath(msg="path already exists", msg_show="持久化路径[{0}]已存在".format(volume_path), status_code=412)
        if service.service_source == AppConstants.SOURCE_CODE and service.language != ServiceLanguageConstants.DOCKER_FILE:
            if volume_path == "/app" or volume_path == "/tmp":
                raise ErrVolumePath(msg="path error", msg_show="源码组件不能挂载/app或/tmp目录", status_code=409)
        if not runner_util.is_runner(service.image):
            if not volume_path.startswith("/"):
                raise ErrVolumePath(msg_show="路径仅支持linux和windows")
            if volume_path in self.SYSDIRS:
                raise ErrVolumePath(msg_show="路径{0}为系统路径".format(volume_path))
        else:
            if not is_path_legal(volume_path):
                raise ErrVolumePath(msg_show="请输入符合规范的路径（如：/tmp/volumes）")
        all_volumes = volume_repo.get_service_volumes(service.service_id).values("volume_path")
        for path in list(all_volumes):
            # volume_path不能重复
            if path["volume_path"].startswith(volume_path + "/") or volume_path.startswith(path["volume_path"] + "/"):
                raise ErrVolumePath(msg="path error", msg_show="已存在以{0}开头的路径".format(path["volume_path"]), status_code=412)

    def __setting_volume_access_mode(self, service, volume_type, settings):
        access_mode = settings.get("access_mode", "")
        if access_mode != "":
            return access_mode.upper()
        if volume_type == self.default_volume_type:
            access_mode = "RWO"
            if service.extend_method == ComponentType.stateless_multiple.value:
                access_mode = "RWX"
        elif volume_type == "config-file":
            access_mode = "RWX"
        elif volume_type == "memoryfs" or volume_type == "local":
            access_mode = "RWO"
        else:
            access_mode = "RWO"

        return access_mode

    def __setting_volume_share_policy(self, service, volume_type, settings):
        share_policy = "exclusive"

        return share_policy

    def __setting_volume_backup_policy(self, service, volume_type, settings):
        backup_policy = "exclusive"

        return backup_policy

    def __setting_volume_capacity(self, service, volume_type, settings):
        if settings.get("volume_capacity"):
            return settings.get("volume_capacity")
        else:
            return 0

    def __setting_volume_provider_name(self, tenant, service, volume_type, settings):
        if volume_type in self.simple_volume_type:
            return ""
        if settings.get("volume_provider_name") is not None:
            return settings.get("volume_provider_name")
        opts = self.get_service_support_volume_options(tenant, service)
        for opt in opts:
            if opt["volume_type"] == volume_type:
                return opt["provisioner"]
        return ""

    def setting_volume_properties(self, tenant, service, volume_type, settings=None):
        """
        目的：
        1. 现有存储如果提供默认的读写策略、共享模式等参数
        """
        if settings is None:
            settings = {}
        access_mode = self.__setting_volume_access_mode(service, volume_type, settings)
        settings["access_mode"] = access_mode
        share_policy = self.__setting_volume_share_policy(service, volume_type, settings)
        settings["share_policy"] = share_policy
        backup_policy = self.__setting_volume_backup_policy(service, volume_type, settings)
        settings["backup_policy"] = backup_policy
        capacity = self.__setting_volume_capacity(service, volume_type, settings)
        settings["volume_capacity"] = capacity
        volume_provider_name = self.__setting_volume_provider_name(tenant, service, volume_type, settings)
        settings["volume_provider_name"] = volume_provider_name

        settings['reclaim_policy'] = "exclusive"
        settings['allow_expansion'] = False

        return settings

    def check_volume_options(self, tenant, service, volume_type, settings):
        if volume_type in self.simple_volume_type:
            return
        options = self.get_service_support_volume_options(tenant, service)
        exists = False
        for opt in options:
            if opt["volume_type"] == volume_type:
                exists = True
                break
        if exists is False:
            raise ErrVolumeTypeNotFound

    def check_service_multi_node(self, service, settings):
        if service.extend_method == ComponentType.state_singleton.value and service.min_node > 1:
            if settings["access_mode"] == "RWO" or settings["access_mode"] == "ROX":
                raise ErrVolumeTypeDoNotAllowMultiNode

    def add_service_volume(self, tenant, service, volume_path, volume_type, volume_name, file_content=None, settings=None):
        volume_name = volume_name.strip()
        volume_path = volume_path.strip()
        volume_name = self.check_volume_name(service, volume_name)
        self.check_volume_path(service, volume_path)
        host_path = "/grdata/tenant/{0}/service/{1}{2}".format(tenant.tenant_id, service.service_id, volume_path)
        volume_data = {
            "service_id": service.service_id,
            "category": service.category,
            "host_path": host_path,
            "volume_type": volume_type,
            "volume_path": volume_path,
            "volume_name": volume_name
        }

        self.check_volume_options(tenant, service, volume_type, settings)
        settings = self.setting_volume_properties(tenant, service, volume_type, settings)

        volume_data['volume_capacity'] = settings['volume_capacity']
        volume_data['volume_provider_name'] = settings['volume_provider_name']
        volume_data['access_mode'] = settings['access_mode']
        volume_data['share_policy'] = settings['share_policy']
        volume_data['backup_policy'] = settings['backup_policy']
        volume_data['reclaim_policy'] = settings['reclaim_policy']
        volume_data['allow_expansion'] = settings['allow_expansion']
        logger.debug("add console service volume is {0}".format(volume_data))
        # region端添加数据
        if service.create_status == "complete":
            data = {
                "category": service.category,
                "volume_name": volume_name,
                "volume_path": volume_path,
                "volume_type": volume_type,
                "enterprise_id": tenant.enterprise_id,
                "volume_capacity": settings['volume_capacity'],
                "volume_provider_name": settings['volume_provider_name'],
                "access_mode": settings['access_mode'],
                "share_policy": settings['share_policy'],
                "backup_policy": settings['backup_policy'],
                "reclaim_policy": settings['reclaim_policy'],
                "allow_expansion": settings['allow_expansion'],
            }
            if volume_type == "config-file":
                data["file_content"] = file_content
            res, body = region_api.add_service_volumes(service.service_region, tenant.tenant_name, service.service_alias, data)
            logger.debug(body)

        volume = volume_repo.add_service_volume(**volume_data)
        if volume_type == "config-file":
            file_data = {"service_id": service.service_id, "volume_id": volume.ID, "file_content": file_content}
            volume_repo.add_service_config_file(**file_data)
        return volume

    def delete_service_volume_by_id(self, tenant, service, volume_id):
        volume = volume_repo.get_service_volume_by_pk(volume_id)
        if not volume:
            return 404, u"需要删除的路径不存在", None
        # if volume.volume_type == volume.SHARE:
        # 判断当前共享目录是否被使用
        mnt = mnt_repo.get_mnt_by_dep_id_and_mntname(service.service_id, volume.volume_name)
        if mnt:
            return 403, u"当前路径被共享,无法删除", None
        if service.create_status == "complete":
            try:
                res, body = region_api.delete_service_volumes(service.service_region, tenant.tenant_name, service.service_alias,
                                                              volume.volume_name, tenant.enterprise_id)
                logger.debug("service {0} delete volume {1}, result {2}".format(service.service_cname, volume.volume_name,
                                                                                body))
            except region_api.CallApiError as e:
                if e.status != 404:
                    raise ServiceHandleException(
                        msg="delete volume from region failure", msg_show="从集群删除存储发生错误", status_code=500)
        volume_repo.delete_volume_by_id(volume_id)
        volume_repo.delete_file_by_volume_id(volume_id)

        return 200, u"success", volume

    def delete_service_volumes(self, service):
        volume_repo.delete_service_volumes(service.service_id)

    def delete_region_volumes(self, tenant, service):
        volumes = volume_repo.get_service_volumes(service.service_id)
        for volume in volumes:
            try:
                res, body = region_api.delete_service_volumes(service.service_region, tenant.tenant_name, service.service_alias,
                                                              volume.volume_name, tenant.enterprise_id)
            except Exception as e:
                logger.exception(e)
