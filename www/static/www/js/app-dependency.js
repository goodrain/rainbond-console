$(function() {
  $('#service_dependency_finished').click(
	function() {		
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
		
		var tenantName = $('#tenantName').val();
		var service_name = $('#service_name').val();
		var _data = $("form").serialize();
		$("#service_dependency_finished").attr('disabled', "true")	
		$.ajax({
			type : "post",
			url : "/apps/" + tenantName + "/"+ service_name + "/app-dependency/",
			data : _data,
			cache : false,
			beforeSend : function(xhr, settings) {
				var csrftoken = $.cookie('csrftoken');
				xhr.setRequestHeader("X-CSRFToken", csrftoken);
			},
			success : function(msg) {
				var dataObj = msg;
				if (dataObj["status"] == "success") {
					window.location.href = "/apps/" + tenantName + "/"
							+ service_name + "/app-waiting/"
				} else {
					alert("创建失败")
					$("#service_dependency_finished").removeAttr('disabled')
				}
			},
			error : function() {
				alert("系统异常,请重试");
				$("#service_dependency_finished").removeAttr('disabled')
			}
		})
	})
});

