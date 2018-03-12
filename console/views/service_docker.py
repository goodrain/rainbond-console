# -*- coding: utf8 -*-
"""
  Created on 18/2/7.
"""
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache
from console.services.region_services import region_services
from www.utils.md5Util import md5fun
from www.utils.url import get_redirect_url
from www.views import AuthedView
import logging
from django.conf import settings

logger = logging.getLogger("default")


class DockerContainerView(AuthedView):
    def get_media(self):
        media = super(DockerContainerView, self).get_media()
        return media

    @never_cache
    def get(self, request, *args, **kwargs):
        context = self.get_context()
        response = redirect(
            get_redirect_url("/apps/{0}/{1}/detail/".format(self.tenantName, self.serviceAlias), request))
        try:
            docker_c_id = request.COOKIES.get('docker_c_id', '')
            docker_h_id = request.COOKIES.get('docker_h_id', '')
            docker_s_id = request.COOKIES.get('docker_s_id', '')
            if docker_c_id != "" and docker_h_id != "" and docker_s_id != "" and docker_s_id == self.service.service_id:
                t_docker_h_id = docker_h_id.lower()
                context["tenant_id"] = self.service.tenant_id
                context["service_id"] = docker_s_id
                context["ctn_id"] = docker_c_id
                context["md5"] = md5fun(self.service.tenant_id + "_" + docker_s_id + "_" + docker_c_id)

                main_url = region_services.get_region_wsurl(self.service.service_region)
                if main_url == "auto":
                    context["ws_uri"] = '{}://{}:6060/docker_console?nodename={}'.format(
                        settings.DOCKER_WSS_URL["type"],
                        settings.DOCKER_WSS_URL[
                            self.service.service_region],
                        t_docker_h_id)
                else:
                    context["ws_uri"] = "{0}/docker_console?nodename={1}".format(main_url, t_docker_h_id)

                response = TemplateResponse(self.request, "www/console.html", context)
            response.delete_cookie('docker_c_id')
            response.delete_cookie('docker_h_id')
            response.delete_cookie('docker_s_id')
        except Exception as e:
            logger.exception(e)
        return response
