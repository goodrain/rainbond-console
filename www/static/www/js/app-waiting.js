$(function() {
	setInterval("getGitCodeCheck()", 3000);
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
					window.location.href = "/apps/" + tenantName + "/"
							+ service_name + "/app-language/"
				} else if (dataObj["status"] == "check_error") {
					$("#git_code_upload").html("语言未识别，请重新提交代码...")
				}
			},
			error : function() {
				// alert("系统异常");
			}
		})
	}
}