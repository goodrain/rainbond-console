$(function () {
    $('#language_btn').click(
        function () {
            var checkedValue = "";
            var val = '';
            $("[name='service_dependency']:checkbox").each(function () {
                if (this.checked)
                    checkedValue = checkedValue + "," + $(this).val()
            });
            var language = $('#language').val();
            if (language == "Node.js") {
                var service_server = $('#service_server').val();
                if (service_server == "") {
                    swal("启动命令不能为空")
                    return false;
                }
            }
            $("#language_btn").attr('disabled', "true")
            var tenantName = $('#tenantName').val();
            var service_name = $('#service_name').val();
            var _data = $("form").serialize();
            $.ajax({
                type: "post",
                url: "/apps/" + tenantName + "/" + service_name
                + "/app-language/",
                data: _data + "&service_dependency=" + checkedValue,
                cache: false,
                beforeSend: function (xhr, settings) {
                    var csrftoken = $.cookie('csrftoken');
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                },
                success: function (msg) {
                    var dataObj = msg
                    if (dataObj["status"] == "success") {
                        app_oneKeyDeploy(tenantName, service_name);
                    } else {
                        swal("创建失败")
                        $("#language_btn").removeAttr('disabled')
                    }
                },
                error: function () {
                    swal("系统异常,请重试");
                    $("#language_btn").removeAttr('disabled')
                }
            })
        })

    $('.fn-tips').tooltip();
});



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
                return
            } else if (data["status"] == "success") {
                event = data["event"]
                currentEventID = event["event_id"]
                var tmpLog = event["event_start_time"] + " @" + event["user_name"] + event["event_type"]
                tmpLog = "<label style='line-height: 21px;'>" + tmpLog + "</label><p id='compile_" + event["event_id"] + "' style='display: none;line-height: 21px;'></p>"
                tmpLog = "<div id='event_" + event["event_id"] + "'>" + tmpLog + "</div>"
                $("#keylog").children("div:first-child").before(tmpLog)
                ok = true
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


function app_oneKeyDeploy(tenantName, serviceAlias) {

    eventID = createEvents(tenantName, serviceAlias, "deploy")
    if (eventID == "") {
        swal("创建部署操作错误。");
        return false
    }
    _url = "/ajax/" + tenantName + '/' + serviceAlias + "/app-deploy/"
    $.ajax({
        type: "POST",
        url: _url,
        cache: false,
        data: "event_id=" + eventID,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            window.location.href = "/apps/" + tenantName + "/" + serviceAlias + "/detail/"
        },
        error: function () {
            swal("系统异常");
        }
    })
}