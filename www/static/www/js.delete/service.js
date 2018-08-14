function MessageQueue(callback){
    this.isStarted = false;
    this.datas=[];
    this.timer=null;
    this.interval = 100;
    this.callback = callback ||function(){};
}
MessageQueue.prototype = {
    add:function(msg){
        this.datas.push(msg);
        if(!this.isStarted){
            this.start();
        }
    },
    start:function(){
        var self = this;
        this.timer = setInterval(function(){
            if(self.datas.length){
                self.execute();
            }else{
                self.stop();
            }
        }, this.interval)
    },
    stop:function(){
        this.isStarted = false;
        clearInterval(this.timer);
    },
    execute:function(){
       this.callback(this.datas.shift());
    }
}
var queue = new MessageQueue(function (msg) {
    $(msg).prependTo($("#keylog .log_content").eq(0));
})
function goto_deploy(tenantName, service_alias) {
    window.location.href = "/apps/" + tenantName + "/" + service_alias
        + "/detail/"
}

function service_my_oneKeyDeploy(categroy, serviceAlias, tenantName, isreload) {
    event_id = createEvents(tenantName, serviceAlias, "deploy")
    if (event_id == "") {
        return false
    }
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
                //$("#onekey_deploy").removeAttr("disabled")
            }
            if (isreload == 'yes') {
                forurl = "/apps/" + tenantName + "/" + serviceAlias
                    + "/detail/"
                window.open(forurl, target = "_parent")
            }
            //$("#onekey_deploy").removeAttr("disabled")
        },
        error: function () {
            //$("#onekey_deploy").removeAttr("disabled")
            swal("系统异常");
        }
    });
}
function service_oneKeyDeploy(categroy, serviceAlias, tenantName, isreload) {
    $("#onekey_deploy").attr('disabled', "true")
    event_id = createEvents(tenantName, serviceAlias, "deploy");
    if (event_id == "") {
        return false
    }
    connectSocket(event_id, "deploy");

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
                swal.close();
            } else if (dataObj["status"] == "owed") {
                swal("余额不足请及时充值");
                ws.close();
                history.go(0);
            } else if (dataObj["status"] == "expired") {
                swal("试用已到期");
                ws.close();
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
                //$("#onekey_deploy").removeAttr("disabled")
            }
            if (isreload == 'yes') {
                forurl = "/apps/" + tenantName + "/" + serviceAlias
                    + "/detail/"
                window.open(forurl, target = "_parent")
            }
            //$("#onekey_deploy").removeAttr("disabled")
        },
        error: function () {
            //$("#onekey_deploy").removeAttr("disabled")
            swal("系统异常");
        }
    });
}

//获取evevts
function createEvents(name, service, action) {
    var currentEventID = ""
    var ok = false;
    if (!action) {
        return;
    }
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
                ok = true

                var arr = event["event_start_time"].split("T");
                var date = arr[0];
                var time = arr[1].split('.')[0];
                var type_json = {
                    "deploy": "部署",
                    "restart": "启动",
                    "delete": "删除",
                    "stop": "关闭",
                    "HorizontalUpgrade": "水平升级",
                    "VerticalUpgrade": "垂直升级",
                    "callback": "回滚",
                    "create": "创建",
                    "share-ys": "分享到云市",
                    "share-yb": "分享到云帮",
                    "own_money": "应用欠费关闭",
                    "expired": "应用过期关闭" ,
                    "reboot"  :"应用重启" ,
                    "git-change":"仓库地址修改",
                    "imageUpgrade":"应用更新"
                }

                var str_log = '<li><time class="tl-time"><h4>' + time + '</h4></time><i class="fa bg-grey tl-icon"></i><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>' + type_json[event["event_type"]] + '中@' + event["user_name"] + '</span><div class="user"><p>';
                str_log += '</p><p class="ajax_log" data-log="' + event["event_id"] + '" style="display: none;">查看详情</p><p class="hide_log" style="display: block;">收起</p></div></div><div class="panel-body"><div class="log"><p class="log_type" style="display: none;"><label class="active" data-log="info">Info日志</label><label data-log="debug">Debug日志</label><label data-log="error">Error日志</label></p><div class="log_content log_height2 log_' + event["event_id"] + '"></div></div></div></div></div></li>'

                if (event["event_type"] == "deploy" && event["old_deploy_version"]) {
                    var version = '当前版本(' + event["old_deploy_version"] + ')';
                    if (event["old_code_version"]) {
                        version = event["old_code_version"];
                    }
                    str_log += '<li><i class="fa tl-icon bg-version"></i><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>' + version + '</span>';
                    str_log += '<div class="user"><button class="btn callback_version" data-version="' + event["old_deploy_version"] + '">回滚到此版本</button></div></div></div></div></li>'

                }
                $(".today_log").show();
                $(str_log).prependTo($("#keylog ul"));
                ajax_getLog();
                //callback_version();
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
function ajax_getLog() {
    $(".ajax_log").off('click');
    $(".ajax_log").click(function () {
        var event_id = $(this).attr("data-log");
        $(this).parents('li').find('.log_type label').removeClass('active');
        $(this).parents('li').find('.log_type label').eq(0).addClass('active');
        if ($(this).parents('li').find('.log_type').css("display") != "none") {
            $(".log_" + event_id).html('');
            do_logshow(event_id, 'info');
        }
        $(this).hide();
        $(this).parent().find('.hide_log').show();
        //$(".log_" + event_id + "").addClass('log_height');
        $(this).parents('li').find('.log').addClass('log_height');
        $(this).parents('li').find('.log_content').addClass('log_height2');
    });
    $(".hide_log").off('click');
    $(".hide_log").click(function () {
        var onOff = $(this).parents('.panel').find('.log').hasClass('log_height');
        if (onOff) {
            $(this).parents('li').find('.log').removeClass('log_height');
            $(this).parents('li').find('.ajax_log').show();
            $(this).hide();
            $(this).parents('.panel').find('.panel-heading').css({ "padding-bottom": "0px" });
            $(this).parents('.panel').find('.log').css({ "height": "0px" });
        }
        else {
            $(this).parents('li').find('.log').addClass('log_height');
            $(this).parents('li').find('.ajax_log').hide();
            $(this).show();
        }
    });
    $(".log_type label").off('click');
    $(".log_type label").click(function () {
        $(this).addClass('active').siblings('label').removeClass('active');
        var event_id = $(this).parents('li').find('.ajax_log').attr("data-log");
        do_logshow(event_id, $(this).attr("data-log"));
    });
}




var ws = null
function connectSocket(event_id, action) {
    var url = $("#event_websocket_uri").val();
    ws = new WebSocket(url);
    var type_json = {
        "deploy": "部署",
        "restart": "启动",
        "delete": "删除",
        "stop": "关闭",
        "HorizontalUpgrade": "水平升级",
        "VerticalUpgrade": "垂直升级",
        "callback": "回滚",
        "create": "创建",
        "own_money": "应用欠费关闭",
        "expired": "应用过期关闭",
        "share-ys": "分享到云市",
        "share-yb": "分享到云帮",
        "reboot"  :"应用重启" ,
        "git-change":"仓库地址修改",
        "imageUpgrade":"应用更新"
    }
    var num = $(".load_more").attr("data-num");
    $(".load_more").attr("data-num", parseInt(num) + 1);
    ws.onopen = function (evt) {
        ws.send("event_id=" + event_id);
        //$("#service_status_operate").attr("disabled","disabled");
        $("#onekey_deploy").attr('disabled', 'disabled');
        window.onSocketOpen && window.onSocketOpen();
    }
    ws.onmessage = function (evt) {
        //var m = jQuery.parseJSON(evt.data)
        $("#keylog .panel-heading").eq(0).css({ "padding-bottom": "5px" });
        $("#keylog .log").eq(0).css({ "height": "20px" });
        $("#keylog .ajax_log").eq(0).hide();
        $("#keylog .hide_log").eq(0).show();
        $("#keylog .log_type").eq(0).hide();
        if (evt.data == "ok") {
            return;
        }
        var m = JSON.parse(evt.data)
        var arr = m.time.split('.')[0];
        var time1 = arr.split('T')[0];
        var time2 = arr.split('T')[1].split('Z')[0];
        var time3 = time2.split('+')[0];
        tmpLog = "<p class='clearfix'><span class='log_time'>" + time3 + "</span><span class='log_msg'> " + m.message + "</span></p>";
        //$("#keylog").children("div:first-child").before(tmpLog)
        //$(tmpLog).prependTo($("#keylog .log_content").eq(0));
        queue.add(tmpLog);
        if (m.step == "callback" || m.step == "last") {
            ws.close();
            $("#keylog li").eq(0).find('.ajax_log').show();
            $("#keylog li").eq(0).find('.log_type').show();
            $("#keylog li").eq(0).find('.hide_log').hide();
            if (m.status == "success") {
                var str = type_json[action] + "成功";
                $("#keylog li").eq(0).find(".fa").removeClass("bg-grey").addClass("bg-success");
            }
            else {
                $("#keylog li").eq(0).find(".fa").removeClass("bg-grey").addClass("bg-danger");
                var str = type_json[action] + "失败(" + m.message + ")";
            }
            if (action == "restart") {
                $("#service_status_operate").css({ "background-color": "#f63a47" });
            }
            else if (action == "stop") {
                $("#service_status_operate").css({ "background-color": "#28cb75" });
            }
            //$("#keylog li").eq(0).find('.panel-heading').css({ "padding-bottom": "0px" });
            $("#keylog li").eq(0).find('.log').css({ "height": "0px" });
            $("#keylog .panel").eq(0).find(".panel-heading span").html(str);
            //$("#service_status_operate").removeAttr("disabled");
            $("#onekey_deploy").removeAttr('disabled');
        }
    }
    ws.onclose = function (evt) {
        $("#keylog .panel-heading").eq(0).css({ "padding-bottom": "0px" });
        $("#keylog .panel-heading .hide_log").eq(0).html('收起');
        console.log('连接关闭')
        window.onSocketClose && window.onSocketClose();
        ajax_getLog();
    }
    ws.onerror = function (evt) {
        console.log("WebSocket错误");
        window.onSocketError && window.onSocketError();
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
    $("#service_status_operate").attr('disabled', "true")
    var taction = $("#operate_" + service_id).attr("data" + service_id)
    if (taction != "stop" && taction != "restart") {
        swal("系统异常");
        window.location.href = window.location.href;
    }
    event_id = createEvents(tenantName, service_alias, taction)
    if (event_id == "") {
        swal("创建操作错误");
        return false;
    }
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
                swal("操作成功");
            } else if (dataObj["status"] == "often") {
                swal("操作正在进行中，请稍后");

            } else if (dataObj["status"] == "owed") {
                swal("余额不足请及时充值");
                ws.close();
                history.go(0);
            } else if (dataObj["status"] == "expired") {
                swal("试用已到期");
                ws.close();
                history.go(0);
            } else if (dataObj["status"] == "over_memory") {
                swal("资源已达上限，不能升级");
                ws.close();
                history.go(0);
            } else if (dataObj["status"] == "over_money") {
                swal("余额不足，不能升级");
                ws.close();
                history.go(0);
            } else {
                swal("操作失败");
                ws.close();
                history.go(0);
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
    $("#service_status_operate").attr('disabled', "true");
    event_id = createEvents(tenantName, service_alias, taction)
    if (event_id == "") {
        swal("创建操作错误");
        return false;
    }
    connectSocket(event_id, taction);


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
                swal.close();
            } else if (dataObj["status"] == "often") {
                swal("操作正在进行中，请稍后");
                ws.close();
                history.go(0);
            } else if (dataObj["status"] == "owed") {
                swal("余额不足请及时充值");
                ws.close();
                history.go(0);
            } else if (dataObj["status"] == "expired") {
                swal("试用已到期");
                ws.close();
                history.go(0);
            } else if (dataObj["status"] == "over_memory") {
                swal("免费资源已达上限，不能操作");
                ws.close();
                history.go(0);
            } else if (dataObj["status"] == "over_money") {
                swal("余额不足，不能操作");
                ws.close();
                history.go(0);
            } else {
                swal("操作失败");
                ws.close();
                history.go(0);
            }
            $("#service_status_operate").removeAttr("disabled");
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
        setTimeout(function () {
            var status = $("#service_status_operate").find("font").html();
            if (status == "关闭") {
                $("#service_status_operate").css({ "background-color": "#f63a47" });
            }
            else {
                $("#service_status_operate").css({ "background-color": "#28cb75" });
            }
        }, 2000);
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
                swal.close();
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
function log_page() {
    $(".load_more").click(function () {
        var that = $(this);
        var num = $(this).attr("data-num");
        var tenantName = $("#tenantName").val();
        var serviceAlias = $("#serviceAlias").val();
        $.ajax({
            type: "GET",
            url: "/ajax/" + tenantName + "/" + serviceAlias + "/events?start_index=" + num,
            data: "",
            cache: false,
            beforeSend: function (xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function (msg) {
                var dataObj = msg;
                var showlog = ""
                var logList = dataObj["log"];
                var next_onOff = dataObj["has_next"];
                that.attr("data-num", parseInt(num) + logList.length);
                if (next_onOff) {
                    $(".load_more").show();
                }
                else {
                    $(".load_more").hide();
                }
                if (typeof (logList) != "undefined") {
                    var type_json = {
                        "deploy": "部署",
                        "restart": "启动",
                        "stop": "关闭",
                        "delete": "删除",
                        "HorizontalUpgrade": "水平升级",
                        "VerticalUpgrade": "垂直升级",
                        "callback": "回滚",
                        "create": "创建",
                        "own_money": "应用欠费关闭",
                        "expired": "应用过期关闭",
                        "share-ys": "分享到云市",
                        "share-yb": "分享到云帮",
                        "reboot"  :"应用重启" ,
                        "git-change":"仓库地址修改",
                        "imageUpgrade":"应用更新"

                    }
                    var status_json = {
                        "success": "成功",
                        "failure": "失败",
                        "timeout": "超时"
                    }
                    var final_status_json = {
                        "complate": "完成",
                        "timeout": "超时"
                    }
                    var bg_color = {
                        "success": "bg-success",
                        "failure": "bg-danger",
                        "timeout": "bg-danger"
                    }
                    for (var i = 0; i < logList.length; i++) {
                        var log = logList[i]
                        if (i == 0 && (log["final_status"] == "")) {
                            connectSocket(log["event_id"], log["type"]);
                        }
                        var arr = log["start_time"].split("T");
                        var date = arr[0];
                        var time = arr[1];
                        var status;
                        var color;
                        if (log["final_status"] == "complete") {
                            status = status_json[log["status"]];
                            color = bg_color[log["status"]];
                        }
                        else if (log["final_status"] == "timeout") {
                            status = final_status_json[log["final_status"]];
                            color = 'bg-danger';
                        }
                        else {
                            status = "进行中";
                            color = 'bg-grey';
                        }
                        if (isToday(date)) {
                            var str_log = '<li><time class="tl-time"><h4>' + time + '</h4></time>';
                            $(".today_log").show();
                        }
                        else {
                            var str_log = '<li><time class="tl-time"><h4>' + time + '</h4><p>' + date + '</p></time>';
                        }
                        if (log["status"] == "failure") {
                            str_log += '<i class="fa ' + color + ' tl-icon"></i><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>' + type_json[log["type"]] + status + '(' + log["message"] + ')' + ' @' + log["user_name"] + '</span><div class="user"><p></p><p class="ajax_log" data-log="' + log["event_id"];
                        }
                        else {
                            str_log += '<i class="fa ' + color + ' tl-icon"></i><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>' + type_json[log["type"]] + status + ' @' + log["user_name"] + '</span><div class="user"><p></p><p class="ajax_log" data-log="' + log["event_id"];
                        }
                        str_log += '">查看详情</p><p class="hide_log">收起</p></div></div><div class="panel-body"><div class="log"><p class="log_type"><label class="active" data-log="info">Info日志</label><label data-log="debug">Debug日志</label><label data-log="error">Error日志</label></p><div class="log_content log_' + log["event_id"] + '"></div></div></div></div></div></li>'
                        if (log["type"] == "deploy" && log["old_deploy_version"] != "") {
                            str_log += '<li><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>当前版本(' + log["old_deploy_version"] + ')</span>';
                            str_log += '<div class="user"><button class="btn callback_version" data-version="' + log["old_deploy_version"] + '">回滚到此版本</button></div></div></div></div></li>'
                        }

                        $(str_log).appendTo($("#keylog ul"));
                        ajax_getLog();
                        //callback_version();
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
                        swal.close();
                        window.location.href = "/apps/" + tenantName
                    } else if (dataObj["status"] == "often") {
                        swal("上次操作正在进行中，稍后再试")
                    } else if (dataObj["status"] == "published") {
                        swal("关联了已发布服务, 不可删除")
                    } else if (dataObj["status"] == "evn_dependency") {
                        var dep_service = dataObj["dep_service"]
                        if (typeof (dep_service) == "undefined") {
                            swal("当前服务被环境依赖不能删除");
                        } else {
                            swal("当前服务被(" + dep_service + ")环境依赖不能删除");
                        }
                    } else if (dataObj["status"] == "mnt_dependency") {
                        var dep_service = dataObj["dep_service"]
                        if (typeof (dep_service) == "undefined") {
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
                swal.close();
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
                swal("操作成功");
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
            event_id = createEvents(tenantName, service_alias, "imageUpgrade")
            if (event_id == "") {
                swal("创建更新操作错误，请重试");
                return false
            }
            $.ajax({
                type: "POST",
                url: "/ajax/" + tenantName + "/" + service_alias + "/upgrade",
                data: "service_id=" + service_id + "&action=imageUpgrade&event_id=" + event_id,
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
    event_id = createEvents(tenantName, service_alias, "reboot")
    if (event_id == "") {
        swal("创建更新操作错误，请重试");
        return false
    }
    $.ajax({
        type: "POST",
        url: "/ajax/" + tenantName + "/" + service_alias + "/manage",
        data: "service_id=" + service_id + "&action=reboot&event_id="+event_id,
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

///////
function high_relation(curServiceName, depServiceName, tenantName) {
    $.ajax({
        type: "GET",
        url: "/ajax/" + tenantName + "/" + curServiceName + "/l7info",
        data: { "dep_service_id": depServiceName },
        cache: false,
        async: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (data) {
            console.log(data);
            var servenlayer = data;
            var domainUrl = servenlayer["domain"];
            console.log(domainUrl);
            //  展示 弹出层 start
            var oStrH = '<div class="layerbg" id="servenLayer"><div class="servenlayer">'

            //var headArray = servenlayer["header"];
            //var statistic = servenlayer["statistic"];
            var cricuit = servenlayer["cricuit"];
            oStrH += '<a href="javascript:;" class="closebtn fn-close"><i class="fa fa-times"></i></a><p class="layer-tit">设置</p>';
            if (domainUrl != "close") {
                if (domainUrl == "off") {
                    oStrH += '<p class="onoffbox clearfix"><span>转发</span><label><input type="checkbox" name="domainurl"  id="domainurl"  class="checkhide" /><span class="checkshow" for="domainurl"></span></label></p><div class="headarrbox clearfix" id="headarrbox" style="display:none;"><p class="domainbox clearfix"><span>Domain</span><input type="text" value="" id="dourl" /></p>';
                } else {
                    oStrH += '<p class="onoffbox clearfix"><span>转发</span><label><input type="checkbox" name="domainurl"  id="domainurl"  class="checkhide" checked="true"/><span class="checkshow" for="domainurl"></span></label></p><div class="headarrbox clearfix" id="headarrbox"><p class="domainbox clearfix"><span>Domain</span><input type="text" value="' + domainUrl + '" id="dourl"/></p>';
                }
            }
            oStrH += '</div>';

            //if(domainUrl == "off"){
            //	oStrH +='<p class="onoffbox clearfix"><span>转发</span><input type="checkbox" name="domainurl"  id="domainurl"  class="checkhide"/><label class="checkshow" for="domainurl"></label></p><div class="headarrbox clearfix" id="headarrbox" style="display:none;"><p class="domainbox clearfix"><span>Domain</span><input type="text" value="" id="dourl" /></p><p class="headertit clearfix"><span>Header</span><cite>Key</cite><cite>Value</cite><a href="javascript:;" id="addheader">+</a></p><div id="headpbox">';
            //}else{
            //	oStrH +='<p class="onoffbox clearfix"><span>转发</span><input type="checkbox" name="domainurl"  id="domainurl"  class="checkhide" checked="true"/><label class="checkshow" for="domainurl"></label></p><div class="headarrbox clearfix" id="headarrbox"><p class="domainbox clearfix"><span>Domain</span><input type="text" value="'+ domainUrl +'" id="dourl"/></p><p class="headertit clearfix"><span>Header</span><cite>Key</cite><cite>Value</cite><a href="javascript:;" id="addheader">+</a></p><div id="headpbox">';
            //}

			/*
			for(var i=0;i<headArray.length;i++){
				oStrH += '<p class="clearfix headerp"><span>&nbsp;</span><input type="text" value="' + headArray[i]["key"] + '" /><input type="text" value="' + headArray[i]["value"] + '" /></p>'
			}
			oStrH +='</div></div>';
			if(statistic == "off"){
				oStrH += '<p class="onoffbox clearfix"><span>统计</span><input type="checkbox" name="statisticsbox"  id="statisticsbox"  class="checkhide"/><label class="checkshow" for="statisticsbox"></label></p>';
			}else{
				oStrH += '<p class="onoffbox clearfix"><span>统计</span><input type="checkbox" name="statisticsbox"  id="statisticsbox"  class="checkhide" checked="true"/><label class="checkshow" for="statisticsbox"></label></p>';
			}
			*/

            //oStrH += '<p class="onoffbox clearfix"><span>熔断</span><input type="checkbox" name="cricuitonoff"  id="cricuitonoff"  class="checkhide" checked="true"/><label class="checkshow" for="cricuitonoff"></label></p>';
            oStrH += '<p class="fusingbox clearfix" id="fusingbox" style="padding:10px 0"><span>熔断</span><select id="fusing"><option value="0">0</option><option value="128">128</option><option value="256">256</option><option value="512">512</option><option value="1024">1024</option></select></p>';
            oStrH += '<p style="color: #838383; line-height: 22px; padding:10px 0; font-size: 14px;">说明：熔断器数值表示同一时刻最大所允许向下游访问的最大连接数，设置为0时则完全熔断。</p>'
            oStrH += '<div class="clearfix  servenbtn"><button  type="button" class="greenbtn" id="hrelsure" data-tenantName="' + tenantName + '" data-servicealias = "' + curServiceName + '" data-valuealias ="' + depServiceName + '">确定</button><button  type="button" id="hreldel" class="redbtn">取消</button></div>';
            oStrH += '</div></div>'
            $(oStrH).appendTo("body");
            if (domainUrl != "off" && domainUrl != "close") {
                if ($("#dourl").val() == "") {
                    $("#hrelsure").addClass("graybtn").removeClass("greenbtn").attr("disabled", "true");
                } else {
                    $("#hrelsure").addClass("greenbtn").removeClass("graybtn").removeAttr("disabled");
                }
            }
            $("#fusing option").each(function () {
                var othis = $(this);
                var thisval = $(this).attr("value");
                if (thisval == cricuit) {
                    $(othis).attr("selected", true);
                }
            });
            //  展示 弹出层 end
            //取消弹出层 start 
            $("#hreldel").click(function () {
                $("#servenLayer").remove();
            });
            $(".fn-close").click(function () {
                $("#servenLayer").remove();
            });
            //取消弹出层 end
            //熔断 start
            $("#cricuitonoff").change(function () {
                var crionoff = $("#cricuitonoff").prop("checked");
                if (crionoff == true) {
                    $("#fusingbox").show();
                } else {
                    $("#fusingbox").hide();
                }
            });
            //熔断 end
            //网址输入框改变 start
            $("#domainurl").change(function () {
                var damainonoff = $("#domainurl").prop("checked");
                if (damainonoff == true) {
                    $("#headarrbox").show();
                    if ($("#dourl").val() == "") {
                        $("#hrelsure").addClass("graybtn").removeClass("greenbtn").attr("disabled", "true");
                    } else {
                        $("#hrelsure").addClass("greenbtn").removeClass("graybtn").removeAttr("disabled");
                    }
                } else {
                    $("#headarrbox").hide();
                    $("#hrelsure").addClass("greenbtn").removeClass("graybtn").removeAttr("disabled");
                }
            });
		    /*
			//网址输入框改变 end
			//添加 key value  输入框  start
			var keyvaluenum = $("#headpbox p").length;
			if(keyvaluenum >= 4){
				$("#addheader").hide();
			}
			$("#addheader").click(function(){
				var cnum = $("#headpbox p").length;
				if(cnum >= 4){
					$("#addheader").hide();
				}
    			var oStrhp = '<p class="clearfix headerp"><span>&nbsp;</span><input type="text" value="" /><input type="text" value="" /></p>';
    			$(oStrhp).appendTo($("#headpbox"));
    		});
			//添加 key value  输入框  end
			*/

            //网址光标移出 start
            $("#dourl").blur(function () {
                var ourl = $("#dourl").val();
                //var hpnum = 0;
                //$("#headpbox p").each(function(){
                //	var keyVal = $(this).find("input").eq(0).val();
                //	var valVal = $(this).find("input").eq(1).val();
                //	if(keyVal != "" && valVal !=""){
                //		hpnum = 1;
                //	}
                //});
                //if(ourl != "" || hpnum == 1){
                //	$("#hrelsure").addClass("greenbtn").removeClass("graybtn").removeAttr("disabled");
                //}else{
                //	$("#hrelsure").addClass("graybtn").removeClass("greenbtn").attr("disabled","true");	
                //}
                if (ourl != "") {
                    $("#hrelsure").addClass("greenbtn").removeClass("graybtn").removeAttr("disabled");
                } else {
                    $("#hrelsure").addClass("graybtn").removeClass("greenbtn").attr("disabled", "true");
                }
            });
            //网址光标移出 end
            /*
			//keyvalue  光标移出  start
		    $("#headpbox input").blur(function(){
		    	var ourl = $("#dourl").val();
		    	var hpnum = 0;
		    	console.log(hpnum);
		    	$("#headpbox p").each(function(){
		    		var keyVal = $(this).find("input").eq(0).val();
		    		var valVal = $(this).find("input").eq(1).val();
		    		if(keyVal != "" && valVal !=""){
		    			hpnum = 1;
		    		}
		    	});
		    	if(ourl != "" || hpnum == 1){
		    		$("#hrelsure").addClass("greenbtn").removeClass("graybtn").removeAttr("disabled");
		    	}else{
		    		$("#hrelsure").addClass("graybtn").removeClass("greenbtn").attr("disabled","true");	
		    	}
		    });
			//keyvalue  光标移出  end
			*/
            //确定提交参数 start
            $("#hrelsure").click(function () {
                var obox = {};
                //var headerbox=[];
                var oneonoff = $("#domainurl").prop("checked");
                var domainval = $("#dourl").val();
                var cricuitval = $("#fusing option:selected").attr("value");
                //var statisticval = $("input#statisticsbox").prop("checked");
                if (oneonoff == true) {
                    obox["domain"] = domainval;
                }
                obox["cricuit"] = cricuitval;
                //obox["statistic"] = (statisticval==true) ? "on" : "off";

                //var twoonoff = $("input#statisticsbox").prop("checked");
                //var threeonoff = $("#cricuitonoff").prop("checked");
                /*
                if(threeonoff == false){
                    typeval = "del";
                }else{
                    typeval = "add";
                }
                */
                /*
                $("#headpbox p").each(function(){
                    var kv={};
            var keyVal = $(this).find("input").eq(0).val();
            var valVal = $(this).find("input").eq(1).val();
            if(keyVal != "" && valVal !=""){
                kv["key"] = keyVal;
                kv["value"] = valVal;
            }
            headerbox.push(kv);
        });
        obox["header"]= headerbox;
        console.log(obox);
        */
                ///ajax
                var oboxstr = JSON.stringify(obox)
                $.ajax({
                    type: "POST",
                    url: "/ajax/" + tenantName + "/" + curServiceName + "/l7info",
                    data: {
                        "dep_service_id": depServiceName,
                        "l7_json": oboxstr
                    },
                    cache: false,
                    async: false,
                    beforeSend: function (xhr, settings) {
                        var csrftoken = $.cookie('csrftoken');
                        xhr.setRequestHeader("X-CSRFToken", csrftoken);
                    },
                    success: function (data) {
                        $("#servenLayer").remove();
                        if (data.status == "success") {
                            swal("设置成功！");
                        } else {
                            swal("设置失败！");
                        }
                    },
                    error: function () {
                        $("#servenLayer").remove();
                        swal("系统异常");
                    }
                });
                ///ajax
            });
            //确定提交参数 end
        },
        error: function () {
            swal("系统异常");
        }
    });
}
function isToday(str) {
    var d = new Date(str);
    var todaysDate = new Date();
    if (d.setHours(0, 0, 0, 0) == todaysDate.setHours(0, 0, 0, 0)) {
        return true;
    } else {
        return false;
    }
}

