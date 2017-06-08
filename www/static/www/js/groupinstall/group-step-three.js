$(function(){

    $(".tablink a").eq(0).addClass("sed");
    $("section.app-box").eq(0).show();
    $(".tablink a").click(function () {
        $(".tablink a").removeClass("sed");
        $(".tablink a").eq($(this).index()).addClass("sed");
        $("section.app-box").hide();
        $("section.app-box").eq($(this).index()).show();
    });

    $("#group_install_three").on("click", function () {
        var share_group_id = $("#shared_group_id").val();
        var service_group_id = $("#service_group_id").val();
        var tenantName = $("#tenantNameValue").val();
        var keyEnvMap = {};
        $(".app-box").each(function () {
            var service_key = $(this).attr("data-key");
            var env_tr = $(this).find("tbody.environment").children("tr");
            var envList = [];
            $(env_tr).each(function(){
                var attr_name = $(this).find("td[name='attr_name']").html();
                console.log("attr_name:"+attr_name);
                var attr_value = $(this).find("[name='attr_value']").val() || $(this).find("[name='attr_value']").html() ;
                console.log(attr_value);
                var envMap = {
                    "attr_name":attr_name,
                    "attr_value":attr_value
                };
                envList.push(envMap);
            });
            keyEnvMap[service_key] = envList;

        });

        console.log(keyEnvMap);
        var envs = JSON.stringify(keyEnvMap);
        var data = {
            group_id:service_group_id,
            envs:envs
        };

        $.ajax({
            type : "post",
            url : "/apps/" + tenantName + "/group-deploy/" + share_group_id+"/step3/",
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
                    swal("系统异常");
                    $("#group_install_three").removeAttr('disabled');
                }
            },
            error : function() {
                swal("系统异常,请重试");
                $("#group_install_three").removeAttr('disabled');
            }
        })

    });

});