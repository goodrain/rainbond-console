//服务创建
function service_create(tenantName, service_key, app_version) {
	window.location.href = "/apps/" + tenantName
			+ "/service-deploy/?service_key=" + service_key + "&app_version=" + app_version
}

function service_update(tenantName, service_key, app_version, update_version) {
    window.location.href = '/ajax/'+tenantName+'/remote/market?service_key='
            + service_key + '&app_version=' + app_version+'&update_version='+update_version+'&action=update';
}


//创建应用
$(function(){
    $('#create_service_name').blur(function(){
        var appName = $(this).val(),
            checkReg = /^[a-z][a-z0-9-]*[a-z0-9]$/,
            result = true;
            
        if(!checkReg.test(appName)){
            $('#create_service_notice').slideDown();
            return;
        }else{
            $('#create_service_notice').slideUp();
        }
    });
    //第一步
    $('#back_service_step1').click(function(){
        var appName = $('#create_service_name').val(),
            checkReg = /^[a-z][a-z0-9-]*[a-z0-9]$/,
            result = true;
            
        if(!checkReg.test(appName)){
            $('#create_service_notice').slideDown();
            return;
        }else{
            $('#create_service_notice').slideUp();
        }
		var tenantName = $("#tenantName").val()
		$("#back_service_step1").prop('disabled', true)
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
                $("#back_service_finished").prop('disabled', false);
    			if (dataObj["status"] == "notexist"){
    				swal("所选的服务类型不存在");
    			} else if (dataObj["status"] == "depend_service_notexit"){
    			    swal("依赖的服务类型不存在，请先下载到服务市场");
    			} else if (dataObj["status"] == "owed"){
    				swal("余额不足请及时充值")
    			} else if (dataObj["status"] == "expired"){
                    swal("已超出试用期限")
                } else if (dataObj["status"] == "exist") {
    				swal("服务名已存在");
    			} else if (dataObj["status"] == "over_memory") {
    				swal("资源已达上限，不能创建");
    			} else if (dataObj["status"] == "over_money") {
    				swal("余额不足，不能创建");
    			} else if (dataObj["status"] == "empty") {
    				swal("服务名称不能为空");    				
    			}else if (dataObj["status"] == "success") {
    				service_alias = dataObj["service_alias"]
    				window.location.href = "/apps/" + tenantName + "/" + service_alias + "/setup/extra/";
    			} else {
    				swal("创建失败");
                }
    		},
    		error : function() {
    			swal("系统异常,请重试");
    			$("#back_service_finished").prop('disabled', false)
    		}
    	})
    });

    $('#back_service_finished').click(function() {
        envs = []
        var flag = false
        $('tbody tr').each(function() {
            env = {};
            $(this).find('[name^=attr]').each(function(event) {
                i = $(this);
                name = $(this).attr('name');
                value = $(this).val() || i.html();
                if (value) {
                    env[name] = value;
                } else {
                    showMessage("有未填写的内容");
                    flag = true
                }
            });
            envs.push(env);
        });
        if (flag) {
            return false;
        }
        var csrftoken = $.cookie('csrftoken');
        data = {"envs": envs};
        $.ajax({
          url: window.location.pathname,
          method: "POST",
          data: $.stringify(data),
          beforeSend: function(xhr) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
          },
          success :function (event) {
            if (event.success) {
              window.location.href = event.next_url;
            } else {
              showMessage(event.info);
            }
          },
          contentType: 'application/json; charset=utf-8',

          statusCode: {
            403: function(event) {
              alert("你没有此权限");
            }
          },
        });
    });
});