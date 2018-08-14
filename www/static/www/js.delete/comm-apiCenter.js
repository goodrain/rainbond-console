/*  全局模块 封装常用的api请求功能  */


/*
	创建应用的操作事件id
	@tenantName 租户名
	@action 操作事件名称 启动:restart, 关闭:stop, 重新部署:"", 服务更新:imageUpgrade
*/
function getEventId(tenantName, serviceAlias, action){
	var dfd = $.Deferred();
    $.ajax({
        type: "POST",
        url: "/ajax/" + tenantName + '/' + serviceAlias + "/events",
        data: "action=" + action,
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
    }).done(function(data){
    	if (data["status"] == "often") {
            swal("上次操作进行中，请稍后！");
            dfd.reject();
        } else if (data["status"] == "success") {
        	dfd.resolve(data)
        } else {
            swal("操作异常！");
            dfd.reject();
        }
    }).fail(function(data){
    	swal("操作异常！");
    })
    return dfd;
}


/*
 部署应用
*/
function deployApp(categroy, tenantName, serviceAlias, eventId, isreload){
	var dfd = $.Deferred();
	var  _url = "/ajax/" + tenantName + '/' + serviceAlias + "/app-deploy/"
    if (categroy !== "application") {
        swal("暂时不支持");
        dfd.reject();
    }else{
    	$.ajax({
	        type: "POST",
	        url: _url,
	        cache: false,
	        data: "event_id=" + eventId,
	        beforeSend: function (xhr, settings) {
	            var csrftoken = $.cookie('csrftoken');
	            xhr.setRequestHeader("X-CSRFToken", csrftoken);
	        },
	        success: function (msg) {
	            var dataObj = msg;
	            if (dataObj["status"] == "success") {
	                swal.close();
	                dfd.resolve(dataObj);
	            } else if (dataObj["status"] == "owed") {
	                swal("余额不足请及时充值");
	                history.go(0);
	            } else if (dataObj["status"] == "expired") {
	                swal("试用已到期");
	                history.go(0);
	            } else if (dataObj["status"] == "language") {
	                swal("应用语言监测未通过")
	                forurl = "/apps/" + tenantName + "/" + serviceAlias
	                    + "/detail/"
	                window.open(forurl, target = "_parent")
	            } else if (dataObj["status"] == "often") {
	                swal("部署正在进行中，请稍后")
	            } else if (dataObj["status"] == "over_memory") {
	                swal("资源已达上限，不能升级")
	            } else if (dataObj["status"] == "over_money") {
	                swal("余额不足，不能升级")
	            } else {
	                swal("操作失败")
	            }
	            if (isreload == 'yes') {
	                forurl = "/apps/" + tenantName + "/" + serviceAlias
	                    + "/detail/"
	                window.open(forurl, target = "_parent")
	            }

                if(dataObj["status"] !== "success"){
                    dfd.reject();
                }
	        },
	        error: function () {
	            swal("系统异常");
	            dfd.reject();
	        }
	    });
    }
    return dfd;
}


/*	
	回滚应用
*/

function rollbackApp(tenantName, serviceAlias, eventId, deployVersion){
	var dfd = $.Deferred();

	 $.ajax({
        type: "POST",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/manage",
        data: "event_id=" + eventId + "&action=rollback&deploy_version=" + deployVersion,
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            var dataObj = msg
            if (dataObj["status"] == "success") {
                swal.close();
                dfd.resolve(dataObj);
            } else if (dataObj["status"] == "often") {
                swal("操作正在进行中，请稍后")
            } else if (dataObj["status"] == "owed") {
                swal("余额不足请及时充值")
            } else if (dataObj["status"] == "expired") {
                swal("试用已到期")
            } else if (dataObj["status"] == "over_memory") {
                swal("资源已达上限，不能升级")
            } else if (dataObj["status"] == "over_money") {
                swal("余额不足，不能升级")
            } else {
                swal("操作失败")
            }

            if (dataObj["status"] !== "success") {
            	dfd.reject();
            }	
        },
        error: function () {
            swal("系统异常");
            dfd.reject();
        }
    });
	return dfd;
}


/*
	获取应用的详情
*/

function getAppDetail(tenantName, serviceAlias) {
	return $.ajax({
		type: "GET",
		url: "/ajax/"+tenantName+"/"+serviceAlias+"/detail/",
		cache: false,
		beforeSend: function(xhr, settings){
			var csrftoken = $.cookie('csrftoken');
			xhr.setRequestHeader("X-CSRFToken", csrftoken);
		}
	})
}

/*
	更新应用
*/
function updateApp(serviceId, tenantName, serviceAlias, eventId) {
	var dfd = $.Deferred();

	return $.ajax({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/upgrade",
        data: "service_id=" + serviceId + "&action=imageUpgrade&event_id=" + eventId,
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            var dataObj = msg;
            if (dataObj["status"] == "success") {
                dfd.resolve();
            } else if (dataObj["status"] == "owed") {
                swal("余额不足请及时充值")
            } else if (dataObj["status"] == "expired") {
                swal("试用已到期")
            } else if (dataObj["status"] == "often") {
                swal("操作正在进行中，请稍后")
            } else if (dataObj["status"] == "over_memory") {
                swal("资源已达上限，不能升级")
            } else if (dataObj["status"] == "over_money") {
                swal("余额不足，不能升级")
            } else {
                swal("设置失败")
            }

            if(dataObj["status"] !== 'success'){
            	dfd.reject();
            }
        },
        error: function () {
            swal("系统异常");
            dfd.reject();
        }
    });

    return dfd;
}

/*
	应用重启
*/

function rebootApp(serviceId, tenantName, serviceAlias, eventId) {
	var dfd = $.Deferred();
	$.ajax({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/manage",
        data: "service_id=" + serviceId + "&action=reboot&event_id="+eventId,
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            var dataObj = msg
            if (dataObj["status"] == "success") {
                dfd.resolve();
            } else if (dataObj["status"] == "often") {
                swal("操作正在进行中，请稍后")
            } else if (dataObj["status"] == "owed") {
                swal("余额不足请及时充值")
            } else if (dataObj["status"] == "expired") {
                swal("试用已到期")
            } else if (dataObj["status"] == "over_memory") {
                swal("免费资源已达上限，不能操作")
            } else if (dataObj["status"] == "over_money") {
                swal("余额不足，不能操作")
            } else {
                swal("操作失败")
            }

            if(dataObj["status"] !== 'success'){
            	dfd.reject();
            }
        },
        error: function () {
            swal("系统异常");
            dfd.reject();
        }
    });
	return dfd;
}


/*
	获取应用容器节点
*/
function getAppContainer(tenantName, serviceAlias) {
	var dfd = $.Deferred();
	$.ajax({
        type: "GET",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/docker",
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (dataObj) {
            dfd.resolve(dataObj);
        },
        error: function () {
            swal("系统异常");
            dfd.reject();
        }
    });
    return dfd;
}

/*
	根据 tenantName, serviceAlias, c_id 和 host_ip 创建容器节点的socket连接
*/

function createAppContainerSocket (tenantName, serviceAlias, c_id, h_ip) {
	var dfd = $.Deferred();
    
	$.ajax({
        type: "POST",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/docker",
        data: "c_id=" + c_id + "&h_id=" + h_ip,
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (dataObj) {
        	if (dataObj["success"]) {
    			dfd.resolve(dataObj);
    		} else {
                swal("操作失败");
    			dfd.reject();
    		}
           
        },
        error: function () {
            swal("系统异常");
            dfd.reject();
        }
    });
    return dfd;
}
