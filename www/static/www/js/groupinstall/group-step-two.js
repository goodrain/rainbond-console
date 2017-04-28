$(function(){
    $(".tablink a").eq(0).addClass("sed");
    $("section.app-box").eq(0).show();
    $(".tablink a").click(function () {
        $(".tablink a").removeClass("sed");
        $(".tablink a").eq($(this).index()).addClass("sed");
        $("section.app-box").hide();
        $("section.app-box").eq($(this).index()).show();
    });
    //点击下一步操作
    $("#group_install_two").on("click", function () {
        var shared_group_id = $("#shared_group_id").val();
        var service_group_id = $("#service_group_id").val();

        var app = $(".app-box");
        var services = [];
        app.each(function(){
            var key = $(this).attr("data-key");
            var version = $(this).attr("data-version")
            var name = $(this).find(".service_name").val();
            var data_json = {
                "service_key":key,
                "service_version":version,
                "service_name":name
            }
            services.push(data_json);
        });
        var data = {
            "service_group_id":service_group_id,
            "services":services
        }
        data = JSON.stringify(data);
        //$.ajax({
        //    type : "post",
        //    url : "/apps/" + tenantName + "/group-deploy/" + share_group_id+"/step2/",
        //    data : data,
        //    cache : false,
        //    beforeSend : function(xhr, settings) {
        //        var csrftoken = $.cookie('csrftoken');
        //        xhr.setRequestHeader("X-CSRFToken", csrftoken);
        //    },
        //    success : function(msg) {
        //        var dataObj = msg;
        //        if (dataObj["success"]) {
        //            window.location.href=dataObj["next_url"]
        //        } else {
        //            swal("创建失败");
        //            $("#group_install_one").removeAttr('disabled');
        //        }
        //    },
        //    error : function() {
        //        swal("系统异常,请重试");
        //        $("#group_install_one").removeAttr('disabled');
        //    }
        //})
        
    });
    
});