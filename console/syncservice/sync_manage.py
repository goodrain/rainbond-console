# -*- coding: utf8 -*-
"""
  Created on 18/3/7.
"""
from console.repositories.app import service_repo
import logging
from console.constants import AppConstants
from console.repositories.team_repo import team_gitlab_repo

logger = logging.getLogger("default")


class SyncTenantServiceManager(object):
    """更新组件表，主要有tenant_service 表中create_status(创建状态)，
        docker_cmd命令，
        team_gitlab_info表中的数据
    """

    def sync_service_info(self):
        try:
            # count = self.get_services_counts()
            print("start process ...")
            pos = 0
            NUMBER_OF_SERVICES = 300
            flag = True
            while flag:
                start_index = pos * NUMBER_OF_SERVICES
                services = self.get_limited_services(start_index, NUMBER_OF_SERVICES)
                if len(list(services)) == 0:
                    logger.debug("- process finished")
                    print("- process finished")
                    flag = False

                for s in services:
                    if not s.service_source:
                        self.process_service(s)
                logger.debug("finish process {0} data".format(NUMBER_OF_SERVICES * (pos + 1)))
                print(("finish process {0} data".format(NUMBER_OF_SERVICES * (pos + 1))))
                pos += 1
            print("process finished")
        except Exception as e:
            print(e)
            logger.exception(e)

    def process_service(self, service):
        # 先处理组件来源
        if service.category == "application":
            service.service_source = AppConstants.SOURCE_CODE
        if service.category == "app_publish":
            if service.service_key != "0000":
                service.service_source = AppConstants.MARKET
            else:
                if service.language == "docker-image":
                    service.service_source = AppConstants.DOCKER_IMAGE
                else:
                    service.service_source = AppConstants.DOCKER_COMPOSE
        # 处理git信息和docker 命令
        if service.service_source == AppConstants.SOURCE_CODE:
            if service.code_from == "gitlab_new" and service.git_project_id > 0:
                # 存储team_gitlab_info
                try:
                    repo_name = service.git_url.rsplit("/")[-1]
                except Exception:
                    repo_name = service.git_url
                params = {
                    "team_id": service.tenant_id,
                    "repo_name": repo_name,
                    "respo_url": service.git_url,
                    "git_project_id": service.git_project_id,
                    "code_version": "master"
                }
                team_gitlab_repo.create_team_gitlab_info(**params)
        service.create_status = "complete"
        service.save()

    def get_limited_services(self, start_index, number_of_services):
        query_sql = """ select * from tenant_service WHERE ID > 31182 limit {0},{1}""".format(
            str(start_index), str(number_of_services))
        services = service_repo.get_services_by_raw_sql(query_sql)
        return services

    def get_services_counts(self):
        query_count_sql = """select count(1) as num from tenant_service"""
        count = service_repo.get_services_by_raw_sql(query_count_sql)
        logger.debug(count)
        return count


syncManager = SyncTenantServiceManager()
