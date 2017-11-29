/*  全局模块 封装常用的api请求功能  */
import http from '../utils/http';
import util from '../utils/util';
import widget from '../ui/widget';
import  lang from '../utils/lang.js';
const Msg = widget.Message;


/*
    获取租户全部应用状态ajax接口
*/
export const getTenantAllAppsStatus = (tenantName) => {
    var dfd = $.Deferred();
    $.ajax({
        type: "GET",  
        url: "/ajax/"+tenantName+"/serviceinfo",          
        cache: false,
        beforeSend: function(xhr, settings){  
            var csrftoken = $.cookie('csrftoken');  
            xhr.setRequestHeader("X-CSRFToken", csrftoken);  
        }
    })
    .done(function(data){
        dfd.resolve(data);
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    获取租户全部应用内存ajax接口
*/

export const getTenantAllAppsMemory  = (tenantName) => {
    var dfd = $.Deferred();
    $.ajax({
        type: "GET",  
        url: "/ajax/"+tenantName+"/tenant-disk",          
        cache: false,
        beforeSend: function(xhr, settings){  
            var csrftoken = $.cookie('csrftoken');  
            xhr.setRequestHeader("X-CSRFToken", csrftoken);  
        }
    })
    .done(function(data){
        dfd.resolve(data);
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}



/*
    
   合并获取租户全部应用状态和和内存接口，对前端来说他们应该是一个接口完成的事 
   根据业务改造数据后返回

*/

export const getTenantAllAppsStatusAndMemory = (tenantName) => {
    var dfd = $.Deferred(), 
        status = {}, 
        memorys = {},
        num = 0;
    $.when(
        getTenantAllAppsStatus(tenantName),
        getTenantAllAppsMemory(tenantName)
    ).done(function(status, memory){
        var result = {
            list: [],
            totalMemory: 0
        };
        var ids = memory.service_ids||[];
        for(let i = 0, len = ids.length; i < len; i++){
            let info = {};
            let id = ids[i];
            info.id = id;
            info.status = status[id] ? status[id].status : 'unknow'
            info.running_memory = memory[id+"_running_memory"] || 0;
            info.storage_memory = memory[id+"_storage_memory"] || 0;
            info.activeAction = status[id]? (status[id].activeAction || []) : [];
            info.disabledAction = status[id] ? (status[id].disabledAction || []) : []
            //根据应用的运行状态来显示的内存数据
            info.runtime_memory  = 0;
            if(info.status == 'running' || info.status == 'deploy'){
                info.runtime_memory = info.running_memory + info.storage_memory;
            } else {
                info.runtime_memory = info.storage_memory;
            }
            info.statusCN = status[id] ? status[id].status_cn : '未知';
            result.totalMemory += info.runtime_memory;
            result.list.push(info);
        }
        dfd.resolve(result);
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;

}



/*
	创建应用的操作事件id
	@tenantName 租户名
	@action 操作事件名称 启动:restart, 关闭:stop, 重新部署:"", 服务更新:imageUpgrade , 重启:reboot 
*/
export function getEventId(tenantName, serviceAlias, action){
	var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/" + tenantName + '/' + serviceAlias + "/events",
        data: {
            action: action
        }
    }).done(function(data){
        if (data["status"] == "success") {
            dfd.resolve(data);
        }else{
            Msg.warning(lang.get(data['status'], '操作异常，请稍后重试'));
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}


/*
    
   批量操作应用
    
*/

export const betchActionApp =  (tenantName, serviceIds, action) => {
    var dfd = $.Deferred();
    http({
        type : "POST",
        url : "/ajax/" + tenantName + "/batch-action",
        data : {
            "action":action,
            "service_ids":JSON.stringify(serviceIds)
        }
    }).done(function(data){
        if(data.ok){
            Msg.success(data.info);
            dfd.resolve(data);
        }
        else{
            Msg.warning(data.info);
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}



/* 批量部署应用 */
export function betchDeployApp(tenantName, serviceIds) {
    return betchActionApp(tenantName, serviceIds, 'deploy')
}


/* 
    批量启动应用
    @serviceIds 数组id 
*/
export function betchOpenApp(tenantName, serviceIds){
    return betchActionApp(tenantName, serviceIds, 'start')
}

/* 
    批量启动应用
    @serviceIds 数组id 
*/
export function betchCloseApp(tenantName, serviceIds){
    return betchActionApp(tenantName, serviceIds, 'stop')
}


/*
    获取能够接受日志输出的应用
*/
export const getCanReceiveLogApp = function(tenantName) {
    var dfd = $.Deferred();
    http({
        type: "GET",
        url: "/ajax/" + tenantName + "/logtype/services"
    }).done(function(data){
        var res = [];
        for(var key in data) {
            res.push(data[key]);
        }
        if(res.length){
            dfd.resolve(res);
        }else{
            Msg.warning("没有可接受日志的应用");
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    获取已有证书
*/
export const getSertificate  = function(tenantName, serviceAlias) {
    var dfd = $.Deferred();
    http({
        type: "get",
        url: "/ajax/"+ tenantName +"/" +serviceAlias+ "/certificate"
    }).done(function(data){
        dfd.resolve(data.data || []);
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

//新建证书
export function addSertificate(tenantName, serviceAlias, private_key, certificate, alias){
    var dfd = $.Deferred();
    http({
        type: "post",
        url: "/ajax/"+ tenantName +"/"+ serviceAlias +"/certificate",
        data:{
            private_key: private_key,
            certificate: certificate,
            alias: alias
        }
    }).done(function(data){
        if(data.status == 'success'){
            Msg.success(data.msg || '添加成功');
            dfd.resolve(data);
        }else{
            Msg.warning(data.msg || '添加失败');
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}


/*
    获取公告
*/
export const getAnnouncement  = function(tenantName) {
    var dfd = $.Deferred();
    http({
        type: "get",
        url: "/ajax/"+ tenantName + "/announcement"
    }).done(function(data){
        dfd.resolve(data);
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}