# -*- coding: utf8 -*-
"""
  Created on 2018/5/10.
"""
from www.apiclient.regionapi import RegionInvokeApi
from www.models.plugin import TenantPlugin, PluginBuildVersion, TenantServicePluginAttr, TenantServicePluginRelation, \
    PluginConfigGroup, PluginConfigItems, ServicePluginConfigVar
from www.models.main import Tenants, TenantServiceInfo
import logging

region_api = RegionInvokeApi()
logger = logging.getLogger("default")


class PluginManage(object):
    def delete_user_installed_market_plugins(self):

        tps = TenantPlugin.objects.filter(origin="local_market",
                                          image="goodrain.me/envoy_discover_service_20180117184912")
        print tps.count()
        for tp in tps:
            tsprs = TenantServicePluginRelation.objects.filter(plugin_id=tp.plugin_id)
            tenant = Tenants.objects.get(tenant_id=tp.tenant_id)
            for tspr in tsprs:
                tss = TenantServiceInfo.objects.filter(service_id=tspr.service_id)
                if tss:
                    service = tss[0]
                    print "process {0}".format(service.service_cname)
                    try:

                        try:
                            region_api.uninstall_service_plugin(service.service_region, tenant.tenant_name, tp.plugin_id,
                                                                service.service_alias)
                        except region_api.CallApiError as e:
                            print e
                            if e.status != 404:
                                continue

                        TenantServicePluginRelation.objects.filter(service_id=service.service_id,
                                                                   plugin_id=tp.plugin_id).delete()

                        ServicePluginConfigVar.objects.filter(service_id=service.service_id,
                                                              plugin_id=tp.plugin_id).delete()
                        TenantServicePluginAttr.objects.filter(service_id=service.service_id,
                                                               plugin_id=tp.plugin_id).delete()

                    except Exception as e:
                        print e
                        logger.exception(e)
                        continue
            try:
                print "process plugin {0}".format(tp.plugin_name)
                try:
                    region_api.delete_plugin(tp.region, tenant.tenant_name, tp.plugin_id)
                except region_api.CallApiError as e:
                    print e
                PluginConfigGroup.objects.filter(plugin_id=tp.plugin_id).delete()
                PluginConfigItems.objects.filter(plugin_id=tp.plugin_id).delete()
                PluginBuildVersion.objects.filter(plugin_id=tp.plugin_id).delete()
                tp.delete()
            except Exception as e:
                print e


        print "finished !"
        logger.debug("finished !")

plugin_manage = PluginManage()