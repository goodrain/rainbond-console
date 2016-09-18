var BranchLocalData = {};
//创建应用
$(function(){
    $('#create_app_name').blur(function(){
        var appName = $(this).val(),
            checkReg = /^[a-z][a-z0-9-]*[a-z0-9]$/,
            result = true;
            
        if(!checkReg.test(appName)){
        	$("#create_app_name").focus()
        	scrollOffset($("#create_app_name").offset()); 
            $('#create_appname_notice').slideDown();
            return;
        }else{
            $('#create_appname_notice').slideUp();
        }
    });
    //第一步
    $('#first_step').click(function(){
        var appName = $('#create_app_name').val(),
            checkReg = /^[a-z][a-z0-9-]*[a-z0-9]$/,
            result = true;
            
        if(!checkReg.test(appName)){
        	$("#create_app_name").focus()
        	scrollOffset($("#create_app_name").offset()); 
            $('#create_appname_notice').slideDown();
            return;
        }else{
            $('#create_appname_notice').slideUp();
        }
        var service_code_clone_url = $('#service_code_clone_url').val()
        if(service_code_clone_url==""){
            $("#service_code_clone_url").focus()
            scrollOffset($("#service_code_clone_url").offset()); 
            $('#create_git_notice').slideDown();
            return;
        }
        var service_code_version = $('#service_code_version').val()
        if(service_code_version==""){
            $("#service_code_version").focus()
            scrollOffset($("#service_code_version").offset()); 
            $('#create_version_notice').slideDown();
            return;
        }
        
        $("#first_step").attr('disabled', true);
    	var _data = $("form").serialize();
        var tenantName= $('#currentTeantName').val();
    	$.ajax({
    		type : "post",
    		url : "/apps/" + tenantName + "/app-create/",
    		data : _data,
    		cache : false,
    		beforeSend : function(xhr, settings) {
    			var csrftoken = $.cookie('csrftoken');
    			xhr.setRequestHeader("X-CSRFToken", csrftoken);
    		},
    		success : function(msg) {
    			var dataObj = msg;
				$("#first_step").attr('disabled', false);
    			if (dataObj["status"] == "exist") {
    				swal("服务名已存在");
    			} else if (dataObj["status"] == "owed"){
    				swal("余额不足请及时充值")
    			} else if (dataObj["status"] == "expired"){
					swal("已超出试用期限")
				} else if (dataObj["status"] == "over_memory") {
    				swal("免费资源已达上限，不能创建");
    			} else if (dataObj["status"] == "over_money") {
    				swal("余额不足，不能创建");
    			} else if (dataObj["status"] == "empty") {
    				swal("应用名称不能为空");
    			}else if (dataObj["status"] == "code_from") {
    				swal("应用资源库未选择");
    			}else if (dataObj["status"] == "code_repos") {
    				swal("代码仓库异常");
    			}else if (dataObj["status"] == "success") {
    				service_alias = dataObj["service_alias"]
    				window.location.href = "/apps/" + tenantName + "/" + service_alias + "/app-dependency/";
    			} else {
    				swal("创建失败");
                }
    		},
    		error : function() {
    			swal("系统异常,请重试");
    			$("#first_step").attr('disabled', false);
    		}
    	})
    });
});

function scrollOffset(scroll_offset) { 
    $("body,html").animate({scrollTop: scroll_offset.top - 70}, 0); 
}
