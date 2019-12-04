# -*- coding: utf8 -*-
"""
  Created on 18/1/17.
"""
import re

from console.constants import AppConstants
from console.repositories.app_config import volume_repo, mnt_repo

from www.apiclient.regionapi import RegionInvokeApi
import logging
from console.utils.urlutil import is_path_legal
from www.utils.crypt import make_uuid

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class AppVolumeService(object):
    SYSDIRS = [
        "/",
        "/bin",
        "/boot",
        "/dev",
        "/etc",
        "/home",
        "/lib",
        "/lib64",
        "/opt",
        "/proc",
        "/root",
        "/sbin",
        "/srv",
        "/sys",
        "/tmp",
        "/usr",
        "/var",
        "/usr/local",
        "/usr/sbin",
        "/usr/bin",
    ]

    def ensure_volume_share_policy(self, tenant, service):
        volumes = self.get_service_volumes(tenant, service)
        for vo in volumes:
            if vo["access_mode"] is None or vo["access_mode"] == "":
                vo["access_mode"] = "RWO"
            vo["access_mode"] = vo["access_mode"].upper()
            if vo["access_mode"] == "RWO" or vo["access_mode"] == "ROX":
                return False
            #  后续添加share_policy进行共享策略的限制
        return True

    def get_service_support_volume_providers(self, tenant, service, kind=''):
        res, body = region_api.get_volume_providers(service.service_region, tenant.tenant_name, kind)
        # 过滤share-file & local-file的StorageClass
        if res.status != 200:
            return 200, []
        return 200, body.list

    # 需要提供更多的信息到源数据中
    # 使用数据中心接口统一返回最合适的类型，
    def get_best_suitable_volume_settings(self, tenant, service, volume_type, access_mode=None, share_policy=None,
                                          backup_policy=None, reclaim_policy=None, provider_name=None):
        data = {
            "volume_type": volume_type,
            "access_mode": access_mode,
            "share_policy": share_policy,
            "backup_policy": backup_policy
            }
        """
        settings 结构
        volume_type: string 新的存储类型，没有合适的相同的存储则返回新的存储
        changed: bool 是否有合适的相同的存储
        ... 后续待补充
        """
        settings = region_api.get_volume_best_selector(service.service_region, tenant.tenant_name, data)
        return settings.bean

    def get_service_volumes(self, tenant, service, is_config_file=False):
        volumes = []
        if is_config_file:
            volumes = volume_repo.get_service_volumes_about_config_file(service.service_id)
        else:
            volumes = volume_repo.get_service_volumes(service.service_id)
        vos = []
        res = None
        body = None
        try:
            res, body = region_api.get_service_volumes_status(service.service_region, tenant.tenant_name, service.service_alias)
        except Exception as e:
            logger.exception(e)
        if res is None or (res is not None and res.status != 200):
            for volume in volumes:
                vo = volume.to_dict()
                vo["status"] = 'not_bound'
                vos.append(vo)
            return vos
        if body and body.bean:
            for volume in volumes:
                vo = volume.to_dict()
                if vo["volume_type"] in ["share-file", "config-file", "local", "memoryfs"]:
                    vo["status"] = "bound"
                    vos.append(vo)
                    continue
                if body.bean.status[vo["volume_name"]] is not None:
                    if body.bean.status[vo["volume_name"]] == "READY":
                        vo["status"] = "bound"
                    else:
                        vo["status"] = "un_bound"
                else:
                    vo["status"] = 'not_bound'
                vos.append(vo)
        return vos

    def check_volume_name(self, service, volume_name):
        r = re.compile(u'^[a-zA-Z0-9_]+$')
        if not r.match(volume_name):
            if service.service_source != AppConstants.MARKET:
                return 400, u"持久化名称只支持数字字母下划线", volume_name
            else:
                volume_name = service.service_cname + make_uuid()[-3:]
        volume = volume_repo.get_service_volume_by_name(
            service.service_id, volume_name)

        if volume:
            return 412, u"持久化名称{0}已存在".format(volume_name), volume_name
        else:
            return 200, u"success", volume_name

    def check_volume_path(self, service, volume_path, local_path):
        if local_path:
            for path in local_path:
                # if volume_path.startswith(path):
                #     return 412, u"持久化路径不能和挂载共享路径相同"
                if volume_path.startswith(path + "/"):
                    return 412, u"持久化路径不能再挂载共享路径下"
        volume = volume_repo.get_service_volume_by_path(
            service.service_id, volume_path)
        if volume:
            return 412, u"持久化路径 {0} 已存在".format(volume_path)
        if service.service_source == AppConstants.SOURCE_CODE:
            if volume_path == "/app":
                return 409, u"源码组件不能挂载/app目录"
        if service.image != "goodrain.me/runner":
            volume_path_win = False
            if re.match('[a-zA-Z]', volume_path[0]) and volume_path[1] == ':':
                volume_path_win = True
            if not volume_path.startswith("/") and not volume_path_win:
                return 400, u"路径仅支持linux和windows"
            if volume_path in self.SYSDIRS:
                return 412, u"路径{0}为系统路径".format(volume_path)
            if volume_path_win and len(volume_path) == 3:
                return 412, u"路径不能为系统路径"
        else:
            if not is_path_legal(volume_path):
                return 412, u"请输入符合规范的路径（如：/app/volumes ）"
        all_volumes = volume_repo.get_service_volumes(
            service.service_id).values("volume_path")
        for path in list(all_volumes):
            # volume_path不能重复

            if path["volume_path"].startswith(volume_path + "/"):
                return 412, u"已存在以{0}开头的路径".format(path["volume_path"])
            if volume_path.startswith(path["volume_path"] + "/"):
                return 412, u"已存在以{0}开头的路径".format(volume_path)

        return 200, u"success"

    def __setting_volume_access_mode(self, service, volume_type, settings):
        access_mode = settings["access_mode"]
        if access_mode != "":
            return access_mode.upper()
        if volume_type == "share_file":
            if service.extend_method == "stateless":
                access_mode = "RWX"
            else:
                access_mode = "RWO"

        if volume_type == "config-file":
            access_mode = "RWX"

        if volume_type == "memoryfs" or volume_type == "local":
            access_mode = "RWO"
        if volume_type == "ceph-rbd" or volume_type == "alicloud-disk":
            access_mode = "RWO"
        # TODO 在此补充新增存储的读写模式

        return access_mode

    def __setting_volume_share_policy(self, service, volume_type, settings):
        share_policy = "exclusive"

        return share_policy

    def __setting_volume_backup_policy(self, service, volume_type, settings):
        backup_policy = "exclusive"

        return backup_policy

    def setting_volume_properties(self, service, volume_type, settings=None):
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

        settings['reclaim_policy'] = "exclusive"
        settings['allow_expansion'] = False

        return settings

    def check_volume_capacity(self, service, volume_type, settings):
        simple_volume_type = ["share-file", "config-file", "memoryfs", "local"]
        if volume_type in simple_volume_type:
            return 200, u''
        if volume_type == "ceph-rbd":
            if settings['volume_capacity'] is None or settings['volume_capacity'] == "":
                return 400, u'ceph-rbd存储容量必须大于0'
            if int(settings['volume_capacity']) <= 0:
                return 400, u'ceph块存储容量必须大于0'
        if volume_type == "alicloud-disk":
            if settings['volume_capacity'] is None or settings['volume_capacity'] == "":
                return 400, u'ceph-rbd存储容量必须大于0'
            if int(settings['volume_capacity']) <= 20:
                return 400, u'阿里云盘存储容量必须大于20'

        return 200, ''

    def check_volume_provider(self, tenant, service, volume_type, settings):
        simple_volume_type = ["share-file", "config-file", "memoryfs", "local"]
        if volume_type in simple_volume_type:
            return 200, u''
        try:
            code, providers = self.get_service_support_volume_providers(tenant, service)
            if code != 200:
                return 500, u'查询可用存储失败'
            exists = False
            for provider in providers:
                if provider.kind == volume_type:
                    for detail in provider.provisioner:
                        if detail.name == settings["provider_name"]:
                            exists = True
                            break
            if exists is False:
                return 400, "没有可用的存储驱动为{0}提供存储服务".format(volume_type)
        except Exception as e:
            logger.exception(e)
            return 500, u'查询可用存储失败'

        return 200, ''

    def check_service_multi_node(self, service, settings):
        if service.min_node > 1:
            if settings["access_mode"] == "RWO" or settings["access_mode"] == "ROX":
                return 400, '组件实例个数大于1， 存储读写模式仅支持单实例读写'
            #  后续添加share_policy进行共享策略的限制
        return 200, ''

    def add_service_volume(self, tenant, service, volume_path, volume_type, volume_name, file_content=None, settings=None):
        volume_name = volume_name.strip()
        volume_path = volume_path.strip()
        code, msg, volume_name = self.check_volume_name(service, volume_name)
        dep_mnt_names = mnt_repo.get_service_mnts(
            tenant.tenant_id, service.service_id).values_list('mnt_dir',
                                                              flat=True)
        local_path = []
        if dep_mnt_names:
            local_path.append(
                dep_mnt_names.values("mnt_dir")[0].get("mnt_dir"))
        if code != 200:
            return code, msg, None
        code, msg = self.check_volume_path(service, volume_path, local_path)
        if code != 200:
            return code, msg, None
        host_path = "/grdata/tenant/{0}/service/{1}{2}".format(
            tenant.tenant_id, service.service_id, volume_path)
        volume_data = {
            "service_id": service.service_id,
            "category": service.category,
            "host_path": host_path,
            "volume_type": volume_type,
            "volume_path": volume_path,
            "volume_name": volume_name
        }
        settings = self.setting_volume_properties(service, volume_type, settings)
        code, msg = self.check_volume_capacity(service, volume_type, settings)
        if code != 200:
            return code, msg, None
        code, msg = self.check_service_multi_node(service, settings)
        if code != 200:
            return code, msg, None
        code, msg = self.check_volume_provider(tenant, service, volume_type, settings)
        if code != 200:
            return code, msg, None

        volume_data['volume_capacity'] = settings['volume_capacity']
        volume_data['volume_provider_name'] = settings['provider_name']
        volume_data['access_mode'] = settings['access_mode']
        volume_data['share_policy'] = settings['share_policy']
        volume_data['backup_policy'] = settings['backup_policy']
        volume_data['reclaim_policy'] = settings['reclaim_policy']
        volume_data['allow_expansion'] = settings['allow_expansion']
        # region端添加数据
        if service.create_status == "complete":
            if volume_type == "config-file":
                data = {
                    "category": service.category,
                    "volume_name": volume_name,
                    "volume_path": volume_path,
                    "volume_type": volume_type,
                    "file_content": file_content,
                    "enterprise_id": tenant.enterprise_id
                }
            else:
                data = {
                    "category": service.category,
                    "volume_name": volume_name,
                    "volume_path": volume_path,
                    "volume_type": volume_type,
                    "enterprise_id": tenant.enterprise_id
                }
            data['volume_capacity'] = settings['volume_capacity']
            data['volume_provider_name'] = settings['provider_name']
            data['access_mode'] = settings['access_mode']
            data['share_policy'] = settings['share_policy']
            data['backup_policy'] = settings['backup_policy']
            data['reclaim_policy'] = settings['reclaim_policy']
            data['allow_expansion'] = settings['allow_expansion']
            res, body = region_api.add_service_volumes(service.service_region, tenant.tenant_name, service.service_alias, data)
            logger.debug(body)

        volume = volume_repo.add_service_volume(**volume_data)
        if volume_type == "config-file":
            file_data = {
                "service_id": service.service_id,
                "volume_id": volume.ID,
                "file_content": file_content
            }
            volume_repo.add_service_config_file(**file_data)
        return 200, "success", volume

    def delete_service_volume_by_id(self, tenant, service, volume_id):
        volume = volume_repo.get_service_volume_by_pk(volume_id)
        if not volume:
            return 404, u"需要删除的路径不存在", None
        # if volume.volume_type == volume.SHARE:
        # 判断当前共享目录是否被使用
        mnt = mnt_repo.get_mnt_by_dep_id_and_mntname(service.service_id,
                                                     volume.volume_name)
        if mnt:
            return 403, u"当前路径被共享,无法删除", None
        if service.create_status == "complete":
            res, body = region_api.delete_service_volumes(
                service.service_region, tenant.tenant_name,
                service.service_alias, volume.volume_name,
                tenant.enterprise_id)
            logger.debug("service {0} delete volume {1}, result {2}".format(
                service.service_cname, volume.volume_name, body))

        volume_repo.delete_volume_by_id(volume_id)
        volume_repo.delete_file_by_volume_id(volume_id)

        return 200, u"success", volume

    def delete_service_volumes(self, service):
        volume_repo.delete_service_volumes(service.service_id)

    def delete_region_volumes(self, tenant, service):
        volumes = volume_repo.get_service_volumes(service.service_id)
        for volume in volumes:
            try:
                res, body = region_api.delete_service_volumes(
                    service.service_region, tenant.tenant_name,
                    service.service_alias, volume.volume_name,
                    tenant.enterprise_id)
            except Exception as e:
                logger.exception(e)
