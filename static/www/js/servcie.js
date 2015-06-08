function deploy(key, tenantName) {
	var service_name = $("#service_name").val();
	var desc = $("#desc").val();
	var _data = $("form").serialize();
	$.ajax({
		type : "POST",
		url : "/apps/" + tenantName + "/market/",
		data : "service_key=" + key,
		cache : false,
		beforeSend : function(xhr, settings) {
			var csrftoken = $.cookie('csrftoken');
			xhr.setRequestHeader("X-CSRFToken", csrftoken);
		},
		success : function(msg) {
			var dataObj = eval("(" + msg + ")");
			if (dataObj["status"] == "exist") {
				alert("服务已部署")
			} else if (dataObj["status"] == "success") {
				window.location.href = "/apps/" + tenantName
						+ "/detail/?service_id=" + dataObj["service_id"]
			} else {
				alert("服务部署失败")
			}
		},
		error : function() {
			//alert("系统异常");
		}
	})
}

function service_detail(service_id, tenantName) {
	window.location.href = "/apps/" + tenantName + "/detail/?service_id="
			+ service_id
}

function service_oneKeyDeploy(categroy, service_id, tenantName) {
	_url = "/apps/" + tenantName + "/market/"
    var serviceAlias = $('#mytags').attr('service');
	if (categroy == "application") {
		_url = "/ajax/" + tenantName + '/' + serviceAlias + "/app-deploy/"
	} else {
		alert("暂时不支持")
		return;
	}
	$.ajax({
		type : "POST",
		url : _url,
        data : 'service_key=' + service_id,
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
			//alert("系统异常");
		}
	})
}

function service_onOperation(service_id, tenantName) {
	var taction = "afwef"
	if ($(".btn.btn-danger.yinyongbtn").attr("data" + service_id) == "Running") {
		taction = "stop"
	} else {
		taction = "restart"
	}
	$.ajax({
		type : "POST",
		url : "/apps/" + tenantName + "/detail/",
		data : "service_id=" + service_id + "&action=" + taction,
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
			//alert("系统异常");
		}
	})
}

function domainSubmit(service_id, tenantName) {
	var domain_name = $("#service_app_name").val();
	$.ajax({
		type : "POST",
		url : "/apps/" + tenantName + "/domain/",
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
			//alert("系统异常");
		}
	})
}

function appCreate(tenantName) {
	var service_name = $("#service_name").val();
	var serviceReg = /^[a-zA-Z0-9]{4,}$/;
	var result = true;
	if (!serviceReg.test(service_name)) {
		alert("服务名字只支持4位的字母与数字组合")
		result = false;
		$('#service_name').focus();
	}
	if (!result) {
		return;
	}
	var desc = $("#desc").val();
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
			} else if (dataObj["status"] == "success") {
				window.location.href = "/apps/" + tenantName
						+ "/app-deploy?service_id=" + dataObj["service_id"]
			} else {
				alert("创建失败")
			}
		},
		error : function() {
			alert("系统异常,请重试");
		}
	})
}

function appDeploy(tenantName) {
	var git_url = $("#git_url").val();
	var service_id = $("#service_id").val();
	var _data = $("form").serialize();
	$.ajax({
		type : "post",
		url : "/apps/" + tenantName + "/app-deploy/",
		data : _data,
		cache : false,
		beforeSend : function(xhr, settings) {
			var csrftoken = $.cookie('csrftoken');
			xhr.setRequestHeader("X-CSRFToken", csrftoken);
		},
		success : function(msg) {
			var dataObj = eval("(" + msg + ")");
			if (dataObj["status"] == "success") {
				window.location.href = "/apps/" + tenantName
						+ "/detail?service_id=" + service_id
			} else {
				alert("部署失败")
			}
		},
		error : function() {
			alert("系统异常,请重试");
		}
	})
}
