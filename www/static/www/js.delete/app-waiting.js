var gitcodechecktimmer;
var requestNumber = 0
$(function() {
	$('#service_code_waiting').attr('disabled', "true");
	getGitCodeCheck();
	$('#service_code_waiting').click(
			function() {
				var tenantName = $('#tenantName').val();
				var service_name = $('#service_name').val();
				window.location.href = "/apps/" + tenantName + "/"
						+ service_name + "/app-language/";
			});
	$('.ctrl_viewdetailinfo').click(function() {
		$('.ctrl_garyinfo', $(this)).remove();
		$(this).parent().next().slideDown();
	});
});

function getGitCodeCheck() {
	var tenantName = $('#tenantName').val();
	var service_name = $('#service_name').val();
	if (service_name != "" && service_name != undefined) {
		requestNumber = requestNumber + 1
		$.ajax({
			type : "GET",
			url : "/ajax/" + tenantName + "/" + service_name
					+ "/check/?requestNumber=" + requestNumber,
			cache : false,
			success : function(msg) {
				var dataObj = msg;
				if (dataObj["status"] == "checked") {
					clearTimeout(gitcodechecktimmer);
					$("#git_code_upload").html(
							"代码已提交，语言识别为 " + dataObj["language"]);
					$("#service_code_waiting").removeAttr('disabled')
				} else if (dataObj["status"] == "check_error") {
					$("#git_code_upload").html("语言未识别，请重新提交代码...");
				}
			},
			error : function() {
				// swal("系统异常");
			}
		})
		
		gitcodechecktimmer=setTimeout("getGitCodeCheck()",1000*Math.ceil(requestNumber / 5)+3000)
	}
}

// function app_create_delete() {
// 	swal({
// 		title: "确定要停止创建当前的应用吗？",
// 		type: "warning",
// 	    showCancelButton: true,
// 		confirmButtonColor: "#DD6B55",
// 		confirmButtonText: "确定",
// 		cancelButtonText: "取消",
// 		closeOnConfirm: false,
// 		closeOnCancel: false
// 	}, function (isConfirm) {
// 		if(isConfirm) {
// 			var tenantName = $('#tenantName').val();
// 			var service_name = $('#service_name').val();
// 			$.ajax({
// 				type : "POST",
// 				url : "/ajax/" + tenantName + "/" + service_name + "/manage/",
// 				data : "action=delete",
// 				cache : false,
// 				beforeSend : function(xhr, settings) {
// 					var csrftoken = $.cookie('csrftoken');
// 					xhr.setRequestHeader("X-CSRFToken", csrftoken);
// 					swal({
// 						title: "正在执行删除操作，请稍候...",
// 						text: "5秒后自动关闭",
// 						timer: 5000,
// 						showConfirmButton : false
// 					});
// 				},
// 				success : function(msg) {
// 					var dataObj = msg
// 					if (dataObj["status"] == "success") {
// 						swal("操作成功");
// 						window.location.href = "/apps/"+tenantName+"/service-entrance/"
// 					} else if (dataObj["status"] == "often") {
// 						swal("上次操作正在进行中，稍后再试")
// 					}else if (dataObj["status"] == "dependency") {
// 						swal("当前服务被依赖不能删除");
// 					} else {
// 						swal("操作失败");
// 					}
// 				},
// 				error : function() {
// 					swal("系统异常");
// 				}
// 			});
// 		}else{
// 			swal.close();
// 		}
// 	});
// }

function app_create_delete() {
	swal({
		title: "确定要停止创建当前的应用吗？",
		type: "warning",
		showCancelButton: true,
		confirmButtonColor: "#DD6B55",
		confirmButtonText: "确定",
		cancelButtonText: "取消",
		closeOnConfirm: false,
		closeOnCancel: false
	}, function (isConfirm) {
		if(isConfirm) {
			var tenantName = $('#tenantName').val();
			var service_name = $('#service_name').val();
			var event_id = '';
			$.ajax({
				type: "POST",
				url: "/ajax/" + tenantName + '/' + service_name + "/events",
				data: "action=delete",
				cache: false,
				async: false,
				beforeSend: function (xhr, settings) {
					var csrftoken = $.cookie('csrftoken');
					xhr.setRequestHeader("X-CSRFToken", csrftoken);
				},
				success: function (data) {
					if (data["status"] == "often") {
						swal("上次操作进行中，请稍后！");
						return ""
					} else if (data["status"] == "success") {
						event_id = data["event"]["event_id"];
					} else {
						swal("系统异常！");
					}

				},
				error: function () {
					swal("系统异常");
				}
			});
			if( event_id )
			{
				$.ajax({
					type : "POST",
					url : "/ajax/" + tenantName + "/" + service_name + "/manage/",
					data : "action=delete&event_id="+event_id,
					cache : false,
					beforeSend : function(xhr, settings) {
						var csrftoken = $.cookie('csrftoken');
						xhr.setRequestHeader("X-CSRFToken", csrftoken);
						swal({
							title: "正在执行删除操作，请稍候...",
							text: "5秒后自动关闭",
							timer: 5000,
							showConfirmButton : false
						});
					},
					success : function(msg) {
						var dataObj = msg
						if (dataObj["status"] == "success") {
							swal("操作成功");
							window.location.href = "/apps/"+tenantName+"/service-entrance/"
						} else if (dataObj["status"] == "often") {
							swal("上次操作正在进行中，稍后再试")
						}else if (dataObj["status"] == "dependency") {
							swal("当前服务被依赖不能删除");
						} else {
							swal("操作失败");
						}
					},
					error : function() {
						swal("系统异常");
					}
				});
			}
		}else{
			swal.close();
		}
	});
}