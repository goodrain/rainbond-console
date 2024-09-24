# -*- coding: utf8 -*-
import datetime
import json
import logging
from functools import reduce

from console.repositories.region_app import region_app_repo
from console.repositories.service_group_relation_repo import \
    service_group_relation_repo
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.forms import model_to_dict
from goodrain_web.custom_config import custom_config
from www.apiclient.regionapi import RegionInvokeApi
from www.github_http import GitHubApi
from www.gitlab_http import GitlabApi
from www.models.plugin import PluginBuildVersion, TenantServicePluginRelation

logger = logging.getLogger('default')

gitClient = GitlabApi()
gitHubClient = GitHubApi()
region_api = RegionInvokeApi()


class BaseTenantService(object):
    def calculate_service_cpu(self, region, min_memory):
        # The algorithm is obsolete
        min_cpu = int(min_memory) / 128 * 20
        return int(min_cpu)


class ServicePluginResource(object):
    def get_service_plugin_resource(self, service_id):
        tprs = TenantServicePluginRelation.objects.filter(service_id=service_id, plugin_status=True)
        memory = 0
        for tpr in tprs:
            try:
                pbv = PluginBuildVersion.objects.get(plugin_id=tpr.plugin_id, build_version=tpr.build_version)
                memory += pbv.min_memory
            except Exception:
                pass
        return memory

    def get_services_plugin_resource_map(self, service_ids):
        tprs = TenantServicePluginRelation.objects.filter(service_id__in=service_ids, plugin_status=True)
        service_plugin_map = {}
        for tpr in tprs:
            pbv = PluginBuildVersion.objects.filter(
                plugin_id=tpr.plugin_id, build_version=tpr.build_version).values("min_memory")
            if pbv:
                p = pbv[0]
                if service_plugin_map.get(tpr.service_id, None):
                    service_plugin_map[tpr.service_id] += p["min_memory"]
                else:
                    service_plugin_map[tpr.service_id] = p["min_memory"]
        return service_plugin_map


class CodeRepositoriesService(object):
    def __init__(self):
        self.MODULES = settings.MODULES

    def getProjectBranches(self, project_id):
        if custom_config.GITLAB:
            return gitClient.getProjectBranches(project_id)
        return ""

    def modifyUser(self, user, password):
        if custom_config.GITLAB:
            gitClient.modifyUser(user.git_user_id, password=password)

    # def addProjectMember(self, git_project_id, git_user_id, level):
    #     if custom_config.GITLAB:
    #         gitClient.addProjectMember(git_project_id, git_user_id, level)

    def listProjectMembers(self, git_project_id):
        if custom_config.GITLAB:
            return gitClient.listProjectMembers(git_project_id)
        return ""

    def deleteProjectMember(self, project_id, git_user_id):
        if custom_config.GITLAB:
            gitClient.deleteProjectMember(project_id, git_user_id)

    def addProjectMember(self, project_id, git_user_id, gitlab_identity):
        if custom_config.GITLAB:
            gitClient.addProjectMember(project_id, git_user_id, gitlab_identity)

    def editMemberIdentity(self, project_id, git_user_id, gitlab_identity):
        if custom_config.GITLAB:
            gitClient.editMemberIdentity(project_id, git_user_id, gitlab_identity)

    def get_gitHub_access_token(self, code):
        if custom_config.GITHUB:
            return gitHubClient.get_access_token(code)
        return ""

    def getgGitHubAllRepos(self, token):
        if custom_config.GITHUB:
            return gitHubClient.getAllRepos(token)
        return ""

    def gitHub_authorize_url(self, user):
        if custom_config.GITHUB:
            return gitHubClient.authorize_url(user.pk)
        return ""

    def gitHub_ReposRefs(self, user, repos, token):
        if custom_config.GITHUB:
            return gitHubClient.getReposRefs(user, repos, token)
        return ""

