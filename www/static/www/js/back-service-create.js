//服务创建
function service_create(tenantName, service_key) {
	window.location.href = "/apps/" + tenantName
			+ "/service-deploy/?service_key=" + service_key
}
//创建应用
$(function(){
    $('#create_service_name').blur(function(){
        var appName = $(this).val(),
            checkReg = /^[a-zA-Z][a-zA-Z0-9_-]*$/,
            result = true;
            
        if(!checkReg.test(appName)){
            $('#create_service_notice').slideDown();
            return;
        }else{
            $('#create_service_notice').slideUp();
        }
    });
    //第一步
    $('#back_service_finished').click(function(){
        var appName = $('#create_service_name').val(),
            checkReg = /^[a-zA-Z][a-zA-Z0-9_-]*$/,
            result = true;
            
        if(!checkReg.test(appName)){
            $('#create_service_notice').slideDown();
            return;
        }else{
            $('#create_service_notice').slideUp();
        }    
        var serviceKey="";
		var serviceId="";
		$("input[name='inlineCheckbox1']:checkbox").each(function() {
			if ($(this).is(":checked")) {
				var str = $(this).val().split("_");
				if (str.length == 2) {
					if (serviceKey != "") {
						serviceKey = serviceKey + ","
					}
					serviceKey = serviceKey + str[0]
				}
			}
		});
		$("#createService").val(serviceKey)	
		
		$("input[name='delineCheckbox1']:checkbox").each(function() {
			if ($(this).is(":checked")) {
				var str = $(this).val().split("_");
				if (str.length == 2) {
					if (serviceId != "") {
						serviceId = serviceId + ","
					}
					serviceId = serviceId + str[0]
				}
			}
		});
		$("#hasService").val(serviceId)
		
		var service_dependecy = $("#service_dependecy").val()
		var createService = $("#createService").val()
		var hasService = $('#hasService').val()
		if(service_dependecy !=""){			
			if(createService=="" && hasService==""){
				$('#create_dependency_service_notice').slideDown();
				return;
			}
		}
		var tenantName = $("#tenantName").val()
		$("#back_service_finished").attr('disabled', "true")
		var _data = $("form").serialize();
    	$.ajax({
    		type : "post",
    		url : "/apps/" + tenantName + "/service-deploy/",
    		data : _data,
    		cache : false,
    		beforeSend : function(xhr, settings) {
    			var csrftoken = $.cookie('csrftoken');
    			xhr.setRequestHeader("X-CSRFToken", csrftoken);
    		},
    		success : function(msg) {
    			var dataObj = msg;
    			if (dataObj["status"] == "notexist"){
    				alert("所选的服务类型不存在");
    				$("#back_service_finished").removeAttr('disabled')
    			} else if (dataObj["status"] == "exist") {
    				alert("服务名已存在");
    				$("#back_service_finished").removeAttr('disabled')
    			} else if (dataObj["status"] == "overtop") {
    				alert("免费资源已达上限，不能创建");
    				$("#back_service_finished").removeAttr('disabled')
    			} else if (dataObj["status"] == "empty") {
    				alert("服务名称不能为空");
    				$("#back_service_finished").removeAttr('disabled')
    			}else if (dataObj["status"] == "success") {
    				service_alias = dataObj["service_alias"]
    				window.location.href = "/apps/" + tenantName + "/" + service_alias + "/app-dependency/";
    			} else {
    				alert("创建失败");
    				$("#back_service_finished").removeAttr('disabled')
                }
    		},
    		error : function() {
    			alert("系统异常,请重试");
    			$("#back_service_finished").removeAttr('disabled')
    		}
    	})
    });
});