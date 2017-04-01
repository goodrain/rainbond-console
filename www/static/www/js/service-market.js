//服务创建
function service_create(tenantName, service_key, app_version) {
	window.location.href = "/apps/" + tenantName
			+ "/service-deploy/?service_key=" + service_key + "&app_version=" + app_version
}

function service_update(tenantName, service_key, app_version, update_version) {
    window.location.href = '/ajax/'+tenantName+'/remote/market?service_key='
            + service_key + '&app_version=' + app_version+'&update_version='+update_version+'&action=update';
}

