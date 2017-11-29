/*  全局模块 封装常用的api请求功能  */
import utils from '../utils/util';
import widget from '../ui/widget';
import http from '../utils/http';
const Msg = widget.Message;
const csrftoken = $.cookie('csrftoken');

/*
	从租户中删除成员
*/
export const removeMemberFromTenant = function(tenantName, user) {
	var dfd = $.Deferred();
    http({
        url: '/ajax/' + tenantName + '/perms', 
        method: "POST",
        data: {"csrfmiddlewaretoken":csrftoken,"user":user,"identity": "remove"}
    }).done(function(data){

        if(data.status == 'success') {
            dfd.resolve(data);
        }else{
            Msg.warning("操作失败");
            dfd.reject(data);
        }

    }).fail(function(data){
        dfd.reject(data);
    })
	return dfd;
}

/*
	添加成员
*/

export const addMember = function(tenantName, email, perm) {
	var dfd = $.Deferred();
    http({
        url: '/ajax/' + tenantName +'/invite',
        data: {
            "csrfmiddlewaretoken":csrftoken,
            "email":email,
            "identity":perm
        },
        method: "POST"
    }).done(function(data){
        if(data.ok){
            dfd.resolve(data);
            Msg.success(data.desc);
        }else{
            dfd.reject(data);
            Msg.warning(data.desc || '操作失败，请稍后再试')
        }
    }).fail(function(data){
         dfd.reject(data);
    })
    return dfd;
}

/*
	成员设置权限
*/
export const setMemberPerm = (tenantName, user, identity) => {
	var dfd = $.Deferred();
    http({
        url: '/ajax/' + tenantName + '/perms',
        method: "POST",
        data: {"csrfmiddlewaretoken":csrftoken,"user":user,"identity":identity}
    }).done(function(data){
        if (data.ok) {
            Msg.success(data.desc)
            dfd.resolve(data);
        } else {
            Msg.warning(data.desc)
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
   去除成员权限
*/

export const removeMemberPerm = (tenantName, user) => {
    return setMemberPerm(tenantName, user);
}

/*
	删除成员
*/
export const removeMember = (tenantName, user) => {
	var dfd = $.Deferred();
    http({
        url: '/ajax/' + tenantName + '/perms', 
        method: "POST",
        data: {"csrfmiddlewaretoken":csrftoken,"user":user,"identity": "remove"}
    }).done(function(data){
        if(data.ok) {
            Msg.success(data.desc);
            dfd.resolve(data);
        }else{
            var msg = data.desc;
            msg && Msg.warning(msg)
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}
