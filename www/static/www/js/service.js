function goto_deploy(tenantName, service_alias) {
	window.location.href = "/apps/" + tenantName + "/" + service_alias
			+ "/detail/"
}

function service_oneKeyDeploy(categroy, serviceAlias, tenantName, isreload) {
	$("#onekey_deploy").attr('disabled', "true")
	_url = "/ajax/" + tenantName + '/' + serviceAlias + "/app-deploy/"
	if (categroy == "application") {
		_url = "/ajax/" + tenantName + '/' + serviceAlias + "/app-deploy/"
	} else {
		swal("暂时不支持")
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
				swal("操作成功")
			} else if (dataObj["status"] == "language") {
				swal("应用语言监测为通过")
				forurl = "/apps/" + tenantName + "/" + serviceAlias
						+ "/detail/"
				window.open(forurl, target = "_parent")
			} else if (dataObj["status"] == "often") {
				swal("上次部署正在进行中，请稍后再试")
			} else {
				swal("操作失败")
				$("#onekey_deploy").removeAttr("disabled")
			}
			if (isreload == 'yes') {
				forurl = "/apps/" + tenantName + "/" + serviceAlias
						+ "/detail/"
				window.open(forurl, target = "_parent")
			}
		},
		error : function() {
			$("#onekey_deploy").removeAttr("disabled")
			// swal("系统异常");
		}
	})
}

function service_my_onOperation(service_id, service_alias, tenantName) {
	var taction = $("#operate_" + service_id).attr("data" + service_id)
	if (taction != "stop" && taction != "restart") {
		swal("系统异常");
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
				swal("操作成功")
			} else {
				swal("操作失败")
			}
		},
		error : function() {
			swal("系统异常");
		}
	})
}

function service_onOperation(service_id, service_alias, tenantName) {
	var taction = $("#service_status_value").val()
	if (taction != "stop" && taction != "restart") {
		swal("参数异常");
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
				swal("操作成功")
			} else {
				swal("操作失败")
			}
		},
		error : function() {
			swal("系统异常");
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
				swal("操作成功")
			} else {
				swal("操作失败")
			}
		},
		error : function() {
			swal("系统异常");
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
				swal("设置成功")
			} else if (dataObj["status"] == "overtop") {
				swal("免费资源已达上限，不能升级")
			} else {
				swal("设置失败")
			}
		},
		error : function() {
			swal("系统异常,请重试");
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
					swal("设置成功")
				} else if (dataObj["status"] == "overtop") {
					swal("免费资源已达上限，不能升级")
				} else {
					swal("设置失败")
				}
			},
			error : function() {
				swal("系统异常,请重试");
			}
		})
	}
}

function delete_service(tenantName, service_alias) {
	swal({
		title: "确定删除当前服务吗？",
		type: "warning",
	    showCancelButton: true,
		confirmButtonColor: "#DD6B55",
		confirmButtonText: "确定",
		cancelButtonText: "取消",
		closeOnConfirm: false,
		closeOnCancel: false
	}, function (isConfirm) {
		if(isConfirm) {
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
			});
		}else{
			swal.close();
		}
	});
}
