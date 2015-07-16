$(function() {
	$('#language_btn').click(
		function() {
			var checkedValue="";
			var val = '';  
			$("[name='service_dependency']:checkbox").each(function(){  
				if(this.checked)
					checkedValue= checkedValue +","+$(this).val() 
			});
			var language = $('#language').val();
			if(language=="Node.js"){
				var service_server = $('#service_server').val();
				if(service_server==""){
					swal("启动命令不能为空")
					return false;
				}
			}
			$("#language_btn").attr('disabled', "true")
			var tenantName = $('#tenantName').val();
			var service_name = $('#service_name').val();
			var _data = $("form").serialize();
			$.ajax({
				type : "post",
				url : "/apps/" + tenantName + "/" + service_name
						+ "/app-language/",
				data : _data+"&service_dependency="+checkedValue,
				cache : false,
				beforeSend : function(xhr, settings) {
					var csrftoken = $.cookie('csrftoken');
					xhr.setRequestHeader("X-CSRFToken", csrftoken);
				},
				success : function(msg) {
					var dataObj = msg
					if (dataObj["status"] == "success") {
						app_oneKeyDeploy(tenantName,service_name);
					} else {
						swal("创建失败")
						$("#language_btn").removeAttr('disabled')
					}
				},
				error : function() {
					swal("系统异常,请重试");
					$("#language_btn").removeAttr('disabled')
				}
			})
		})
});




function app_oneKeyDeploy(tenantName, serviceAlias) {
	_url = "/ajax/" + tenantName + '/' + serviceAlias + "/app-deploy/"
	$.ajax({
		type : "POST",
		url : _url,
		cache : false,
		beforeSend : function(xhr, settings) {
			var csrftoken = $.cookie('csrftoken');
			xhr.setRequestHeader("X-CSRFToken", csrftoken);
		},
		success : function(msg) {
			window.location.href = "/apps/" + tenantName + "/" + serviceAlias + "/detail/"
		},
		error : function() {
			// swal("系统异常");
		}
	})
}