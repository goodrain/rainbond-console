from django.conf import settings

from goodrain_web.base import BaseHttpClient



import json
import logging

logger = logging.getLogger('default')

class RegionServiceApi(BaseHttpClient):
    def __init__(self, *args, **kwargs):
        BaseHttpClient.__init__(self, *args, **kwargs)
        self.default_headers = {'Connection':'keep-alive'}
        region_service_info = settings.REGION_SERVICE_API
        for k, v in region_service_info.items():
            setattr(self, k, v)
            
    def create_service(self, tenant, body):
        url = self.url + "/v1/tenants/" + tenant + "/services"
        headers = {'Content-Type': 'application/json'}  
        res, body = self._post(url, headers, body)
        # logger.debug("%s:%s" % (res, body))
        return body
    
    def build_service(self, service_id, body):
        url = self.url + "/v1/services/lifecycle/" + service_id + "/build/"
        headers = {'Content-Type': 'application/json'} 
        res, body = self._post(url, headers, body)
        # logger.debug("%s:%s" % (res, body))
        return body
    
    def check_service_status(self, service_id):
        url = self.url + "/v1/services/lifecycle/" + service_id + "/status/"
        # logger.debug(url)
        res, body = self._post(url, self.default_headers)
        return body
    
    def restart(self, service_id):
        url = self.url + "/v1/services/lifecycle/" + service_id + "/restart/"
        res, body = self._post(url, self.default_headers)
        # logger.debug(body)
        return body
    
    def stop(self, service_id):
        url = self.url + "/v1/services/lifecycle/" + service_id + "/stop/"
        res, body = self._post(url, self.default_headers)
        return body
    
    def delete(self, service_id):
        url = self.url + "/v1/services/lifecycle/" + service_id + "/delete/"
        res, body = self._delete(url, self.default_headers)
        return body

    def check_status(self, body):
        url = self.url + "/v1/services/lifecycle/status/"
        headers = {'Content-Type': 'application/json'} 
        res, body = self._post(url, headers, body)
        # logger.debug(body)
        return body
    
    def get_log(self, service_id, body):        
        url = self.url + "/v1/services/lifecycle/" + service_id + "/log/"
        headers = {'Content-Type': 'application/json'}        
        res, body = self._post(url, headers, body)
        # logger.debug(body)
        return body
    
    def get_userlog(self, service_id, body):        
        url = self.url + "/v1/services/lifecycle/" + service_id + "/userlog/"
        headers = {'Content-Type': 'application/json'}  
        res, body = self._post(url, headers, body)
        # logger.debug(body)
        return body
    
    def verticalUpgrade(self, service_id, body):
        url = self.url + "/v1/services/lifecycle/" + service_id + "/vertical/"
        headers = {'Content-Type': 'application/json'}  
        res, body = self._post(url, headers, body)
        return body
        
        
    def horizontalUpgrade(self, service_id, body):
        url = self.url + "/v1/services/lifecycle/" + service_id + "/horizontal/"
        headers = {'Content-Type': 'application/json'}  
        res, body = self._put(url, headers, body)
        return body
    
    def netAndDiskStatics(self, service_id):
        url = self.url + "/v1/services/statics/" + service_id + "/net-disk/"
        res, body = self._post(url, self.default_headers)
        return body
    
    def addUserDomain(self, body):
        url = self.url + "/v1/lb/user-domains"
        headers = {'Content-Type': 'application/json'}
        res, body = self._post(url, headers, body)
        return body
    
    def changeMemory(self, service_id, body):
        url = self.url + "/v1/services/" + service_id + "/language"
        headers = {'Content-Type': 'application/json'}  
        res, body = self._post(url, headers, body)
        return body
    
    def pause(self, tenant_id):
        url = self.url + "/v1/tenants/" + tenant_id + "/pause"
        headers = {'Content-Type': 'application/json'}  
        res, body = self._post(url, headers)
        return body
    
    def unpause(self, tenant_id):
        url = self.url + "/v1/tenants/" + tenant_id + "/unpause"
        headers = {'Content-Type': 'application/json'}  
        res, body = self._post(url, headers)
        return body
