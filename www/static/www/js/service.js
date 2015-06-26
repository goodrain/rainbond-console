//服务创建
function service_create(tenantName, service_key) {
	window.location.href = "/apps/" + tenantName
			+ "/service-deploy/?service_key=" + service_key
}

// 服务部署
function service_deploy(tenantName, service_key) {
	var service_name = $("#service_name").val();
	var desc = $("#desc").val();
	var _data = $("form").serialize();
	$.ajax({
		type : "POST",
		url : "/apps/" + tenantName + "/service-deploy/",
		data : _data,
		cache : false,
		beforeSend : function(xhr, settings) {
			var csrftoken = $.cookie('csrftoken');
			xhr.setRequestHeader("X-CSRFToken", csrftoken);
		},
		success : function(msg) {
			var dataObj = eval("(" + msg + ")");
			if (dataObj["status"] == "exist") {
				alert("服务已存在")
				window.location.href = "/apps/" + tenantName + "/"
						+ service_alias + "/detail/"
			} else if (dataObj["status"] == "overtop") {
				alert("免费资源已达上限，不能部署")
			} else if (dataObj["status"] == "success") {
				window.location.href = "/apps/" + tenantName + "/"
						+ dataObj["service_alias"] + "/detail/"
			} else {
				alert("服务部署失败")
			}
		},
		error : function() {
			// alert("系统异常");
		}
	})
}

function goto_deploy(tenantName, service_alias) {
	window.location.href = "/apps/" + tenantName + "/" + service_alias
			+ "/detail/"
}

function service_oneKeyDeploy(categroy, serviceAlias, tenantName) {
	$("#onekey_deploy").attr('disabled', "true")
	_url = "/ajax/" + tenantName + '/' + serviceAlias + "/app-deploy/"
	if (categroy == "application") {
		_url = "/ajax/" + tenantName + '/' + serviceAlias + "/app-deploy/"
	} else {
		alert("暂时不支持")
		return;
	}
	$.ajax({
		type : "POST",
		url : _url,
		cache : false,
		beforeSend : function(xhr, settings) {
			var csrftoken = $.cookie('csrftoken');
			xhr.setRequestHeader("X-CSRFToken", csrftoken);
		},
		success : function(msg) {
			var dataObj = msg;
			if (dataObj["status"] == "success") {
				alert("操作成功")
			} else if (dataObj["status"] == "often") {
				alert("上次部署正在进行中，请稍后再试")
			} else {
				alert("操作失败")
				$("#onekey_deploy").removeAttr("disabled")
			}
		},
		error : function() {
			$("#onekey_deploy").removeAttr("disabled")
			// alert("系统异常");
		}
	})
}

function service_my_onOperation(service_id, service_alias, tenantName) {
	var taction = $("#operate_" + service_id).attr("data" + service_id)
	if (taction != "stop" && taction != "restart") {
		alert("系统异常");
		window.location.href = window.location.href;
	}
	$.ajax({
		type : "POST",
		url : "/ajax/" + tenantName + "/" + service_alias + "/manage/",
		data : "service_id=" + service_id + "&action=" + taction,
		cache : false,
		beforeSend : function(xhr, settings) {
			var csrftoken = $.cookie('csrftoken');
			xhr.setRequestHeader("X-CSRFToken", csrftoken);
		},
		success : function(msg) {
			var dataObj = msg
			if (dataObj["status"] == "success") {
				alert("操作成功")
			} else {
				alert("操作失败")
			}
		},
		error : function() {
			alert("系统异常");
		}
	})
}

function service_onOperation(service_id, service_alias, tenantName) {
	var taction = $("#service_status_operate").attr("data" + service_id)
	if (taction != "stop" && taction != "restart") {
		alert("参数异常");
		window.location.href = window.location.href;
	}
	$.ajax({
		type : "POST",
		url : "/ajax/" + tenantName + "/" + service_alias + "/manage/",
		data : "service_id=" + service_id + "&action=" + taction,
		cache : false,
		beforeSend : function(xhr, settings) {
			var csrftoken = $.cookie('csrftoken');
			xhr.setRequestHeader("X-CSRFToken", csrftoken);
		},
		success : function(msg) {
			var dataObj = msg
			if (dataObj["status"] == "success") {
				alert("操作成功")
			} else {
				alert("操作失败")
			}
		},
		error : function() {
			alert("系统异常");
		}
	})
}

function domainSubmit(service_id, tenantName, service_alias) {
	var domain_name = $("#service_app_name").val();
	if (domain_name == "") {
		return;
	}
	$.ajax({
		type : "POST",
		url : "/apps/" + tenantName + "/" + service_alias + "/domain/",
		data : "service_id=" + service_id + "&domain_name=" + domain_name,
		cache : false,
		beforeSend : function(xhr, settings) {
			var csrftoken = $.cookie('csrftoken');
			xhr.setRequestHeader("X-CSRFToken", csrftoken);
		},
		success : function(msg) {
			var dataObj = eval("(" + msg + ")");
			if (dataObj["status"] == "success") {
				alert("操作成功")
			} else {
				alert("操作失败")
			}
		},
		error : function() {
			alert("系统异常");
		}
	})
}

function appCreate(tenantName) {
	$("#submit1").attr('disabled', "true")
	var _data = $("form").serialize();
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
			var dataObj = eval("(" + msg + ")");
			if (dataObj["status"] == "exist") {
				alert("服务名已存在")
			} else if (dataObj["status"] == "overtop") {
				alert("免费资源已达上限，不能创建")
			} else if (dataObj["status"] == "empty") {
				alert("应用名称不能为空")
			}else if (dataObj["status"] == "code_from") {
				alert("应用资源库未选择")
			} else if (dataObj["status"] == "success") {
				service_alias = dataObj["service_alias"]
				window.location.href = "/apps/" + tenantName + "/"
						+ service_alias + "/detail/"
			} else {
				alert("创建失败")
			}
		},
		error : function() {
			alert("系统异常,请重试");
		}
	})
}

function service_upgrade(tenantName, service_alias) {
	var service_min_config = $("#serviceMemorys").val();
	memory = 128 * Math.pow(2, service_min_config - 1)
	cpu = 100 * Math.pow(2, service_min_config - 1)
	$.ajax({
		type : "post",
		url : "/ajax/" + tenantName + "/" + service_alias + "/upgrade/",
		data : "action=vertical&memory=" + memory + "&cpu=" + cpu,
		cache : false,
		beforeSend : function(xhr, settings) {
			var csrftoken = $.cookie('csrftoken');
			xhr.setRequestHeader("X-CSRFToken", csrftoken);
		},
		success : function(msg) {
			var dataObj = msg;
			if (dataObj["status"] == "success") {
				alert("设置成功")
			} else if (dataObj["status"] == "overtop") {
				alert("免费资源已达上限，不能升级")
			} else {
				alert("设置失败")
			}
		},
		error : function() {
			alert("系统异常,请重试");
		}
	})
}

function app_upgrade(tenantName, service_alias) {
	var service_min_node = $("#serviceNods").val();
	if (service_min_node >= 0) {
		$.ajax({
			type : "post",
			url : "/ajax/" + tenantName + "/" + service_alias + "/upgrade/",
			data : "action=horizontal&node_num=" + (service_min_node - 1),
			cache : false,
			beforeSend : function(xhr, settings) {
				var csrftoken = $.cookie('csrftoken');
				xhr.setRequestHeader("X-CSRFToken", csrftoken);
			},
			success : function(msg) {
				var dataObj = msg;
				if (dataObj["status"] == "success") {
					alert("设置成功")
				} else if (dataObj["status"] == "overtop") {
					alert("免费资源已达上限，不能升级")
				} else {
					alert("设置失败")
				}
			},
			error : function() {
				alert("系统异常,请重试");
			}
		})
	}
}

function delete_service(tenantName, service_alias) {
	var statu = confirm("确定删除当前服务吗?");
	if (statu) {
		$.ajax({
			type : "POST",
			url : "/ajax/" + tenantName + "/" + service_alias + "/manage/",
			data : "action=delete",
			cache : false,
			beforeSend : function(xhr, settings) {
				var csrftoken = $.cookie('csrftoken');
				xhr.setRequestHeader("X-CSRFToken", csrftoken);
			},
			success : function(msg) {
				var dataObj = msg
				if (dataObj["status"] == "success") {
					alert("操作成功")
					window.location.href = "http://user.goodrain.com/"
				} else {
					alert("操作失败")
				}
			},
			error : function() {
				alert("系统异常");
			}
		})
	}
}
