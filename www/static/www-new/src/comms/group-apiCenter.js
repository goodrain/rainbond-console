/*  全局模块 封装常用的api请求功能  */
import http from '../utils/http';
import utils from '../utils/util';
import widget from '../ui/widget';
var Msg = widget.Message;
/*
    分享应用组
*/
export function shareGroup(tenantName, groupId) {
    var dfd = $.Deferred();
    http({
        type : "POST",
        url : "/apps/" + tenantName + "/" + groupId + "/preview/",
        data : {
            "group_id": groupId
        }
    }).done(function(data){
       
        console.log(data);
        if (data.code == 200 || data.code == 201) {
            Msg.success('操作成功！')
            dfd.resolve(data);
        } else {
            Msg.warning(data.msg);
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;

}

/*
修改组名
*/
export const updateGroupName = (tenantName, groupId, groupName ) => {
    var dfd = $.Deferred();
    http({
        type : "post",
        url : "/ajax/" + tenantName  + "/group/update",
        data : {
            new_group_name : groupName,
            group_id: groupId
        }
    }).done(function(data){
        if (data.ok){
            Msg.success('操作成功！')
            dfd.resolve(data)
        }else{
            dfd.reject(data);
            Msg.warning(data.info);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    删除组
*/

export const deleteGroup = (tenantName, groupId) => {
    var dfd = $.Deferred();
    http({
        type : "post",
        url : "/ajax/" + tenantName  + "/group/delete",
        data : {
            group_id : groupId
        }
    }).done(function(data){
        if(data.ok) {
            Msg.success(data.info);
            dfd.resolve(data)
        }else{
            Msg.warning(data.info)
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    添加组
*/
export const addGroup = (tenantName, groupName) => {
    var dfd = $.Deferred();
    http({
        type : "post",
        url : "/ajax/" + tenantName  + "/group/add",
        data : {
            group_name : groupName
        }
    }).done(function(data){
         if (data.ok){
            Msg.success('操作成功!')
            dfd.resolve(data);
        }else{
            dfd.reject(data);
            Msg.warning(data.info);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}