$(function () {
    $("#group_install_one").on("click", function () {
        var group_name = $("#group_name").val();
        if ($.trim(group_name) == "") {
            swal("组名称不能为空");
            return false;
        }
        //禁用按钮
        $("#group_install_one").attr('disabled');
        var tenantName = $("#tenantNameValue").val();
        var share_group_id = $("#share_group_id").val();
        $.ajax({
            type : "post",
            url : "/apps/" + tenantName + "/group-deploy/" + share_group_id+"/step1/",
            data : "group_name="+group_name,
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {
                var dataObj = msg;
                if (dataObj["success"]) {
                    window.location.href=dataObj["next_url"]
                } else {
                    swal("创建失败");
                    $("#group_install_one").removeAttr('disabled');
                }
            },
            error : function() {
                swal("系统异常,请重试");
                $("#group_install_one").removeAttr('disabled');
            }
        })
    });
});