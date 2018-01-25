/*  全局模块 封装常用的api请求功能  */
import utils from '../utils/util';
import widget from '../ui/widget';
import lang from '../utils/lang';
import { getEventId } from './apiCenter';
import http from '../utils/http';
import http2 from '../utils/http2';
const Msg = widget.Message;
const csrftoken = $.cookie('csrftoken');




/*
    获取应用基本信息
*/
export const getAppInfo = (tenantName, serviceAlias) => 
{
    var dfd = $.Deferred();
    http({
        type: 'get',
        url: '/ajax/'+ tenantName +'/'+ serviceAlias +'/appinfo/'
    }).done((data) => {
        dfd.resolve(data);
    }).fail((data) => {
        dfd.reject(data);
    })
    return dfd;
}


/*
 获取应用概览页 应用信息接口
*/
export const getAppDetailsForDeploy = (serviceAlias) => {
    return http({
        type: "GET",
        url: "/ajax/"+serviceAlias+"/detail/",
        showLoading: false
    })
}

/*
 获取应用设置页 应用特性信息接口
 */
export const getAppCharacter = (tenantName, serviceAlias) => {
    var dfd = $.Deferred();
    return http({
        type: "get",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/service-labels"
    }).done(function(data){
        dfd.resolve(data);
    }).fail(function(data){
        dfd.reject();
    })
}

/*
   应用设置页 删除应用特性信息接口
 */
export const delAppCharacter = (tenantName, serviceAlias,labelid) => {
    var dfd = $.Deferred();
    return http({
        type: "post",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/service-labels/delete",
        data:{
            "label_id":labelid
        }
    }).done(function(data){
        if (data["ok"] == "true") {
            dfd.resolve(data);
         } else {
            dfd.reject(data);
         }
    }).fail(function(data){
        dfd.reject();
    })
}

/*
   应用设置页 添加标签
 */
export const addAppCharacter = (tenantName, serviceAlias,labelarr) => {
    var dfd = $.Deferred();
    return http({
        type: "post",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/service-labels",
        data:{
            "labels":JSON.stringify(labelarr)
        }
    }).done(function(data){
        if (data["ok"] == "true") {
            dfd.resolve(data);
         } else {
            dfd.reject(data);
         }
    }).fail(function(data){
        dfd.reject();
    })
}
/*
    挂载或取消挂载其他应用共享的持久化目录
*/
export const connectOrCutAppDisk = (tenantName, sourceServiceAlias, data) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + sourceServiceAlias + "/mnt",
        data: data
    }).done(function(data){
         if (data["status"] == "success") {
            dfd.resolve(data);
         } else {
            Msg.warning(data.msg || data.info || '操作失败，请稍后重试');
            dfd.reject(data);
         }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    挂载其他应用共享的持久化目录
*/
export const connectAppDisk = (tenantName, sourceServiceAlias, ids=[]) => {

    try{
        ids = JSON.stringify(ids);
    }catch(e){
        
    }

    return connectOrCutAppDisk(
        tenantName, 
        sourceServiceAlias, 
        {
            action: 'add',
            dep_vol_ids: ids
        }
    )
}

/*
    取消挂载其他应用共享的持久化目录
*/
export const cutConnectedAppDisk = (tenantName, sourceServiceAlias, id) => {
    return connectOrCutAppDisk(
        tenantName, 
        sourceServiceAlias, 
        {
            action: 'cancel',
            dep_vol_id: id
        }
    )
}


/* 创建或取消应用之间的关联关系  */
export const createOrCancelAppRelation = (tenantName, sourceServiceAlias, destServiceAlias, action) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + sourceServiceAlias + "/relation",
        data: {
            "dep_service_alias": destServiceAlias,
            "action": action
        }
    }).done(function(data){
        if (data["status"] == "success") {
           dfd.resolve(data);
        } else {
            Msg.warning(data.msg || '操作失败，请稍后重试');
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    创建应用之间的依赖关联
*/

export const createAppRelation = (tenantName, sourceServiceAlias, destServiceAlias) => {
    return createOrCancelAppRelation(
        tenantName, 
        sourceServiceAlias, 
        destServiceAlias, 
        'add'
    );
}

/*
    取消应用之间的依赖关联
*/

export const cancelAppRelation = (tenantName, sourceServiceAlias, destServiceAlias) => {
    return createOrCancelAppRelation(
        tenantName, 
        sourceServiceAlias, 
        destServiceAlias, 
        'cancel'
    )
}

/*
    判断应用是否开启了应用特性增强

    应用增强开启后， 依赖服务页面的服务依赖可以显示设置按钮
*/

export const isAppEnhanced = (tenantName, serviceAlias) => {
    var dfd = $.Deferred();
    http({
        showLoading: false,
        type : "POST",
        url : "/ajax/"+tenantName+"/"+serviceAlias+"/is_midrain", 
        data : {
               "action":"check"     
        }
    }).done(function(data){
        if(data.status === 'success'){
            dfd.resolve(data.is_mid === 'yes');
        }else{
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    开启关闭应用特性增强
*/

export const openOrCloseAppSuper = (tenantName, serviceAlias, action) => {
    var dfd = $.Deferred();
    http({
        type : "POST",
        url : "/ajax/"+tenantName+"/"+serviceAlias+"/is_midrain", 
        data : {
               "action": action     
        }
    }).done(function(data){
        if(data.status === 'success'){
            Msg.success("操作成功");
            dfd.resolve(data);
        }else{
            Msg.warning("操作失败!");
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}


/*
    开启应用特性增强
*/
export const openAppSuper = (tenantName, serviceAlias) => {
    return openOrCloseAppSuper(tenantName, serviceAlias, 'add')
}

/*
    关闭应用特性增强
*/
export const closeAppSuper = (tenantName, serviceAlias) => {
    return openOrCloseAppSuper(tenantName, serviceAlias, 'del')
}


/*
     获取应用的全部日志信息
     如果要获取应用某个实例的日志， 需要从这个接口返回的数据中过滤出来
     @param instanceId 区分是全部日志 还是某个实例日志
     如果 instanceId 不传则代表为全部日志， 否则是某个实例的日志

     @return html字符串可直接插入页面中
*/
export const getAppLog = function(tenantName, serviceAlias, instanceId) {
    var dfd = $.Deferred();
    if(instanceId) {
        instanceId = instanceId.substring(0,12);
    }
    http({
        type: "GET",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/log",
        data: {
            action: 'service'
        }
    }).done(function(data){
        var datalog = data["list"]||'';
        if(!instanceId){
            //dfd.resolve(datalog);
            var resArr = [];
            for(var i=0,len=datalog.length;i<len;i++){
                resArr.push(datalog[i].substr(13));
            }
            dfd.resolve(resArr.join('</br>'))
        }else{
             //var logArr = datalog.split('</br>');
             var resArr = [];
             for(var i=0,len=datalog.length;i<len;i++){
                //从单条日志中获取该日志所属实例的id
                var logInstanceId = datalog[i].substring(0, 12);
                if(logInstanceId === instanceId){
                    resArr.push(datalog[i].substr(13));
                }

             }
             dfd.resolve(resArr.join('</br>'))
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    获取应用log日志的socketurl
*/

export const getAppLogSocketUrl = function(tenantName, serviceAlias) {
    var dfd = $.Deferred();
    http({
        type : "GET",
        url : "/ajax/" + tenantName + "/" + serviceAlias + "/log_instance",
        data : {},
        showLoading: false
    }).done(function(data){
        var websocket_uri = data["ws_url"];
        if(websocket_uri){
            dfd.resolve(websocket_uri);
        }else{
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    检查应用是否设置了日志对接
*/

export const checkAppLogOutput = function(tenantName, serviceAlias) {
    var dfd = $.Deferred();
    http({
        type: "GET",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/match-log/check",
        cache: false
    }).done(function(data){
        var data = eval(data);
        if (data.status == "success") {
            dfd.resolve(true)
        }else{
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    取消应用日志输出
*/

export const cancelAppLogOutput = function(tenantName, serviceAlias) {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/match-log/delete"
    }).done(function(data){
        var data = eval(data);
        if (data.status == "success") {
            Msg.success("取消成功,重启后生效");
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
    设置应用日志输出
*/
export const setAppLogOutput = function(tenantName, serviceAlias, serviceId, serviceType) {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/match-log",
        data: {
            "dep_service_id": serviceId,
            "dep_service_type": serviceType
        }
    }).done(function(data){
        if (data.status == "success") {
            dfd.resolve(data);
        } else {
            Msg.warning(data.message);
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;

}

/*
    从应用中删除成员
*/
export const removeMemberFromApp = function(tenantName, serviceAlias, user) {
    var dfd = $.Deferred();
    var csrftoken = $.cookie('csrftoken');
    http({
        url: '/ajax/' + tenantName + '/' + serviceAlias + '/perms',
        method: "POST",
        data: {"csrfmiddlewaretoken":csrftoken,"user":user,"identity": "remove"}
    }).done(function(data){
        if(data.status == 'success') {
            dfd.resolve(data)
        }else{
            Msg.warning("操作失败");
            dfd.reject(data)
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    修改应用的名称
*/

export const updateAppcName = (tenantName, serviceAlias, newcName) => {
    var dfd = $.Deferred();
    http({
        type : "post",
        url : "/ajax/"+tenantName+"/change-service-name",
        data : {
            new_service_cname : newcName,
            service_alias : serviceAlias
        }
    }).done(function(data){
        if(data.ok){
           dfd.resolve(data)
        }else{
            Msg.warning(data.info);
            dfd.reject(data)
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    应用分支修改
*/
export const changeAppBrance = (tenantName, serviceAlias, branch) => {
    var dfd = $.Deferred();
    http({
        type: "post",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/branch",
        data: {
            branch: branch
        }
    }).done(function(data){
        if(data.ok){
            dfd.resolve(data)
        }else{
            Msg.warning(data.info || '操作失败，请稍后重试');
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    应用端口删除
*/

export const delAppPort = (tenantName, serviceAlias, port) => {
    var dfd = $.Deferred();
    http({
        url: '/ajax/' + tenantName + '/' + serviceAlias + '/custom-port',
        type:'post',
        data:{
            "action": "del_port",
            "port_port": port
        }
    }).done(function(data){
        if(data.success) {
            dfd.resolve(data);
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
  设定端口对内服务和对外服务的开关
*/

export const openOrCloseInnerAndOuter = (tenantName, serviceAlias, port, action) => {
    var dfd = $.Deferred();
    http({
        url: '/ajax/' + tenantName + '/' + serviceAlias + '/ports/' + port,
        data:{
            action: action
        },
        type: 'post'
    }).done(function(data){
        if(data.success) {
            Msg.success('操作成功!');
            dfd.resolve(data);
        }else{
            var msg = data.info;
            msg && Msg.warning(msg);
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject();
    })
    return dfd;
}

/*
  打开端口对外服务
*/

export const openAppInner = (tenantName, serviceAlias, port) => {
    var action = "open_inner";
    return openOrCloseInnerAndOuter(tenantName, serviceAlias, port, action)
}

/*
    关闭端口对内服务
*/

export const closeAppInner = (tenantName, serviceAlias, port) => {
    var action = "close_inner";
    return openOrCloseInnerAndOuter(tenantName, serviceAlias, port, action)
}

/*
  打开端口对外访问
*/

export const openAppOuter = (tenantName, serviceAlias, port) => {
    var action = "open_outer";
    return openOrCloseInnerAndOuter(tenantName, serviceAlias, port, action)
}

/*
  关闭端口对外访问
*/

export const closeAppOuter = (tenantName, serviceAlias, port) => {
    var action = "close_outer";
    return openOrCloseInnerAndOuter(tenantName, serviceAlias, port, action)
}

/*
    添加自动伸缩规则
    data = {
        port: port,
        item: item,
        maxvalue: maxvalue,
        minvalue: minvalue,
        nodenum: nodenum
    }
*/
export const addAutoExtendRule = (tenantName, serviceAlias, data) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/rule",
        data: data
    }).done(function(data){
        if(data.status == 'success') {
            Msg.success(data.message);
            dfd.resolve(data)
        }else{
            Msg.warning(data.message);
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    获取应用的自动伸缩规则数据
*/

export const getAutoExtendRule = (tenantName, serviceAlias) => {
    var dfd = $.Deferred();
    http({
        type: "GET",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/rule"
    }).done(function(data){
        if (data.status == "success") {
            //根据业务改造数据
            for(var id in (data.data||{})){
                var rule = data.data[id];
                rule.statuscn = rule.status ? '已生效' : '未生效';

                if (rule.item == "tp") {
                    rule.desc = "当端口" + rule.port + "吞吐率大于" + rule.minvalue + "小于"+rule.maxvalue+"时,设置实例数为"+rule.node_number;
                }
                if (rule.item == "rt") {
                   rule.desc = "当端口" + rule.port + "响应时间大于" + rule.minvalue + "小于"+rule.maxvalue+"时,设置实例数为"+rule.node_number;
                }
                if (rule.item == "on") {
                   rule.desc =  "当端口" + rule.port + "在线人数大于" + rule.minvalue + "小于"+rule.maxvalue+"时,设置实例数为"+rule.node_number;
                }
                if(!rule.desc) {
                    rule.desc = "";
                }
            }
            dfd.resolve(data.data);
        }else{
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })

    return dfd;
}

/*
    删除自动伸缩规则
*/
export const delAutoExtendRule = (tenantName, serviceAlias, id) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/rule/delete",
        data: {id: id}
    }).done(function(data){
        if (data.status == "success") {
            Msg.success("删除成功");
            dfd.resolve(data)
        } else {
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    开启或关闭自动伸缩的某条规则
*/
export const openOrCloseRule = (tenantName, serviceAlias, id, status) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/rule/status",
        data: {id: id, status: status}
    }).done(function(data){
        if (data.status == "success") {
            Msg.success(data.message);
            dfd.resolve(data);
        } else {
            Msg.warning(data.message);
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    开启自动伸缩规则
*/
export const openAutoExtendRule = (tenantName, serviceAlias, id) => {
    return openOrCloseRule(tenantName, serviceAlias, id, true)
}

/*
    关闭自动伸缩规则
*/
export const closeAutoExtendRule = (tenantName, serviceAlias, id) => {
    return openOrCloseRule(tenantName, serviceAlias, id, false)
}

/*
    设置应用手动伸缩 扩容方式
    @param extend_method  state:有状态 stateless:无状态 state-expend:有状态可水平扩容
*/
export const appUpgradeType = (tenantName, serviceAlias, extend_method) => {
    var dfd = $.Deferred();
    http({
        type: "post",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/upgrade/",
        data: {
            action: 'extend_method',
            extend_method: extend_method
        }
    }).done(function(data){
        if (data["status"] == "success") {
            Msg.success("设置成功");
            dfd.resolve(data);
        }  else {
            Msg.warning(lang.get(data['status'] || '操作失败'));
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    设置应用手动伸缩 实例数
*/
export const appUpgradePodNum = (tenantName, serviceAlias, podNum) => {
    var dfd = $.Deferred();
    getEventId(
        tenantName, 
        serviceAlias, 
        "HorizontalUpgrade"
    ).done(function(data){
        var event = data["event"];
        var eventId = event["event_id"];
        http({
            type: "post",
            url: "/ajax/" + tenantName + "/" + serviceAlias + "/upgrade/",
            data: {
                action: 'horizontal',
                node_num: podNum,
                event_id: eventId
            }
        }).done(function(data){
            if (data["status"] == "success") {
                Msg.success("设置成功");
                dfd.resolve(data);
            } else {
                Msg.warning(lang.get(data['status'] || '操作失败'));
                dfd.reject(data);
            }
        }).fail(function(data){
            dfd.reject(data);
        })
    }).fail(function(data){
        dfd.reject(data);
    })
    
    return dfd;
}

/*
    应用手动伸缩 内存及cpu修改
*/
export const appUpgradeMemory = (tenantName, serviceAlias, memory) => {
    var dfd = $.Deferred();
    getEventId(
        tenantName, 
        serviceAlias, 
        "VerticalUpgrade"
    ).done(function(data){
        var event = data["event"];
        var eventId = event["event_id"];

        var cpu = 20 * (memory / 128);
        http({
            type: "post",
            url: "/ajax/" + tenantName + "/" + serviceAlias + "/upgrade",
            data: {
                action: 'vertical',
                memory: memory,
                cpu: cpu,
                event_id: eventId
            }
        }).done(function(data){
            if (data["status"] == "success") {
                Msg.success("设置成功");
                dfd.resolve(data);
            } else {
                Msg.warning(lang.get(data['status'] || '操作失败'));
                dfd.reject(data);
            }
        }).fail(function(data){
            dfd.reject(data);
        })
    }).fail(function(){
        dfd.reject();
    })

    
    return dfd;
}

/*
    应用邀请成员
*/

export const addAppMember = function(tenantName, serviceAlias, email, perm) {
    var dfd = $.Deferred();
    http({
        url: '/ajax/' + tenantName + '/' + serviceAlias + '/invite',
        data: {
            "email":email,
            "identity":perm
        },
        method: "POST"
    }).done(function(data){
         if(data.ok){
            Msg.success(data.desc);
            dfd.resolve(data);
            
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
    应用删除成员
*/

export const removeAppMember = function(tenantName, serviceAlias, user) {
    var dfd = $.Deferred();
    http({
        url: '/ajax/' + tenantName + '/' + serviceAlias + '/perms', 
        method: "POST",
        data: {"csrfmiddlewaretoken":csrftoken,"user":user,"identity": "remove"}
    }).done(function(data){
        if(data.ok) {
            Msg.success('操作成功!');
            dfd.resolve(data);
        }else{
            var msg = data.info || data.desc;
            msg && Msg.warning(msg)
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    成员设置权限
*/
export const setAppMemberPerm = (tenantName, serviceAlias, user, identity) => {
    var dfd = $.Deferred();
    http({
        url: '/ajax/' + tenantName + '/' + serviceAlias + '/perms',
        method: "POST",
        data: {"csrfmiddlewaretoken":csrftoken,"user":user,"identity":identity||''}
    }).done(function(data){
        if (data.ok) {
            Msg.success(data.desc);
            dfd.resolve(data);
        } else {
            Msg.warning(data.desc || '操作失败');
            dfd.reject(data)
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    
    return dfd;
}

/*
    去除成员权限
*/
export const removeAppMemberPerm = (tenantName, serviceAlias, user) => {
    return setAppMemberPerm(tenantName, serviceAlias, user)
}

/*
    删除当前应用
*/
export const delApp = (tenantName, serviceAlias) => {
    var dfd = $.Deferred();
    getEventId(
        tenantName, 
        serviceAlias, 
        "delete"
    ).done(function(data){
        var event = data["event"];
        var eventId = event["event_id"];
        http({
            type: "POST",
            url: "/ajax/" + tenantName + "/" + serviceAlias + "/manage/",
            data: {
                action: 'delete',
                event_id: eventId
            }
        }).done(function(data){
            if (data["status"] == "success") {
                Msg.success('删除成功');
                dfd.resolve(data);
            } else if (data["status"] == "often") {
                Msg.warning("上次操作正在进行中，稍后再试")
            } else if (data["status"] == "published") {
                Msg.warning("关联了已发布服务, 不可删除")
            } else if (data["status"] == "evn_dependency") {
                var dep_service = data["dep_service"]
                if (typeof (dep_service) == "undefined") {
                    Msg.warning("当前服务被环境依赖不能删除");
                } else {
                    Msg.warning("当前服务被(" + dep_service + ")环境依赖不能删除");
                }
            } else if (data["status"] == "mnt_dependency") {
                var dep_service = data["dep_service"]
                if (typeof (dep_service) == "undefined") {
                    Msg.warning("当前服务被挂载依赖不能删除");
                } else {
                    Msg.warning("当前服务被(" + dep_service + ")挂载依赖不能删除");
                }
            } else if (data["status"] == "payed") {
                Msg.warning("您尚在包月期内无法删除应用")
            }
            else {
                Msg.warning(data.info || "操作失败");
            }

            if(data["status"] !== "success") {
                dfd.reject(data);
            }
        }).fail(function(data){
            dfd.reject(data);
        })

    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    添加持久化目录
*/

export const addDir = (tenantName, serviceAlias,name , dirPath, type) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/volume",
        data: {
            "action": "add",
            "volume_path": dirPath,
            "volume_name": name,
            "volume_type": type
        }
    }).done(function(data){
        var json_data = eval(data)
        if (json_data.code == 200) {
            Msg.success('操作成功');
            dfd.resolve(json_data.volume);
        } else if (json_data.code == 303) {
            Msg.warning("挂载路径必须为绝对路径");
        } else if (json_data.code == 304) {
            Msg.warning("挂载路径不能为系统目录!");
        } else if (json_data.code == 305) {
            Msg.warning("挂载路径已存在!");
        } else if (json_data.code == 306) {
            Msg.warning("挂载路径的根路径已挂载!");
        } else if (json_data.code == 307) {
            Msg.warning("挂载路径的子路径已挂载, 请先删除自路径后挂载!")
        } else {
            Msg.warning("添加失败!");
        }

        if(json_data.code !== 200){
            dfd.reject(json_data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    删除持久化条目
*/
export const removeDir = (tenantName, serviceAlias, id) => {
    var dfd = $.Deferred();
    http({
        type: "post",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/volume",
        data: {
            "action": "cancel",
            "volume_id": id
        }
    }).done(function(data){
        var json_data = eval(data)
        if (json_data.code == 200) {
            Msg.success("操作成功");
            dfd.resolve(json_data);
        } else {
            Msg.warning("删除失败!");
            dfd.reject(json_data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    新增环境变量
*/

export const addEnvVar = (tenantName, serviceAlias, attrName, attrValue, desc) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: '/ajax/' + tenantName + '/' + serviceAlias + '/custom-env',
        data: {
            "action": "add_attr",
            "attr_name": attrName,
            "attr_value": attrValue,
            "name" : desc
        }
    }).done(function(data){
        if(data.success) {
            Msg.success(data.info || '操作成功');
            dfd.resolve(data);
        }else{
            Msg.warning(data.info || '操作失败');
            dfd.reject(data);
        }
    }).fail(function(data){

    })
    return dfd;
}

/*
    删除环境变量
*/
export const delEnvVar = (tenantName, serviceAlias, attrName) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: '/ajax/' + tenantName + '/' + serviceAlias + '/custom-env',
        data: {
            "attr_name": attrName,
            "action": "del_attr"
        }
    }).done(function(data){
        if(data.success) {
            Msg.success(data.info || '操作成功');
            dfd.resolve(data);
        }else{
            Msg.warning(data.info || '操作失败');
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
     添加服务端口
*/
export const addPort = (tenantName, serviceAlias, port, protocol) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: '/ajax/' + tenantName + '/' + serviceAlias + '/custom-port',
        data: {
            "port_port": port,
            "port_alias": serviceAlias.toUpperCase() + port,
            "port_protocol": protocol,
            "action": "add_port"
        }
    }).done(function(data){
        if(data.success) {
            Msg.success(data.info || '操作成功');
            dfd.resolve(data);
        }else{
            Msg.warning(data.info || '操作失败');
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
     删除服务端口
*/
export const delPort = (tenantName, serviceAlias, port) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: '/ajax/' + tenantName + '/' + serviceAlias + '/custom-port',
        data: {
            "port_port": port,
            "action": "del_port"
        }
    }).done(function(data){
        if(data.success) {
            Msg.success(data.info || '操作成功');
            dfd.resolve(data);
        }else{
            Msg.warning(data.info || '操作失败');
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
     应用端口域名操作
*/
export const domainAction = (action, tenantName, serviceAlias, serviceId, port, domain, protocol, certificateId) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/domain",
        data: {
            protocol: protocol,
            service_id: serviceId,
            domain_name: domain,
            action: action,
            multi_port_bind: port,
            certificate_id: certificateId
        }
    }).done(function(data){
        if (data["status"] == "success") {
            Msg.success('操作成功!');
            dfd.resolve(data);
        } else if (data["status"] == "limit") {
            Msg.warning("免费用户不允许")
        } else if (data["status"] == "exist") {
            Msg.warning("域名已存在")
        } else {
            Msg.warning("操作失败")
        }
        if(data['status'] !== 'success'){
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    端口添加域名
*/

export const addDomain = (tenantName, serviceAlias, serviceId, port, domain, protocol, certificateId) => {
    return domainAction('start', tenantName, serviceAlias, serviceId, port, domain, protocol, certificateId)
}

/*
    解绑域名
*/

export const delDomain = (tenantName, serviceAlias, serviceId, port, domain) => {

    if(domain.indexOf("//") > -1){
        domain = domain.split("//")[1];
    }

    return domainAction('close', tenantName, serviceAlias, serviceId, port, domain)
}

/*
    修改端口
*/
export const editPort= (tenantName, serviceAlias, port, newPort) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/ports/"+port,
        data: {
            action: 'change_port',
            value: newPort,
            pk:1,
            name:''
        }
    }).done(function(data){
        if (data.success) {
            Msg.success('操作成功!');
            dfd.resolve(data);
        } else{
            Msg.warning(data.info || '操作失败');
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    修改协议
*/
export const editProtocol= (tenantName, serviceAlias, port, protocol) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/ports/"+port,
        data: {
            action: 'change_protocol',
            value: protocol,
            name:'edit_protocol_' + port,
            pk:1
        }
    }).done(function(data){
        if (data.success) {
            Msg.success('操作成功!');
            dfd.resolve(data);
        } else{
            Msg.warning(data.info || '操作失败');
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    修改别名
*/
export const editPortAlias= (tenantName, serviceAlias, port, portAlias) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/ports/"+port,
        data: {
            action: 'change_port_alias',
            value: portAlias,
            name:'',
            pk:1
        }
    }).done(function(data){
        if (data.success) {
            Msg.success('操作成功!');
            dfd.resolve(data);
        } else{
            Msg.warning(data.info || '操作失败');
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    更换分组
*/
export const changeGroup = (tenantName, serviceId, groupId) => {
    var dfd = $.Deferred();
    http({
        type: "post",
        url: "/ajax/"+tenantName+"/group/change-group",
        data: {
            "group_id": groupId,
            "service_id": serviceId
        }
    }).done(function(data){
        if (data.ok) {
            Msg.success(data.info);
            dfd.resolve(data);
        } else {
            Msg.warning(data.info);
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    修改基本信息
*/
export const editInfo = (tenantName, serviceAlias, name, groupId, gitUrl) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/service-info-edit",
        data: {
            "service_name":name,
            "group_id":groupId,
            "git_url":gitUrl
        }
    }).done(function(data){
        if(data["ok"]){
            Msg.success(data["msg"])
            dfd.resolve(data);
        }else{
            Msg.warning(data['msg']);
            dfd.reject(data);
        }
    }).fail(function(data){
         dfd.reject(data);
    })
    return dfd;
}

/*
    获取应用地址分支
*/


export const loadGitBranch = (tenantName, serviceAlias) => {
    var dfd = $.Deferred();
    http({
        showLoading: false,
        type: "get",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/branch"
    }).done(function(data){
        data.branchs = data.branchs || [];
        dfd.resolve(data);
    }).fail(function(XMLHttpRequest){
        dfd.reject();
    })
    return dfd;
}
/*
    获取应用某端口的innerUrl 和 outer
*/

export const loadPortUrl = (tenantName, serviceAlias, port, protocol) => {
    var dfd = $.Deferred();
    http({
        showLoading: false,
        url:'/ajax/' + tenantName + '/' + serviceAlias + '/ports/' + port,
        type: 'get'
    }).done(function(data){

        data.jsInnerUrl = '';
        if(data.environment.length) {
            data.jsInnerUrl = data.environment[0].value + ':' + data.environment[1].value
        }

        data.jsOuterUrl = '';
        data.jsOuterHerf = ''
        if(data.outer_service) {
            if(protocol == 'http') {
                data.jsOuterUrl = port + "." + data.outer_service.domain + ':' + data.outer_service.port;
            } else {
                data.jsOuterUrl = data.outer_service.domain + ':' + data.outer_service.port;
            }
            data.jsOuterHerf = "http://" + data.jsOuterUrl;
        }
        dfd.resolve(data);

    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    获取某个应用事件的log, type: info/debug/error
*/

export const getEventlogByType = (tenantName, serviceAlias, eventId, type) => {
   return http({
        type: "GET",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/event/" + eventId + "/log?level="+type
   })

}

/*
    应用确认付款
*/
export const appPay = (tenantName, serviceAlias) => {
    var dfd = $.Deferred();
    http({
        type: "post",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/pay-money"
    }).done(function(data){

        if(data["status"] == "success") {
            Msg.success("支付成功");
            dfd.resolve(data);
        }else if (data["status"] == "not_enough") {
            Msg.warning("余额不足, 请充值");
        }
        else {
            Msg.warning(data["info"] || "操作异常，请稍后再试");
        }

        if(data['status']!='success'){
            dfd.reject(data);
        }

    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}


/*
    应用启动或关闭
*/
export const appOpenOrClose = (serviceId, tenantName, serviceAlias, eventId, action) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/manage",
        data:{
            'service_id': serviceId,
            'action': action,
            'event_id': eventId
        }
    }).done(function(data){
        if(data['status'] === 'success') {
            Msg.success('操作成功!');
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
     开启应用, 需要传入eventId
*/
export const openAppByEventId = (serviceId, tenantName, serviceAlias, eventId) => {
    return appOpenOrClose(serviceId, tenantName, serviceAlias, eventId, 'restart')
}

/* 
     开启应用，不要虚传入eventId
*/
export function openApp(tenantName, serviceAlias, serviceId) {
    var dfd = $.Deferred();
    getEventId(
        tenantName, 
        serviceAlias, 
        'restart'
    )
    .done(function(data){
        var event = data["event"];
        var eventId = event["event_id"];
        openAppByEventId(
            serviceId, 
            tenantName, 
            serviceAlias, 
            eventId
        ).done(function(data){
            dfd.resolve(data);
        }).fail(function(data){
            dfd.reject(data);
        })
    })
    .fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}


/*
    关闭应用, 需要传入eventId
*/
export const closeAppByEventId = (serviceId, tenantName, serviceAlias, eventId) => {
    return appOpenOrClose(serviceId, tenantName, serviceAlias, eventId, 'stop')
}

/* 
   关闭应用, 不需要传入eventId
*/
export function closeApp(tenantName, serviceAlias, serviceId) {
    var dfd = $.Deferred(), action = 'stop';
    getEventId(
        tenantName, 
        serviceAlias, 
        action
    ).done(function(data){
        var event = data["event"];
        var eventId = event["event_id"];
        closeAppByEventId(
            serviceId, 
            tenantName, 
            serviceAlias, 
            eventId
        ).done(function(data){
            dfd.resolve(data);
        }).fail(function(data){
            dfd.reject(data);
        })
    })
    .fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}


/*
     重启应用, 需要传入eventId
*/
export const NewrebootByEventId = (serviceId, tenantName, serviceAlias, eventId) => {
    return appOpenOrClose(serviceId, tenantName, serviceAlias, eventId, 'reboot')
}

/* 
   重启应用, 不需要传入eventId
*/
export function NewrebootApp(tenantName, serviceAlias, serviceId) {
    var dfd = $.Deferred();
    getEventId(
        tenantName, 
        serviceAlias, 
        'reboot'
    ).done(function(data){
        var event = data["event"];
        var eventId = event["event_id"];
        NewrebootByEventId(
            serviceId, 
            tenantName, 
            serviceAlias, 
            eventId
        ).done(function(data){
            dfd.resolve(data);
        }).fail(function(data){
            dfd.reject(data);
        })
    })
    .fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}




/*  
    回滚应用, 需要传入eventId
*/
export function rollbackAppByEventId(tenantName, serviceAlias, deployVersion, eventId){
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/manage",
        data: {
            event_id: eventId,
            action: 'rollback',
            deploy_version: deployVersion
        }
    }).done(function(data){
        if (data["status"] == "success") {
            dfd.resolve(data);
        } else {
            Msg.warning(lang.get(data['status'], '操作异常，请稍后重试'));
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    回滚应用, 不需要传入eventId
*/

export const rollbackApp = (tenantName, serviceAlias, deployVersion) => {
    var dfd = $.Deferred();
    getEventId(
        tenantName, 
        serviceAlias,
        'rollback'
    ).done(function(data){
        var event = data["event"];
        var eventId = event["event_id"];
        rollbackAppByEventId(
            tenantName, 
            serviceAlias, 
            eventId
        ).done(function(data){
            dfd.resolve(data);
        }).fail(function(data){
            dfd.reject(data);
        })
    })
    .fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    更新应用, 需要传eventId
*/
export const updateAppByEventId = (serviceId, tenantName, serviceAlias, eventId) => {
    var dfd = $.Deferred();

    http({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/upgrade",
        data: {
            service_id: serviceId,
            action: 'imageUpgrade',
            event_id: eventId
        }
    }).done(function(data){
        if (data["status"] == "success") {
            dfd.resolve(data);
        } else {
            Msg.warning(lang.get(data['status'], '操作异常，请稍后重试'));
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject();
    })
    return dfd;
}

/*
     更新应用， 不需要传入eventId
*/

export const updateApp = (serviceId, tenantName, serviceAlias) => {
    var dfd = $.Deferred();
    getEventId(
        tenantName, 
        serviceAlias,
        'imageUpgrade'
    ).done(function(data){
        var event = data["event"];
        var eventId = event["event_id"];
        updateAppByEventId(
            serviceId,
            tenantName, 
            serviceAlias, 
            eventId
        ).done(function(data){
            dfd.resolve(data);
        }).fail(function(data){
            dfd.reject(data);
        })
    })
    .fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    应用重启, 需要传入eventId
*/

export const rebootAppByEventId = (serviceId, tenantName, serviceAlias, eventId) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + serviceAlias + "/manage",
        data: {
            service_id: serviceId,
            action: 'reboot',
            event_id: eventId
        }
    }).done(function(data){
        if (data["status"] == "success") {
            dfd.resolve(data);
        } else {
            Msg.warning(lang.get(data['status'], '操作异常，请稍后重试'));
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    应用重启, 不需要传入eventId
*/

export const rebootApp = (serviceId, tenantName, serviceAlias) => {
    var dfd = $.Deferred();
    getEventId(
        tenantName, 
        serviceAlias,
        'reboot'
    ).done(function(data){
        var event = data["event"];
        var eventId = event["event_id"];
        rebootAppByEventId(
            serviceId,
            tenantName, 
            serviceAlias, 
            eventId
        ).done(function(data){
            dfd.resolve(data);
        }).fail(function(data){
            dfd.reject(data);
        })
    })
    .fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}



/*
    获取应用的详情
*/
export const getAppDetail = (tenantName, serviceAlias) => {
    return http({
        type: "GET",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/detail/",
        showLoading: false
    })
}

/*
    部署应用, 需要传入eventId
*/
export const deployAppByEventId = (categroy, tenantName, serviceAlias, eventId) => {
    var dfd = $.Deferred();
    
    //if (categroy !== "application") {
    //   Msg.warning("暂时不支持");
    //   dfd.reject();
    //}else{
   
        http({
            type: "POST",
            url: "/ajax/" + tenantName + '/' + serviceAlias + "/app-deploy/",
            data: {
                event_id: eventId
            }
        }).done(function(data){
            if (data["status"] == "success") {
                dfd.resolve(data);
            } else {
                Msg.warning(lang.get(data['status'], '操作异常，请稍后重试'));
                dfd.reject(data);
            }
        }).fail(function(data){
            dfd.reject(data);
        })
    //}
    return dfd;
}

/*
 部署应用, 不需要传入eventId
*/
export function deployApp(categroy, tenantName, serviceAlias){
    var dfd = $.Deferred();
   
    // if (categroy !== "application") {
    //  Msg.warning("暂时不支持");
    //  dfd.reject();
    //}else{
   
        getEventId(
            tenantName, 
            serviceAlias, 
            'deploy'
        ).done(function(data){
            var event = data["event"];
            var eventId = event["event_id"];
            
            deployAppByEventId(
                categroy, 
                tenantName, 
                serviceAlias, 
                eventId
            ).done(function(data){
                dfd.resolve(data);
            }).fail(function(data){
                dfd.reject();
            })

        }).fail(function(data){
            dfd.reject();
        })
    
    //}

    
    return dfd;
    
}


/*
    获取应用实例
*/
export const getAppContainer = (tenantName, serviceAlias) => {
    var dfd = $.Deferred();
    http({
        type: "GET",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/docker",
        showLoading:false
    }).done(function(data){
        dfd.resolve(data);
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    根据 tenantName, serviceAlias, c_id 和 host_ip 创建容器节点的socket连接地址， 用于容器节点管理
*/

export const createAppContainerSocket = (tenantName, serviceAlias, c_id, h_ip) => {
    var dfd = $.Deferred();
    http({
        type: "POST",
        url: "/ajax/"+tenantName+"/"+serviceAlias+"/docker",
        data: {
            "c_id": c_id,
            "h_id": h_ip
        }
    }).done(function(data){
        if (data["success"]) {
            dfd.resolve(data);
        } else {
            Msg.warning("操作失败");
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}


/*
    查询应用内存包月信息

    如果硬盘已经设置过包月，  则这时内存包月不能再选包月时长， 而是根据硬盘的包月时长直接进行付款
*/

export const getMemoryMonthlyInfo = (tenantName, serviceAlias) => {
    var dfd = $.Deferred();
    http({
        type : "get",
        url : "/ajax/"+tenantName+"/"+serviceAlias+"/memory-pay-method"
    }).done(function(data){

        //不支持
        if(data.status === 'unsupport'){
            Msg.warning(data,info);
            dfd.reject(data);
            return;
        }

        if(data.status === 'success'){

            //硬盘还没有选择包月，  内存包月可以选择时长的情况
            if(data["choosable"])
            {   
                //当前内存一个月需要的钱数
                data.oneMonthMoney = (data["memory_unit_fee"]*data["memory"]*24*30/1024).toFixed(2);
            }
            //硬盘已经选择包月，  内存包月直接付款的情况
            else{
                //当前包月剩余总小时数
                var remainTotalHour = data.remainTotalHour = data["left_hours"];
                //当前包月换算成剩余的天数
                var remainDay = data.remainDay = parseInt(remainTotalHour/24);
                //当前包月换算成天数后的剩余小时数
                var remainHour = data.remainHour = remainTotalHour%24;
                //要付款的钱数
                data.toPayMoney = data["memory_fee"];
            }
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

/*
    应用内存包月提交接口

    @monthNum 月数
    @payMoney 金额

    包月: method = post2pre
    包月直接付款: method = pre2post
*/

const appMemoryMonthlyAjax = (tenantName, serviceAlias,method ,monthNum, payMoney) => {
    var dfd = $.Deferred();
    http({
        type : "post",
        url : "/ajax/"+tenantName+"/"+serviceAlias+"/memory-pay-method",
        data : {
            update_method : method,
            pay_period : monthNum,
            pay_money : payMoney
        }
    }).done(function(data){
        if( data["status"] == "success" )
        {
            Msg.success("操作成功");
            dfd.resolve(data);
        }
        else if( data["status"] == "not_enough" ){
            Msg.warning("余额不足，请充值");
        }
        else{
            Msg.warning(data["info"]);
        }

        if(data.status !== 'success'){
            dfd.reject(data);
        }
    }).fail(function(data){
         dfd.reject(data);
    })
    return dfd;
}

//内存包月接口
export const appMemoryMonthly = (tenantName, serviceAlias,monthNum, payMoney) => {
    return appMemoryMonthlyAjax(tenantName, serviceAlias, 'post2pre' ,monthNum, payMoney)
}


/*
    获取增加包月时长时的信息， 比如获取每个月的费用
*/

export const getAppMonthlyInfo =(tenantName, serviceAlias) => {
    var dfd = $.Deferred();
    http({
        type : "get",
        url : "/ajax/"+tenantName+"/"+serviceAlias+"/postpone"
    }).done(function(data){
        if(data.status === 'success') {
            data.oneMonthMoney = (data["unit_price"]*24*30).toFixed(2);
            dfd.resolve(data);
        }else {
            Msg.warning(data.info || '获取包月信息失败， 请稍后再试');
            dfd.reject(data);
        }

    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    提交应用增加包月时长
*/

export const appMonthlyAddTime = (tenantName, serviceAlias, monthNum) => {
    var dfd = $.Deferred();
    http({
        type : "post",
        url : "/ajax/"+tenantName+"/"+serviceAlias+"/postpone",
        data : {
            pay_period : monthNum
        }
    }).done(function(data){
        
        if(data.status === 'success') {
            Msg.success('操作成功!')
            dfd.resolve(data);
        }else if(data.status === 'not_enough') {
            Msg.warning("余额不足, 请充值");
        }else {
            Msg.warning(data.info);
        }

        if(data.status !== 'success') {
            dfd.reject(data);
        }

    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    获取硬盘包月信息
*/

export const getDiskMonthlyInfo = (tenantName, serviceAlias) => {
    var dfd = $.Deferred();
    http({
        type : "get",
        url : "/ajax/"+tenantName+"/"+serviceAlias+"/disk-pay-method"
    }).done(function(data){

        if(data.status === 'success') {
            //内存包月未设置，则这里可以选择包月的时长
            if(data.choosable) {

                //硬盘每月每G 需要花费的金额
                data.oneMonthOneGmoney = data["disk_unit_fee"] * 24 * 30;

            //内存包月以设置， 则这里不可以选择包月的时长
            }else{
                //当前包月剩余总小时数
                var remainTotalHour = data.remainTotalHour = data["left_hours"];
                //当前包月换算成剩余的天数
                var remainDay = data.remainDay = parseInt(remainTotalHour/24);
                //当前包月换算成天数后的剩余小时数
                var remainHour = data.remainHour = remainTotalHour%24;
                //要付款的钱数,  1G硬盘每小时的费用*剩余的小时数
                data.oneGmoney =(data["disk_unit_fee"]*data["left_hours"]).toFixed(2);
            }
            dfd.resolve(data);
            
        }else{
            Msg.warning(data.info || '获取硬盘包月信息失败，请稍后再试');
            dfd.reject(data);
        }

    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}


/*
    应用硬盘包月和预付款包月接口， 通过method区分

    @monthNum 月数
    @payMoney 金额

    包月提交: method = post2pre
    预付款 : method = pre2post
*/

const appDiskMonthlyAjax = (tenantName, serviceAlias ,method ,diskSize, monthNum) => {
    var dfd = $.Deferred();
    http({
        type : "post",
        url : "/ajax/"+tenantName+"/"+serviceAlias+"/disk-pay-method",
        data : {
            update_method : method,
            pay_period : monthNum,
            pay_disk : diskSize
        }
    }).done(function(data){
        if( data["status"] == "success" )
        {
            Msg.success("操作成功");
            dfd.resolve(data);
        }
        else if( data["status"] == "not_enough" ){
            Msg.warning("余额不足, 请充值");
        }
        else{
            Msg.warning(data["info"]);
        }

        if(data.status !== 'success'){
            dfd.reject(data);
        }
    }).fail(function(data){
         dfd.reject(data);
    })
    return dfd;
}

/*
    硬盘包月
*/
export const appDiskMonthly = (tenantName, serviceAlias, diskSize, monthNum) => {
    return appDiskMonthlyAjax(tenantName, serviceAlias, 'post2pre', diskSize, monthNum)
}

/*
    硬盘包月预付款
*/
export const appDiskMonthlyNoMonth = (tenantName, serviceAlias, diskSize) => {
    return appDiskMonthlyAjax(tenantName, serviceAlias, 'pre2post', diskSize)
}

/*
    获取应用内存包月 扩容信息
*/

export const appMemoryMonthlyExpansionInfo = (tenantName, serviceAlias) => {
    var dfd = $.Deferred();
    http({
        type : "get",
        url : "/ajax/"+tenantName+"/"+serviceAlias+"/service-extend"
    }).done(function(data){

        if(data.status === 'success'){

            //是否可以设置节点数量
            data.canSetNodeNums = !!data["node_choosable"];
            //单位最小的金额, 算总金额的时候， 拿选择的总内存数乘它
            data.unitMoney = (data["memory_unit_fee"]*data["left_hours"]/1024).toFixed(2);
            data.minMemory = data['app_min_memory'];
            //单条内存最大8g, 
            var oneNodeMaxMemory = 1024 * 8+128;
            data.maxMemory = data['app_max_memory'] > oneNodeMaxMemory ? oneNodeMaxMemory : data['app_max_memory'];
            
            data.minNode = data['min_node'];
            data.serviceMemory = data["service_memory"];
            data.showMoney = data["show_money"];
            if(data.showMoney){
                data.payMoney = data.unitMoney * (data.minNode * data.minMemory - data.serviceMemory);
            }
            dfd.resolve(data);
        } else {
            Msg.warning(data.info || '获取扩容信息失败， 请稍后再试');
            dfd.reject(data);
        }

    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*

    提交内存扩容
*/
export const postMemoryMonthlyExpansion = (tenantName, serviceAlias, memory, nodeNum) => {
    var dfd = $.Deferred();
    http({
        type : "post",
        url : "/ajax/"+tenantName+"/"+serviceAlias+"/service-extend",
        data : {
            node_num : nodeNum,
            node_memory : memory
        }
    }).done(function(data){

        if(data.status === 'success') {
            Msg.success('操作成功');
            dfd.resolve(data);
        }else if(data.status === 'not_enough'){
            Msg.warning("余额不足, 请充值");
        }else {
            Msg.warning(data["info"]);
        }

        if(data.status !== 'success') {
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    获取当前应用的健康监测信息
*/
export const getHealthCheckInfo = (tenantName, serviceAlias, mode) => {
    var dfd = $.Deferred();
    http2({
      url:'/ajax/'+tenantName+'/'+serviceAlias+'/probe?mode='+mode,
      type:'get',
      isTipError: false
    }).done(function(data){
        if(data.code >= 200 && data.code < 300){
            dfd.resolve(data);
        }else{
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    获取应用运行时健康监测信息
*/
export const getRunningHealthCheckInfo = (tenantName, serviceAlias) => {
    return getHealthCheckInfo(tenantName, serviceAlias, 'liveness')
}

/*
    获取应用启动时健康监测信息
*/
export const getStartingHealthCheckInfo = (tenantName, serviceAlias) => {
    return getHealthCheckInfo(tenantName, serviceAlias, 'readiness')
}

/*
  激活/禁用健康监测　
*/
export const activeAndDisableHealthCheck = (tenantName, serviceAlias, probe_id) => {
  return http({
       url:'/ajax/'+tenantName+'/'+serviceAlias+'/probe/'+probe_id+'/update_used',
       type:'POST'
  })
}

/*
    应用批量续费包月、包月
*/

const appBatchMonthly = (tenantName, data) => {
    var dfd = $.Deferred();
    http({
        type:'post',
        url:"/apps/"+tenantName+"/service-renew/",
        data:data
    }).done(function(data){
        if (data.code == '0000'){
            Msg.success('操作成功!');
            dfd.resolve(data);
        }else{
            Msg.warning(data.msg_show);
            dfd.reject(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}

/*
    批量续费
*/
export const appBatchRenew = (tenantName, serviceIdsArr = [], monthNum) => {
    var arr = [];
    for(var i=0;i<serviceIdsArr.length;i++){
        arr.push({
            service_id: serviceIdsArr[i],
            month_num: monthNum || ''
        });
    }
    var data = {
        data: JSON.stringify(arr),
        action: 'batch'
    }
    return appBatchMonthly(tenantName, data)
}


/*
    批量内存包月， 不选择时长
*/
export const appBatchMemoryWithoutTime = (tenantName, serviceIdsArr = []) => {
    var arr = [];
    for(var i=0;i<serviceIdsArr.length;i++){
        arr.push({
            service_id: serviceIdsArr[i]
        });
    }
    var data = {
        data: JSON.stringify(arr),
        action: 'batch-memory',
        type: 'prepaid_disk'
    }
    return appBatchMonthly(tenantName, data)
}

/*
    批量内存包月， 选择时长
*/
export const appBatchMemoryWitTime = (tenantName, serviceIdsArr = [], monthNum) => {
    var arr = [];
    for(var i=0;i<serviceIdsArr.length;i++){
        arr.push({
            service_id: serviceIdsArr[i],
            month_num: monthNum || ''
        });
    }
    var data = {
        data: JSON.stringify(arr),
        action: 'batch-memory',
        type: 'postpaid_disk'
    }
    return appBatchMonthly(tenantName, data)
}


/*
    批量硬盘包月， 不选择时长
*/
export const appBatchDiskWithoutTime = (tenantName, serviceIdsArr = [], disk) => {
    var arr = [];
    for(var i=0;i<serviceIdsArr.length;i++){
        arr.push({
            service_id: serviceIdsArr[i],
            disk: disk
        });
    }
    var data = {
        data: JSON.stringify(arr),
        action: 'batch-disk',
        type: 'prepaid_memory'
    }
    return appBatchMonthly(tenantName, data)
}

/*
    批量硬盘包月， 选择时长
*/
export const appBatchDiskWithTime = (tenantName, serviceIdsArr = [], disk, monthNum) => {
    var arr = [];
    for(var i=0;i<serviceIdsArr.length;i++){
        arr.push({
            service_id: serviceIdsArr[i],
            disk: disk,
            month_num: monthNum || ''
        });
    }
    var data = {
        data: JSON.stringify(arr),
        action: 'batch-disk',
        type: 'postpaid_memory'
    }
    return appBatchMonthly(tenantName, data);
}

/*
    获取未安装的插件
*/
export const getNotInstalledPlugin = (tenantName, serviceAlias) => {
    var url = '/ajax/'+tenantName+'/'+serviceAlias+'/appdetails/?fr=plugin';
    return http({
       url:url,
       type:'get'
    })
}



/*
 获取应用平均响应时间监控数据
 start没有值代表请求的瞬时数据
*/
export const getAppRequestTime = (data={tenantName, serviceAlias, serviceId, start, end, step:7}) => {
    if(data.start){
        return http({
            url: '/ajax/' + data.tenantName + '/' + data.serviceAlias + '/query_range',
            type:'get',
             showLoading: false,
            data:{
                query:'sum(app_requesttime{service_id="'+data.serviceId+'",mode="avg"})',
                start: data.start,
                end: data.end || (new Date().getTime()/1000),
                step: data.step
            }
        })
    }else{
        return http({
            url: '/ajax/' + data.tenantName + '/' + data.serviceAlias + '/query',
            type:'get',
             showLoading: false,
            data:{
                query:'sum(app_requesttime{service_id="'+data.serviceId+'",mode="avg"})'
            }
        })
    }
}

/*
 获取应用吞吐率监控数据
*/
export const getAppRequest = (data={tenantName, serviceAlias, serviceId, start, end, step:7}) => {
     if(data.start){
        return http({
            url: '/ajax/' + data.tenantName + '/' + data.serviceAlias + '/query_range',
            type:'get',
            showLoading: false,
            data:{
                query:'sum(rate(app_request{method="total",service_id="'+data.serviceId+'"}[30s]))',
                start: data.start,
                end: data.end || (new Date().getTime()/1000),
                step: data.step
            }
        })
    }else{
        return http({
            url: '/ajax/' + data.tenantName + '/' + data.serviceAlias + '/query',
             showLoading: false,
            type:'get',
            data:{
                query:'sum(rate(app_request{service_id="'+data.serviceId+'"}[15s]))'
            }
        })
    }
}

/*
 获取应用在线人数监控数据
*/
export const getAppOnlineNumber = (data={tenantName, serviceAlias, serviceId, start, end, step:7}) => {
    if(data.start){
        return http({
            url: '/ajax/' + data.tenantName + '/' + data.serviceAlias + '/query_range',
            type:'get',
             showLoading: false,
            data:{
                query:'sum(app_requestclient{service_id="'+data.serviceId+'"})',
                start: data.start,
                end: data.end || (new Date().getTime()/1000),
                step: data.step
            }
        })
    }else{
        return http({
            url: '/ajax/' + data.tenantName + '/' + data.serviceAlias + '/query',
            type:'get',
             showLoading: false,
            data:{
                query:'sum(app_requestclient{service_id="'+data.serviceId+'"})'
            }
        })
    }
}



