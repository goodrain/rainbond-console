/*  全局模块 封装常用的api请求功能  */
import http from '../utils/http';
import util from '../utils/util';
import widget from '../ui/widget';
import lang from '../utils/lang.js';
const Msg = widget.Message;


/*
    安装插件
*/
export const installPlugin = (tenantName, serviceAlias, plugin_id, version) => {
    var dfd = $.Deferred();
    http({
        type: "post",  
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/plugin/relation",
        data:{
            plugin_id: plugin_id,
            build_version:  version
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
    更新插件到最新版本
*/

export const updatePluginToNew = (tenantName, serviceAlias, plugin_id) => {
    var dfd = $.Deferred();
    http({
        type: "put",  
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/plugin/relation",
        data:{
            plugin_id: plugin_id,
            build_version:  "use_newest"
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
    卸载插件
*/
export const unInstallPlugin = (tenantName, serviceAlias, plugin_id) => {
    var dfd = $.Deferred();
    http({
        type: "delete",  
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/plugin/relation",
        data:{
            plugin_id: plugin_id
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
    停用插件
*/
export const disablePlugin = (tenantName, serviceAlias, plugin_id) => {
    var dfd = $.Deferred();
    http({
        type: "put",  
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/plugin/is_switch",
        data:{
            plugin_id: plugin_id,
            is_switch: false
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
    启用插件
*/
export const activePlugin = (tenantName, serviceAlias, plugin_id) => {
    var dfd = $.Deferred();
    http({
        type: "put",  
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/plugin/is_switch",
        data:{
            plugin_id: plugin_id,
            is_switch: true
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
     更新插件配置信息
*/
export const updatePluginVal = (tenantName, serviceAlias, data={}) => {
    var dfd = $.Deferred();
    http({
        type: "put",  
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/plugin/attrs",
        data:data
    })
    .done(function(data){
        dfd.resolve(data);
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}


/*
    获取已安装插件的配置信息
*/
export const getInstalledPluginConfig = (tenantName, serviceAlias, plugin_id, version) => {
    var dfd = $.Deferred();
    http({
        type: "get",  
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/plugin/relation",
        data:{
            plugin_id: plugin_id,
            build_version:  version
        }
    })
    .done(function(data){
        dfd.resolve(data);
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}