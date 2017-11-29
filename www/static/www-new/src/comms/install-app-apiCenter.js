/*  全局模块 封装常用的api请求功能  */
import utils from '../utils/util';
import widget from '../ui/widget';
import http from '../utils/http';
const Msg = widget.Message;

/*
	
*/
export const removeMemberFromTenant = function(tenantName, user) {
	var dfd = $.Deferred();
    http({
        url: '/ajax/' + tenantName + '/perms', 
        method: "POST",
        data: {"csrfmiddlewaretoken":csrftoken,"user":user,"identity": "remove"}
    }).done(function(data){

    }).fail(function(data){
        dfd.reject(data);
    })
	return dfd;
}