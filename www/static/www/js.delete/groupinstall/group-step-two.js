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
        var share_group_id = $("#shared_group_id").val();
        var service_group_id = $("#service_group_id").val();
        var tenantName = $("#tenantNameValue").val();
        var app = $(".app-box");
        var services = [];
        var flag = true;
        app.each(function(){
            var key = $(this).attr("data-key");
            var version = $(this).attr("data-version")
            var name = $(this).find(".service_name").val();
            if ($.trim(name) == ""){
                flag = false;
            }
            var data_json = {
                "service_key":key,
                "service_version":version,
                "service_name":name
            }
            services.push(data_json);
        });

        if (!flag){
            swal("您有尚未填写的参数");
            return false;
        }
        var services_str = JSON.stringify(services);
        var data = {
            "service_group_id":service_group_id,
            "services":services_str
        }
        $("#group_install_two").attr('disabled');
        console.log(data);
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
               if (dataObj["status"] == "notexist"){
                   swal("所选的服务类型不存在");
               } else if (dataObj["status"] == "owed"){
                   swal("余额不足请及时充值")
               } else if (dataObj["status"] == "expired"){
                   swal("试用已到期")
               } else if (dataObj["status"] == "over_memory") {
                   if (dataObj["tenant_type"] == "free"){
                       swal("资源已达上限,不能创建");
                   }else
                       swal("资源已达上限，不能创建");
               } else if (dataObj["status"] == "over_money") {
                   swal("余额不足，不能创建");
               } else if (dataObj["status"] == "empty") {
                   swal("服务名称不能为空");
               } else if (dataObj["success"]) {
                   // swal("创建成功");
                   window.location.href=dataObj["next_url"]
               } else {
                   swal("系统异常");
                   $("#group_install_two").removeAttr('disabled');
               }
           },
           error : function() {
               swal("系统异常,请重试");
               $("#group_install_two").removeAttr('disabled');
           }
        })
        
    });
    
});