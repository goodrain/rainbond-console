$(function () {
    $("#nextstep").click(function () {
        var params = getParams();
        if (params.create_name) {
            console.log(params.create_name);
            $("#create_name_notice").css({"display": "none"});
        }
        else {
            $("#create_name_notice").css({"display": "block"});
            return;
        }

        if (params.version_no){
            console.log(params.version_no);
            $("#version_no_notice").css({"display": "none"});
        }else{
            $("#version_no_notice").css({"display": "block"});
            return;
        }

        $.ajax({
            type: "POST",
            url: "/apps/" + params.tenant_name + "/" + params.group_id + "/" + params.share_id + "/first/",
            data: {
                "alias": params.create_name,
                "publish_type":params.publish_type,
                "group_version":params.version_no,
                "desc":params.desc,
                "is_market":params.is_market,
                "installable":params.installable
                
            },
            cache: false,
            beforeSend: function (xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function (msg) {
                var json_data = eval(msg);
                if (json_data.code == 200) {
                    location.href = "/apps/" + params.tenant_name + "/" + params.group_id + "/" + params.share_id + "/second/";
                } else {
                    swal(json_data.msg);
                }
            },
            error: function () {
                swal("系统异常");
            }
        });
    });

    /**
     * 发布到云市显示是否允许安装选项
     */
    $("input[name=publish_dest]").change(function () {
        var ys_dest = $("#ys_dest").prop("checked");
        if (ys_dest){
            $("#ys_operation").show();
        }else{
            $("#ys_operation").hide();
        }
    });

});

/**
 * 获取页面数据
 * @returns {{tenant_name: (*|jQuery), group_id: (*|jQuery), share_id: (*|jQuery), create_name: (*|jQuery), version_no: (*|jQuery), publish_type: string, desc: (*|jQuery), is_market: boolean, installable: boolean}}
 */
function getParams() {
    var tenant_name = $("#tenant_name").val();
    var group_id = $("#group_id").val();
    var share_id = $("#share_id").val();
    var create_name = $("#create_name").val();
    var version_no = $("#version_no").val();
    var publish_type = "services_group";
    var is_clound_frame = $("#cloud_frame").prop("checked");
    if (is_clound_frame)
        publish_type = "cloud_frame";
    var desc = $("#desc").val();
    var is_market = true;
    var ys_dest = $("#ys_dest").prop("checked");
    if (!ys_dest)
        is_market = false;
    var installable = true;
    var not_allow_install = $("#not_allow_install").prop("checked");
    if (not_allow_install)
        installable = false;
    var params = {
        tenant_name: tenant_name, group_id: group_id, share_id: share_id, create_name: $.trim(create_name),
        version_no: $.trim(version_no), publish_type: publish_type, desc: desc, is_market: is_market, installable: installable
    }
    return params;
}
