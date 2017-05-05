function goto_deploy(tenantName, service_alias) {
    window.location.href = "/apps/" + tenantName + "/" + service_alias
        + "/detail/"
}

function service_oneKeyDeploy(categroy, serviceAlias, tenantName, isreload) {

    event_id = createEvents(tenantName, serviceAlias, "deploy")

    if (event_id == "") {
        return false
    }
    connectSocket(event_id,"deploy");

    $("#onekey_deploy").attr('disabled', "true")
    _url = "/ajax/" + tenantName + '/' + serviceAlias + "/app-deploy/"
    if (categroy == "application") {
        _url = "/ajax/" + tenantName + '/' + serviceAlias + "/app-deploy/"
    } else {
        swal("暂时不支持")
        return;
    }
    $.ajax({
        type: "POST",
        url: _url,
        cache: false,
        data: "event_id=" + event_id,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            var dataObj = msg;
            if (dataObj["status"] == "success") {
                swal("操作成功");
            } else if (dataObj["status"] == "owed") {
                swal("余额不足请及时充值")
            } else if (dataObj["status"] == "expired") {
                swal("试用已到期")
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
                $("#onekey_deploy").removeAttr("disabled")
            }
            if (isreload == 'yes') {
                forurl = "/apps/" + tenantName + "/" + serviceAlias
                    + "/detail/"
                window.open(forurl, target = "_parent")
            }
            $("#onekey_deploy").removeAttr("disabled")
        },
        error: function () {
            $("#onekey_deploy").removeAttr("disabled")
            swal("系统异常");
        }
    });
}

//获取evevts
function createEvents(name, service, action) {
    var currentEventID = ""
    var ok = false
    $.ajax({
        type: "POST",
        url: "/ajax/" + name + '/' + service + "/events",
        data: "action=" + action,
        cache: false,
        async: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (data) {
            if (data["status"] == "often") {
                swal("上次操作进行中，请稍后！");
                return ""
            } else if (data["status"] == "success") {
                event = data["event"]
                currentEventID = event["event_id"]
                //var tmpLog = event["event_start_time"] + " @" + event["user_name"] + event["event_type"]
                //tmpLog = "<label style='line-height: 21px;'>" + tmpLog + "</label><p id='compile_" + event["event_id"] + "' style='display: none;line-height: 21px;'></p>"
                //tmpLog = "<div id='event_" + event["event_id"] + "'>" + tmpLog + "</div>"
                //$("#keylog").children("div:first-child").before(tmpLog)
                ok = true

                var arr = event["event_start_time"].split("T");
                var date = arr[0];
                var time = arr[1].split('.')[0];
                var type_json = {
                    "deploy" : "部署",
                    "restart" : "启动",
                    "delete" : "删除",
                    "stop" : "关闭",
                    "HorizontalUpgrade" : "水平升级",
                    "VerticalUpgrade" : "垂直升级",
                    "callback" : "回滚",
                    "create" : "创建"
                }

                var str_log = '<li><time class="tl-time"><h4>'+time+'</h4><p>'+date+'</p></time><i class="fa bg-grey tl-icon"></i><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>'+type_json[event["event_type"]]+'中</span><div class="user"><p>@'+event["user_name"];
                str_log += '</p><p class="ajax_log" data-log="'+event["event_id"]+'" style="display: block;">查看日志</p><p class="hide_log">收起</p></div></div><div class="panel-body"><div class="log log_'+event["event_id"]+'"></div></div></div></div></li>'

                if( event["event_type"] == "deploy" )
                {
                    str_log += '<li><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>当前版本('+event["old_deploy_version"]+')</span>';
                    str_log += '<div class="user"><button class="btn btn-success callback_version" data-version="'+event["old_deploy_version"]+'">回滚到此版本</button></div></div></div></div></li>'

                }

                $(str_log).prependTo($("#keylog ul"));
                ajax_getLog();
                callback_version();
            } else {
                swal("系统异常！");
            }

        },
        error: function () {
            swal("系统异常");
        }
    });
    if (ok) {
        return currentEventID
    }
    return ""
}
function ajax_getLog(){
    $(".ajax_log").off('click');
    $(".ajax_log").click(function(){
        var event_id = $(this).attr("data-log");
        do_logshow(event_id);
        $(this).hide();
        $(this).parent().find('.hide_log').show();
        $(".log_" + event_id + "").addClass('log_height');
    });
    $(".hide_log").off('click');
    $(".hide_log").click(function(){
        var onOff = $(this).parents('.panel').find('.log').hasClass('log_height');
        if(onOff)
        {
            $(this).parents('.panel').find('.log').removeClass('log_height');
            $(this).html("查看日志");
        }
        else{
            $(this).parents('.panel').find('.log').addClass('log_height');
            $(this).html("收起");
        }
    });
}
function callback_version(){
    var tenantName = $("#tenantName").val();
    var service_alias = $("#service_alias").val();
    $(".callback_version").off('click');
    $(".callback_version").click(function(){
        var that = $(this);
        swal({
            title: "确定恢复当前版本吗？",
            type: "warning",
            showCancelButton: true,
            confirmButtonColor: "#DD6B55",
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            closeOnConfirm: false,
            closeOnCancel: false
        }, function (isConfirm) {
            if (isConfirm) {
                var event_id = createEvents(tenantName, service_alias , "callback");
                connectSocket(event_id,"callback");
                do_rollback(event_id,that.attr("data-version"));
            } else {
                swal.close();
            }
        });

    });
}
var ws = null
function connectSocket(event_id,action) {
    var url = $("#event_websocket_uri").val();
    ws = new WebSocket(url);
    var type_json = {
        "deploy" : "部署",
        "restart" : "启动",
        "delete" : "删除",
        "stop" : "关闭",
        "HorizontalUpgrade" : "水平升级",
        "VerticalUpgrade" : "垂直升级",
        "callback" : "回滚",
        "create" : "创建"
    }
    ws.onopen = function (evt) {
        ws.send("event_id=" + event_id);
    }
    ws.onmessage = function (evt) {
        //var m = jQuery.parseJSON(evt.data)
        if( evt.data == "ok" )
        {
            return;
        }
        var m = JSON.parse(evt.data)
        var arr = m.time.split('.')[0];
        var time1 = arr.split('T')[0];
        var time2 = arr.split('T')[1].split('Z')[0];
        tmpLog = "<p>" + time1 + " " + time2 + m.message + "</p>";
        //$("#keylog").children("div:first-child").before(tmpLog)

        $(tmpLog).prependTo($("#keylog .log").eq(0));
        if( m.step == "callback" || m.step == "last" )
        {
            ws.close();
            console.log(action);
            if( m.status == "success" )
            {
                var str = type_json[action]+"成功";
                $("#keylog li").eq(0).find(".fa").removeClass("bg-grey").addClass("bg-success");
            }
            else{
                $("#keylog li").eq(0).find(".fa").removeClass("bg-grey").addClass("bg-danger");
                var str = type_json[action]+"失败("+ m.message+")";
            }
            $("#keylog .panel").eq(0).find(".panel-heading span").html(str);
        }
    }
    ws.onclose = function (evt) {
        console.log("连接关闭");
    }
    ws.onerror = function (evt) {
        console.log("WebSocket错误");
    }
}

function closeSocket() {
    if (!ws) {
        return false;
    }
    ws.close();
    return false;
}

function service_my_onOperation(service_id, service_alias, tenantName) {
    $("#operate_" + service_id).attr('disabled', "true")
    var taction = $("#operate_" + service_id).attr("data" + service_id)
    if (taction != "stop" && taction != "restart") {
        swal("系统异常");
        window.location.href = window.location.href;
    }
    $.ajax({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + service_alias + "/manage",
        data: "service_id=" + service_id + "&action=" + taction,
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            var dataObj = msg
            if (dataObj["status"] == "success") {
                swal("操作成功")
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
            $("#operate_" + service_id).removeAttr("disabled")
        },
        error: function () {
            swal("系统异常");
            $("#operate_" + service_id).removeAttr("disabled")
        }
    })
}

// 服务重启关闭
function service_onOperation(service_id, service_alias, tenantName) {

    var taction = $("#service_status_value").val()
    if (taction != "stop" && taction != "restart") {
        swal("参数异常");
        window.location.href = window.location.href;
    }
    event_id = createEvents(tenantName, service_alias, taction)
    if (event_id == "") {
        swal("创建操作错误");
        return false
    }
    connectSocket(event_id,taction);

    $("#service_status_operate").attr('disabled', "true")
    $.ajax({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + service_alias + "/manage",
        data: "service_id=" + service_id + "&action=" + taction + "&event_id=" + event_id,
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            var dataObj = msg
            if (dataObj["status"] == "success") {
                swal("操作成功")
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
            $("#service_status_operate").removeAttr("disabled")
        },
        error: function () {
            swal("系统异常");
            $("#service_status_operate").removeAttr("disabled");
        }
    })
}

var csrftoken = $.cookie('csrftoken');
var tenantName = $('#mytags').attr('tenant');
var serviceAlias = $('#mytags').attr('service');

$(document).ready(
    function () {
        log_page();
        if ($('#git_branch').length) {
            $.ajax({
                type: "get",
                url: "/ajax/" + tenantName + "/" + serviceAlias + "/branch",
                cache: false,
                success: function (data) {
                    for (var i in data.branchs) {
                        var opt = $("<option/>").val(data.branchs[i]).html(data.branchs[i])
                        if (data.branchs[i] == data.current) {
                            opt.prop('selected', true)
                        }
                        $('#git_branch').prepend(opt)
                    }
                }
            })
        }

    }
)

// 服务分支
function service_branch_change(tenantName, service_alias) {
    var branch = $("#git_branch").val();
    $.ajax({
        type: "post",
        url: "/ajax/" + tenantName + "/" + service_alias + "/branch",
        data: "branch=" + branch,
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            swal("切换完毕, 下次部署后生效");
        },
        error: function () {
            swal("系统异常,请重试");
        }
    })
}

// 域名绑定
function domainSubmit(action, service_id, tenantName, service_alias, port_name, domain_link) {
    if (action != "start" && action != "close") {
        swal("参数异常");
        window.location.href = window.location.href;
    }
    //绑定端口
    var domain_name = domain_link != "" ? domain_link : $("#service_app_name_" + port_name).val();
    console.log(domain_name);
    var multi_port_bind = port_name;
    console.log(multi_port_bind);
    if (multi_port_bind == "") {
        swal("选择有效的端口");
        return;
    }
    if (domain_name == "") {
        swal("输入有效的域名");
        return;
    }
    $.ajax({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + service_alias + "/domain",
        data: "service_id=" + service_id + "&domain_name=" + domain_name
        + "&action=" + action + "&multi_port_bind=" + multi_port_bind,
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            var dataObj = msg
            if (dataObj["status"] == "success") {
                swal("操作成功")
                if (window.location.href.indexOf("fr=") < 0) {
                    window.location.href = window.location.href
                        + "?fr=settings";
                } else {
                    window.location.href = window.location.href
                }
            } else if (dataObj["status"] == "limit") {
                swal("免费用户不允许")
            } else if (dataObj["status"] == "exist") {
                swal("域名已存在")
            } else {
                swal("操作失败")
            }
        },
        error: function () {
            swal("系统异常");
        }
    })
}

// 服务垂直升级
function service_upgrade(tenantName, service_alias) {
    event_id = createEvents(tenantName, service_alias, "VerticalUpgrade")
    if (event_id == "") {
        swal("创建垂直升级操作错误");
        return false
    }
    var service_min = $("#serviceMemorys").val();
    memory = service_min
    cpu = 20 * (service_min / 128)
    $.ajax({
        type: "post",
        url: "/ajax/" + tenantName + "/" + service_alias + "/upgrade",
        data: "action=vertical&memory=" + memory + "&cpu=" + cpu + "&event_id=" + event_id,
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            var dataObj = msg;
            if (dataObj["status"] == "success") {
                swal("设置成功")
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
        },
        error: function () {
            swal("系统异常,请重试");
        }
    })
}

// 服务水平升级
function app_upgrade(tenantName, service_alias) {
    event_id = createEvents(tenantName, service_alias, "HorizontalUpgrade")
    if (event_id == "") {
        swal("创建水平升级操作错误");
        return false
    }
    var service_min_node = $("#serviceNods").val();
    if (service_min_node >= 0) {
        $.ajax({
            type: "post",
            url: "/ajax/" + tenantName + "/" + service_alias + "/upgrade/",
            data: "action=horizontal&node_num=" + service_min_node + "&event_id=" + event_id,
            cache: false,
            beforeSend: function (xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function (msg) {
                var dataObj = msg;
                if (dataObj["status"] == "success") {
                    swal("设置成功")
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
            },
            error: function () {
                swal("系统异常,请重试");
            }
        })
    }
}

// 服务扩容方式修改
function extends_upgrade(tenantName, service_alias) {
    var extend_method = $("#extend_method").val();
    if (extend_method != "") {
        $.ajax({
            type: "post",
            url: "/ajax/" + tenantName + "/" + service_alias + "/upgrade/",
            data: "action=extend_method&extend_method=" + extend_method,
            cache: false,
            beforeSend: function (xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function (msg) {
                var dataObj = msg;
                if (dataObj["status"] == "success") {
                    swal("设置成功")
                } else if (dataObj["status"] == "owed") {
                    swal("余额不足请及时充值")
                } else if (dataObj["status"] == "expired") {
                    swal("试用已到期")
                } else if (dataObj["status"] == "often") {
                    swal("操作正在进行中，请稍后")
                } else if (dataObj["status"] == "no_support") {
                    swal("当前服务不支持修改")
                } else {
                    swal("设置失败")
                }
            },
            error: function () {
                swal("系统异常,请重试");
            }
        })
    }
}
//下页日志
function log_page(){
    $(".load_more").click(function(){
        var that = $(this);
        var num = $(this).attr("data-num");
        var tenantName = $("#tenantName").val();
        var serviceAlias = $("#serviceAlias").val();
        $.ajax({
            type: "GET",
            url: "/ajax/"+tenantName+"/"+serviceAlias+"/events?page="+num,
            data: "action=operate",
            cache: false,
            beforeSend: function (xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function (msg) {
                that.attr("data-num",num++);
                var dataObj = msg;
                var showlog = ""
                var logList = dataObj["log"]
                if (typeof(logList) != "undefined") {
                    var type_json = {
                        "deploy" : "部署",
                        "restart" : "启动",
                        "stop" : "关闭",
                        "delete" : "删除",
                        "HorizontalUpgrade" : "水平升级",
                        "VerticalUpgrade" : "垂直升级",
                        "callback" : "回滚",
                        "create" : "创建"
                    }
                    var status_json = {
                        "success" : "成功",
                        "failure" : "失败",
                        "timeout" : "超时"
                    }
                    var final_status_json = {
                        "complate" : "完成",
                        "timeout" : "超时"
                    }
                    var bg_color = {
                        "success" : "bg-success",
                        "failure" : "bg-danger",
                        "timeout" : "bg-danger"
                    }
                    for (var i = 0; i < logList.length; i++) {
                        var log = logList[i]
                        if (i == 0 && (log["final_status"] == "")) {
                            connectSocket(log["event_id"],log["type"]);
                        }
                        var arr = log["start_time"].split("T");
                        var date = arr[0];
                        var time = arr[1];
                        var status;
                        var color;
                        if( log["final_status"] == "complete" )
                        {
                            status = status_json[log["status"]];
                            color = bg_color[log["status"]];
                        }
                        else if( log["final_status"] == "timeout" ){
                            status = final_status_json[log["final_status"]];
                            color = 'bg-danger';
                        }
                        else{
                            status = "进行中";
                            color = 'bg-grey';
                        }
                        if( log["status"] == "failure" )
                        {
                            var str_log = '<li><time class="tl-time"><h4>'+time+'</h4><p>'+date+'</p></time><i class="fa '+color+' tl-icon"></i><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>'+type_json[log["type"]]+status+log["message"]+'</span><div class="user"><p>@'+log["user_name"]+'</p><p class="ajax_log" data-log="'+log["event_id"];
                        }
                        else{
                            var str_log = '<li><time class="tl-time"><h4>'+time+'</h4><p>'+date+'</p></time><i class="fa '+color+' tl-icon"></i><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>'+type_json[log["type"]]+status+'</span><div class="user"><p>@'+log["user_name"]+'</p><p class="ajax_log" data-log="'+log["event_id"];
                        }
                        str_log += '">查看日志</p><p class="hide_log">收起</p></div></div><div class="panel-body"><div class="log log_'+log["event_id"]+'"></div></div></div></div></li>'
                        if( log["type"] == "deploy" && log["old_deploy_version"] != "" )
                        {
                            str_log += '<li><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>当前版本('+log["old_deploy_version"]+')</span>';
                            str_log += '<div class="user"><button class="btn btn-success callback_version" data-version="'+log["old_deploy_version"]+'">回滚到此版本</button></div></div></div></div></li>'
                        }
                        $(str_log).appendTo($("#keylog ul"));
                        ajax_getLog();
                        callback_version();
                    }
                }
            },
            error: function () {
                //swal("系统异常");
            }
        })
    });
}

// 服务删除
function delete_service(tenantName, service_alias) {

    var code_from = $("#cur_delete_service").attr("data-code");
    var notify_text = "确定删除当前服务吗？";
    if (code_from == "gitlab_new") {
        notify_text = "关联git代码将同步删除，确定删除当前服务吗？"
    }
    swal({
        title: notify_text,
        type: "warning",
        showCancelButton: true,
        confirmButtonColor: "#DD6B55",
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        closeOnConfirm: false,
        closeOnCancel: false
    }, function (isConfirm) {
        if (isConfirm) {
            event_id = createEvents(tenantName, service_alias, "delete")
            if (event_id == "") {
                swal("创建删除操作错误");
                return false
            }
            $.ajax({
                type: "POST",
                url: "/ajax/" + tenantName + "/" + service_alias + "/manage/",
                data: "action=delete&event_id=" + event_id,
                cache: false,
                beforeSend: function (xhr, settings) {
                    var csrftoken = $.cookie('csrftoken');
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                    swal({
                        title: "正在执行删除操作，请稍候...",
                        text: "5秒后自动关闭",
                        timer: 5000,
                        showConfirmButton: false
                    });
                },
                success: function (msg) {
                    var dataObj = msg;
                    if (dataObj["status"] == "success") {
                        swal("操作成功");
                        window.location.href = "/apps/" + tenantName
                    } else if (dataObj["status"] == "often") {
                        swal("上次操作正在进行中，稍后再试")
                    } else if (dataObj["status"] == "published") {
                        swal("关联了已发布服务, 不可删除")
                    } else if (dataObj["status"] == "evn_dependency") {
                        var dep_service = dataObj["dep_service"]
                        if (typeof(dep_service) == "undefined") {
                            swal("当前服务被环境依赖不能删除");
                        } else {
                            swal("当前服务被(" + dep_service + ")环境依赖不能删除");
                        }
                    } else if (dataObj["status"] == "mnt_dependency") {
                        var dep_service = dataObj["dep_service"]
                        if (typeof(dep_service) == "undefined") {
                            swal("当前服务被挂载依赖不能删除");
                        } else {
                            swal("当前服务被(" + dep_service + ")挂载依赖不能删除");
                        }
                    } else if (dataObj["status"] == "payed") {
                        swal("您尚在包月期内无法删除应用")
                    }
                    else {
                        swal("操作失败");
                    }
                },
                error: function () {
                    swal("系统异常");
                }
            });
        } else {
            swal.close();
        }
    });
}

function buid_relation(action, curServiceName, depServiceName, tenantName) {
    if (action != "add" && action != "cancel") {
        swal("系统异常");
        window.location.href = window.location.href;
    }
    $.ajax({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + curServiceName + "/relation",
        data: "dep_service_alias=" + depServiceName + "&action=" + action,
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            var dataObj = msg
            if (dataObj["status"] == "success") {
                swal("操作成功")
                if (window.location.href.indexOf("fr=") < 0) {
                    window.location.href = window.location.href
                        + "?fr=relations";
                } else {
                    window.location.href = window.location.href
                }
            } else {
                swal("操作失败")
            }
        },
        error: function () {
            // swal("系统异常");
        }
    })
}

function add_new_attr(service_id, port) {
    var msg = ''
    msg = msg + '<tr>'
    msg = msg + '<td><input name ="' + service_id + '_name" value=""></td>'
    msg = msg + '<td><input name ="' + service_id + '_attr_name" value=""></td>'
    msg = msg + '<td><input name ="' + service_id + '_attr_value" value=""></td>'
    msg = msg + '<td><input type="hidden" name ="' + service_id + '_attr_id" value="0"><button type="button" class="btn btn-success btn-xs" onclick="attr_delete(this);">删除</button></td>'
    msg = msg + '</tr>'
    $("#envVartable tr:last").after(msg);
}

function attr_save(service_id, tenant_name, service_name) {
    var id_obj = $('input[name=' + service_id + '_serviceNoChange]');
    var id = [];
    for (var i = 0; i < id_obj.length; i++) {
        id.push(id_obj[i].value)
    }
    var reg = /[\u4E00-\u9FA5\uF900-\uFA2D]/
    var regother = /[\uFF00-\uFFEF]/
    var nochange_name_obj = $('input[name=' + service_id + '_nochange_name]');
    var nochange_name = [];
    for (var i = 0; i < nochange_name_obj.length; i++) {
        var tmp = nochange_name_obj[i].value;
        if (reg.test(tmp) || regother.test(tmp)) {
            swal("变量名不正确");
            return false;
        }
        if (tmp == "") {
            swal("必填项不能为空");
            return false;
        } else {
            nochange_name.push(tmp)
        }
    }

    var name_obj = $('input[name=' + service_id + '_name]');
    var name = [];
    for (var i = 0; i < name_obj.length; i++) {
        if (name_obj[i].value == "") {
            swal("必填项不能为空");
            return false;
        } else {
            name.push(name_obj[i].value)
        }
    }
    var attr_name_obj = $('input[name=' + service_id + '_attr_name]');
    var attr_name = [];
    for (var i = 0; i < attr_name_obj.length; i++) {
        var tmp = attr_name_obj[i].value;
        if (reg.test(tmp) || regother.test(tmp)) {
            swal("变量名不正确");
            return false;
        }
        if (tmp == "") {
            swal("必填项不能为空");
            return false;
        } else {
            attr_name.push(tmp)
        }
    }
    var attr_value_obj = $('input[name=' + service_id + '_attr_value]');
    var attr_value = [];
    for (var i = 0; i < attr_value_obj.length; i++) {
        var tmp = attr_value_obj[i].value;
        if (reg.test(tmp) || regother.test(tmp)) {
            swal("变量名不正确");
            return false;
        }
        if (tmp == "") {
            swal("必填项不能为空");
            return false;
        } else {
            attr_value.push(tmp)
        }
    }
    var attr_id_obj = $('input[name=' + service_id + '_attr_id]');
    var attr_id = [];
    for (var i = 0; i < attr_id_obj.length; i++) {
        var tmp = attr_id_obj[i].value;
        attr_id.push(tmp)
    }
    $.ajax({
        type: "POST",
        url: "/ajax/" + tenant_name + "/" + service_name + "/envvar",
        data: "nochange_name=" + nochange_name.toString() + "&id=" + id.toString() + "&name=" + name.toString() + "&attr_name="
        + attr_name.toString() + "&attr_value=" + attr_value.toString() + "&attr_id=" + attr_id.toString(),
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            var dataObj = msg
            if (dataObj["status"] == "success") {
                swal("操作成功")
            } else {
                swal("操作失败")
            }
        },
        error: function () {
            // swal("系统异常");
        }
    })
}

function attr_delete(obj) {
    var trobj = $(obj).closest('tr');
    $(trobj).remove();
}


function buid_mnt(action, curServiceName, depServiceName, tenantName) {
    if (action != "add" && action != "cancel") {
        swal("系统异常");
        window.location.href = window.location.href;
    }
    $.ajax({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + curServiceName + "/mnt",
        data: "dep_service_alias=" + depServiceName + "&action=" + action,
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            var dataObj = msg
            if (dataObj["status"] == "success") {
                swal("操作成功")
                if (window.location.href.indexOf("fr=") < 0) {
                    window.location.href = window.location.href
                        + "?fr=relations";
                } else {
                    window.location.href = window.location.href
                }
            } else {
                swal("操作失败")
            }
        },
        error: function () {
            // swal("系统异常");
        }
    })
}

//服务更新
function service_image(service_id, service_alias, tenantName) {
    $.ajax({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + service_alias + "/upgrade",
        data: "service_id=" + service_id + "&action=imageUpgrade",
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            var dataObj = msg;
            if (dataObj["status"] == "success") {
                swal("操作成功,重启后生效")
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
        },
        error: function () {
            swal("系统异常");
        }
    })
}

//服务更新并重新启动
function service_image_reboot(service_id, service_alias, tenantName) {
    swal({
        title: "更新应用会对应用进行重新部署，期间应用可能会暂时无法提供服务，确定要更新吗？",
        type: "warning",
        showCancelButton: true,
        confirmButtonColor: "#DD6B55",
        confirmButtonText: "更新",
        cancelButtonText: "取消",
        closeOnConfirm: false,
        closeOnCancel: false
    }, function (isConfirm) {
        if (isConfirm) {
            //先使用同步请求更新应用数据
            $.ajax({
                type: "POST",
                url: "/ajax/" + tenantName + "/" + service_alias + "/upgrade",
                data: "service_id=" + service_id + "&action=imageUpgrade",
                cache: false,
                async: false,
                beforeSend: function (xhr, settings) {
                    var csrftoken = $.cookie('csrftoken');
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                },
                success: function (msg) {
                    var dataObj = msg;
                    if (dataObj["status"] == "success") {
                        $("#service_image_operate").hide();
                        // 更新应用数据成功后模拟用户点击启动按钮,重启应用
                        service_reboot(service_id, service_alias, tenantName);
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
                },
                error: function () {
                    swal("系统异常");
                }
            });

        } else {
            swal.close();
        }
    });
}

// 服务重启
function service_reboot(service_id, service_alias, tenantName) {
    $("#service_status_operate").attr('disabled', "true")
    $.ajax({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + service_alias + "/manage",
        data: "service_id=" + service_id + "&action=reboot",
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            var dataObj = msg
            if (dataObj["status"] == "success") {
                swal("操作成功")
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
            $("#service_status_operate").removeAttr("disabled")
        },
        error: function () {
            swal("系统异常");
            $("#service_status_operate").removeAttr("disabled");
        }
    });
}


function payed_upgrade(tenantName, url) {
    var current_select = "company"
    swal({
        title: "",
        text: "升级为付费用户，携手云帮一起迈向云计算的未来！",
        showCancelButton: true,
        confirmButtonColor: "#DD6B55",
        confirmButtonText: "确定升级",
        cancelButtonText: "我再想想",
        closeOnConfirm: false,
        closeOnCancel: false
    }, function (isConfirm) {
        if (isConfirm) {
            $.ajax({
                type: "POST",
                url: "/payed/" + tenantName + "/upgrade",
                data: "current_select=" + "company",
                cache: false,
                beforeSend: function (xhr, settings) {
                    var csrftoken = $.cookie('csrftoken');
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                },
                success: function (msg) {
                    var dataObj = msg
                    if (dataObj["status"] == "success") {
                        swal("操作成功")
                        window.location.href = "/apps/" + tenantName
                    } else {
                        swal("操作失败")
                    }
                },
                error: function () {
                    // swal("系统异常");
                }
            });
        } else {
            swal.close();
        }
    });
}



