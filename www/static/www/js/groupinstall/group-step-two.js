$(function(){
    //点击下一步操作
    $("#group_install_two").on("click", function () {
        var shared_group_id = $("#shared_group_id").val();
        var service_group_id = $("#service_group_id").val();

        var data = {
            "service_group_id":service_group_id
        }
        $.ajax({
            type : "post",
            url : "/apps/" + tenantName + "/group-deploy/" + share_group_id+"/step2/",
            data : data,
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