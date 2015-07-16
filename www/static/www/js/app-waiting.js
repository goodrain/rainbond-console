var gitcodechecktimmer
$(function() {
	gitcodechecktimmer = setInterval("getGitCodeCheck()", 3000);
	$('#service_code_waiting').click(
	 function() {
		 var tenantName = $('#tenantName').val();
		 var service_name = $('#service_name').val();
		 window.location.href = "/apps/" + tenantName + "/" + service_name + "/app-language/"
	})
});

function getGitCodeCheck() {
	var tenantName = $('#tenantName').val();
	var service_name = $('#service_name').val();
	if (service_name != "" && service_name != undefined) {
		$.ajax({
			type : "GET",
			url : "/ajax/" + tenantName + "/" + service_name + "/check/",
			cache : false,
			success : function(msg) {
				var dataObj = msg;
				if (dataObj["status"] == "checked") {
					clearInterval(gitcodechecktimmer);
					$("#git_code_upload").html("代码已提交，语言识别为 "+dataObj["language"])
				} else if (dataObj["status"] == "check_error") {
					$("#git_code_upload").html("语言未识别，请重新提交代码...")
				}
			},
			error : function() {
				// swal("系统异常");
			}
		})
	}
}

function app_create_delete(){
	var tenantName = $('#tenantName').val();
	var service_name = $('#service_name').val();
	if (service_name != "" && service_name != undefined) {
		var statu = confirm("确定删除当前服务吗?");
		if (statu) {
			$.ajax({
				type : "POST",
				url : "/ajax/" + tenantName + "/" + service_name + "/manage/",
				data : "action=delete",
				cache : false,
				beforeSend : function(xhr, settings) {
					var csrftoken = $.cookie('csrftoken');
					xhr.setRequestHeader("X-CSRFToken", csrftoken);
				},
				success : function(msg) {
					var dataObj = msg
					if (dataObj["status"] == "success") {
						swal("操作成功")
						window.location.href = "/apps/" + tenantName
					} else if (dataObj["status"] == "dependency") {
						swal("当前服务被依赖不能删除")
					} else {
						swal("操作失败")
					}
				},
				error : function() {
					swal("系统异常");
				}
			})
		}
	}
}