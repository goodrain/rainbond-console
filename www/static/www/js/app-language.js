$(function() {
	$('#language_btn').click(
		function() {
			var checkedValue="";
			var val = '';  
			$("[name='service_dependency']:checkbox").each(function(){  
				if(this.checked)
					checkedValue= checkedValue +","+$(this).val() 
			});
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
						window.location.href = "/apps/" + tenantName + "/"
								+ service_name + "/detail/"
					} else {
						alert("创建失败")
						$("#language_btn").attr('disabled', "false")
					}
				},
				error : function() {
					alert("系统异常,请重试");
					$("#language_btn").attr('disabled', "false")
				}
			})
		})
});