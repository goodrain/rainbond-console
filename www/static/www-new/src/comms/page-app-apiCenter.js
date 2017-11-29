/*  全局模块 封装常用的api请求功能  */
import utils from '../utils/util';
import widget from '../ui/widget';
import lang from '../utils/lang';
import http from '../utils/http';
const Msg = widget.Message;
const csrftoken = $.cookie('csrftoken');

/*
获取用户充值页面数据
*/
export const getPageUserPayData = (tenantName) => {
    var dfd = $.Deferred();
    http({
        type: 'get',
        url: '/ajax/'+ tenantName +'/recharge'
    }).done((data) => {
        if(data.success === false){
            Msg.warning(data.message);
            dfd.reject(data);
        }else{
            //转换后台返回的actions
            if(data.actions){
                var actions = data.actions;
                data.actions = {};
                for(var k in actions){
                    var item = actions[k] || [];
                    for(var i=0;i<item.length;i++){
                        data.actions[item[i]] = 1;
                    }
                }
            }
            dfd.resolve(data);
        }
        
    }).fail((data) => {
        dfd.reject(data);
    })
    return dfd;
}


/*
获取团队页面数据
*/
export const getPageTeamData = (tenantName) => {
    var dfd = $.Deferred();
    http({
        type: 'get',
        url: '/ajax/'+ tenantName +'/teams'
    }).done((data) => {
        if(data.success === false){
            Msg.warning(data.message);
            dfd.reject(data);
        }else{
            //转换后台返回的actions
            if(data.actions){
                var actions = data.actions;
                data.actions = {};
                for(var k in actions){
                    var item = actions[k] || [];
                    for(var i=0;i<item.length;i++){
                        data.actions[item[i]] = 1;
                    }
                }
            }
            dfd.resolve(data);
        }
        
    }).fail((data) => {
        dfd.reject(data);
    })
    return dfd;
}

/*
获取总揽页面数据
*/
export const getPageHomeData = (tenantName) => {
    var dfd = $.Deferred();
    http({
        type: 'get',
        url: '/ajax/'+ tenantName +'/overview'
    }).done((data) => {
        if(data.success === false){
            Msg.warning(data.message);
            dfd.reject(data);
        }else{
            //转换后台返回的actions
            if(data.actions){
                var actions = data.actions;
                data.actions = {};
                for(var k in actions){
                    var item = actions[k] || [];
                    for(var i=0;i<item.length;i++){
                        data.actions[item[i]] = 1;
                    }
                }
            }
            dfd.resolve(data);
        }
        
    }).fail((data) => {
        dfd.reject(data);
    })
    return dfd;
}



/*
    获取应用页面初始数据
*/
export const getPageAppData = (tenantName, serviceAlias, type) => {
    var dfd = $.Deferred();
    http({
        type: 'get',
        url: '/ajax/'+ tenantName +'/'+ serviceAlias +'/appdetails/?fr='+type
    }).done((data) => {
        if(data.success === false){
            Msg.warning(data.message);
            dfd.reject(data);
        }else{
            //转换后台返回的actions
            if(data.actions){
                var actions = data.actions;
                data.actions = {};
                for(var k in actions){
                    var item = actions[k] || [];
                    for(var i=0;i<item.length;i++){
                        data.actions[item[i]] = 1;
                    }
                }
            }

            //设置
            if(type == 'settings'){
                var serviceId = data.tenantServiceInfo.service_id;
                var group_id = data.serviceGroupIdMap[serviceId];
                var group_name = "";
                if(group_id){
                    group_name = data.serviceGroupNameMap[group_id] || '未分组';
                }
                data.group_name = group_name;
                data.group_id = group_id;
            }

            dfd.resolve(data);
        }
        
    }).fail((data) => {
        dfd.reject(data);
    })
    return dfd;
}

/*
概览
*/

function isSameDomain(domains){
    if(domains.length == 2){
        var domain1 = domains[0];
        var domain2 = domains[1];
        if(domain1.split('//')[1] == domain2.split('//')[1]){
            return true;
        }else{
            return false;
        }

    }else{
        return false;
    }
}

function getHttpsFromDomains(domains){
    for(var i=0;i<domains.length;i++){
        if(domains[i].split('//')[0] == 'https:'){
            return domains[i];
        }
    }
}


export const getPageOverviewAppData = (tenantName, serviceAlias) => {
    var dfd = $.Deferred();
    getPageAppData(
        tenantName, 
        serviceAlias,
        'deployed'
    ).done(function(data){
         var port_domain_map = data.port_domain_map || {};
         var domains = [];
         for(var k in port_domain_map){
            domains = domains.concat(port_domain_map[k] || [])
         }

         //处理还有一个域名，但为http和https两种协议时的情况
         if(domains.length == 2){
             if(isSameDomain(domains)){
                 domains = [getHttpsFromDomains(domains)];
             }
         }

         data.domain_list = domains;
         

        dfd.resolve(data);
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}


/*
扩容
*/

export const getPageExpansionAppData = (tenantName, serviceAlias) => {
    return getPageAppData(
        tenantName, 
        serviceAlias,
        'expansion'
    )
}

/*
监控
*/

export const getPageMonitorAppData = (tenantName, serviceAlias) => {
    return getPageAppData(
        tenantName, 
        serviceAlias,
        'statistic'
    )
}

/*
日志
*/

export const getPageLogAppData = (tenantName, serviceAlias) => {
    return getPageAppData(
        tenantName, 
        serviceAlias,
        'log'
    )
}

/*
费用
*/

export const getPagePayAppData = (tenantName, serviceAlias) => {
    return getPageAppData(
        tenantName, 
        serviceAlias,
        'cost'
    )
}

/*
依赖
*/

export const getPageRelationAppData = (tenantName, serviceAlias) => {
    return getPageAppData(
        tenantName, 
        serviceAlias,
        'relations'
    )
}

/*
存储
*/

export const getPageMntAppData = (tenantName, serviceAlias) => {
    return getPageAppData(
        tenantName, 
        serviceAlias,
        'mnt'
    )
}

/*
设置
*/

export const getPageSettingAppData = (tenantName, serviceAlias) => {
    return getPageAppData(
        tenantName, 
        serviceAlias,
        'settings'
    )
}

/*
端口
*/

export const getPagePortAppData = (tenantName, serviceAlias) => {
    return getPageAppData(
        tenantName, 
        serviceAlias,
        'ports'
    )
}