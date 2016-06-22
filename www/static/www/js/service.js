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
			} else if (dataObj["status"] == "owed") {
				swal("余额不足请及时充值")
			} else if (dataObj["status"] == "language") {
				swal("应用语言监测未通过")
				forurl = "/apps/" + tenantName + "/" + serviceAlias
						+ "/detail/"
				window.open(forurl, target = "_parent")
			} else if (dataObj["status"] == "often") {
				swal("部署正在进行中，请稍后")
			} else if (dataObj["status"] == "over_memory") {
				swal("资源已达上限，不能升级")
			} else if (dataObj["status"] == "over_money") {
				swal("余额不足，不能升级")
			} else {
				swal("操作失败")
				$("#onekey_deploy").removeAttr("disabled")
			}
			if (isreload == 'yes') {
				forurl = "/apps/" + tenantName + "/" + serviceAlias
						+ "/detail/"
				window.open(forurl, target = "_parent")
			}
			$("#onekey_deploy").removeAttr("disabled")
		},
		error : function() {
			$("#onekey_deploy").removeAttr("disabled")
			swal("系统异常");
		}
	})
}

function service_my_onOperation(service_id, service_alias, tenantName) {
	$("#operate_"+service_id).attr('disabled', "true")
	var taction = $("#operate_" + service_id).attr("data" + service_id)
	if (taction != "stop" && taction != "restart") {
		swal("系统异常");
		window.location.href = window.location.href;
	}
	$.ajax({
		type : "POST",
		url : "/ajax/" + tenantName + "/" + service_alias + "/manage",
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
			} else if (dataObj["status"] == "often") {
				swal("操作正在进行中，请稍后")
			} else if (dataObj["status"] == "owed") {
				swal("余额不足请及时充值")
			} else if (dataObj["status"] == "over_memory") {
				swal("资源已达上限，不能升级")
			} else if (dataObj["status"] == "over_money") {
				swal("余额不足，不能升级")
			} else {
				swal("操作失败")
			}
			$("#operate_"+service_id).removeAttr("disabled")
		},
		error : function() {
			swal("系统异常");
			$("#operate_"+service_id).removeAttr("disabled")
		}
	})
}

// 服务重启关闭
function service_onOperation(service_id, service_alias, tenantName) {
	var taction = $("#service_status_value").val()
	if (taction != "stop" && taction != "restart") {
		swal("参数异常");
		window.location.href = window.location.href;
	}
	$("#service_status_operate").attr('disabled', "true")
	$.ajax({
		type : "POST",
		url : "/ajax/" + tenantName + "/" + service_alias + "/manage",
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
			} else if (dataObj["status"] == "often") {
				swal("操作正在进行中，请稍后")
			} else if (dataObj["status"] == "owed") {
				swal("余额不足请及时充值")
			} else if (dataObj["status"] == "over_memory") {
				swal("免费资源已达上限，不能操作")
			} else if (dataObj["status"] == "over_money") {
				swal("余额不足，不能操作")
			} else {
				swal("操作失败")
			}
			$("#service_status_operate").removeAttr("disabled")
		},
		error : function() {
			swal("系统异常");
			$("#service_status_operate").removeAttr("disabled");
		}
	})
}

var csrftoken = $.cookie('csrftoken');
var tenantName = $('#mytags').attr('tenant');
var serviceAlias = $('#mytags').attr('service');

$(document).ready(
	function() {
		if ($('#git_branch').length) {
			$.ajax({
				type: "get",
				url: "/ajax/" + tenantName + "/" + serviceAlias + "/branch",
				cache: false,
				success: function (data) {
					for (var i in data.branchs) {
						var opt = $("<option/>").val(data.branchs[i]).html(data.branchs[i])
						if (data.branchs[i] == data.current) {
							opt.prop('selected', true)
						}
						$('#git_branch').prepend(opt)
					}
				}
			})
		}
		
	}
)

// 服务分支
function service_branch_change(tenantName, service_alias) {
	var branch = $("#git_branch").val();
	$.ajax({
		type : "post",
		url : "/ajax/" + tenantName + "/" + service_alias + "/branch",
		data : "branch=" + branch,
		cache : false,
		beforeSend : function(xhr, settings) {
			var csrftoken = $.cookie('csrftoken');
			xhr.setRequestHeader("X-CSRFToken", csrftoken);
		},
		success : function(msg) {
			swal("切换完毕, 下次部署后生效");
		},
		error : function() {
			swal("系统异常,请重试");
		}
	})
}

// 域名绑定
function domainSubmit(action, service_id, tenantName, service_alias) {
	if (action != "start" && action != "close") {
		swal("参数异常");
		window.location.href = window.location.href;
	}
	var domain_name = $("#service_app_name").val();
	if (domain_name == "") {
		swal("输入有效的域名");
		return;
	}
	$.ajax({
		type : "POST",
		url : "/ajax/" + tenantName + "/" + service_alias + "/domain",
		data : "service_id=" + service_id + "&domain_name=" + domain_name
				+ "&action=" + action,
		cache : false,
		beforeSend : function(xhr, settings) {
			var csrftoken = $.cookie('csrftoken');
			xhr.setRequestHeader("X-CSRFToken", csrftoken);
		},
		success : function(msg) {
			var dataObj = msg
			if (dataObj["status"] == "success") {
				swal("操作成功")
				if (window.location.href.indexOf("fr=") < 0) {
					window.location.href = window.location.href
							+ "?fr=settings";
				} else {
					window.location.href = window.location.href
				}
			} else if (dataObj["status"] == "limit") {
				swal("免费用户不允许")
			} else if (dataObj["status"] == "exist") {
				swal("域名已存在")
			} else {
				swal("操作失败")
			}
		},
		error : function() {
			swal("系统异常");
		}
	})
}

// 服务垂直升级
function service_upgrade(tenantName, service_alias) {
	var service_min = $("#serviceMemorys").val();
	memory = service_min
	cpu = 20 * (service_min/128)
	$.ajax({
		type : "post",
		url : "/ajax/" + tenantName + "/" + service_alias + "/upgrade",
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
			} else if (dataObj["status"] == "owed") {
				swal("余额不足请及时充值")
			} else if (dataObj["status"] == "often") {
				swal("操作正在进行中，请稍后")
			} else if (dataObj["status"] == "over_memory") {
				swal("资源已达上限，不能升级")
			} else if (dataObj["status"] == "over_money") {
				swal("余额不足，不能升级")
			} else {
				swal("设置失败")
			}
		},
		error : function() {
			swal("系统异常,请重试");
		}
	})
}

// 服务水平升级
function app_upgrade(tenantName, service_alias) {
	var service_min_node = $("#serviceNods").val();
	if (service_min_node >= 0) {
		$.ajax({
			type : "post",
			url : "/ajax/" + tenantName + "/" + service_alias + "/upgrade/",
			data : "action=horizontal&node_num=" + service_min_node,
			cache : false,
			beforeSend : function(xhr, settings) {
				var csrftoken = $.cookie('csrftoken');
				xhr.setRequestHeader("X-CSRFToken", csrftoken);
			},
			success : function(msg) {
				var dataObj = msg;
				if (dataObj["status"] == "success") {
					swal("设置成功")
				} else if (dataObj["status"] == "owed") {
					swal("余额不足请及时充值")
				} else if (dataObj["status"] == "often") {
					swal("操作正在进行中，请稍后")
				} else if (dataObj["status"] == "over_memory") {
					swal("资源已达上限，不能升级")
				} else if (dataObj["status"] == "over_money") {
					swal("余额不足，不能升级")
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

// 服务扩容方式修改
function extends_upgrade(tenantName, service_alias) {
    var extend_method = $("#extend_method").val();
    if (extend_method !="") {
        $.ajax({
            type : "post",
            url : "/ajax/" + tenantName + "/" + service_alias + "/upgrade/",
            data : "action=extend_method&extend_method=" + extend_method,
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {
                var dataObj = msg;
                if (dataObj["status"] == "success") {
                    swal("设置成功")
                } else if (dataObj["status"] == "owed") {
                    swal("余额不足请及时充值")
                } else if (dataObj["status"] == "often") {
                    swal("操作正在进行中，请稍后")
                } else if (dataObj["status"] == "no_support") {
                    swal("当前服务不支持修改")
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

// 服务删除
function delete_service(tenantName, service_alias) {
	swal({
		title : "确定删除当前服务吗？",
		type : "warning",
		showCancelButton : true,
		confirmButtonColor : "#DD6B55",
		confirmButtonText : "确定",
		cancelButtonText : "取消",
		closeOnConfirm : false,
		closeOnCancel : false
	}, function(isConfirm) {
		if (isConfirm) {
			$.ajax({
				type : "POST",
				url : "/ajax/" + tenantName + "/" + service_alias + "/manage/",
				data : "action=delete",
				cache : false,
				beforeSend : function(xhr, settings) {
					var csrftoken = $.cookie('csrftoken');
					xhr.setRequestHeader("X-CSRFToken", csrftoken);
					swal({
						title : "正在执行删除操作，请稍候...",
						text : "5秒后自动关闭",
						timer : 5000,
						showConfirmButton : false
					});
				},
				success : function(msg) {
					var dataObj = msg
					if (dataObj["status"] == "success") {
						swal("操作成功");
						window.location.href = "/apps/" + tenantName
					} else if (dataObj["status"] == "often") {
						swal("上次操作正在进行中，稍后再试")
					} else if (dataObj["status"] == "evn_dependency") {
						var dep_service = dataObj["dep_service"]
						if (typeof(dep_service) == "undefined"){
							swal("当前服务被环境依赖不能删除");
						}else{
							swal("当前服务被("+dep_service+")环境依赖不能删除");
						}
					} else if (dataObj["status"] == "mnt_dependency") {
                        var dep_service = dataObj["dep_service"]
                        if (typeof(dep_service) == "undefined"){
                            swal("当前服务被挂载依赖不能删除");
                        }else{
                            swal("当前服务被("+dep_service+")挂载依赖不能删除");
                        }
                    } else {
						swal("操作失败");
					}
				},
				error : function() {
					swal("系统异常");
				}
			});
		} else {
			swal.close();
		}
	});
}

function buid_relation(action, curServiceName, depServiceName, tenantName) {
	if (action != "add" && action != "cancel") {
		swal("系统异常");
		window.location.href = window.location.href;
	}
	$.ajax({
		type : "POST",
		url : "/ajax/" + tenantName + "/" + curServiceName + "/relation",
		data : "dep_service_alias=" + depServiceName + "&action=" + action,
		cache : false,
		beforeSend : function(xhr, settings) {
			var csrftoken = $.cookie('csrftoken');
			xhr.setRequestHeader("X-CSRFToken", csrftoken);
		},
		success : function(msg) {
			var dataObj = msg
			if (dataObj["status"] == "success") {
				swal("操作成功")
				if (window.location.href.indexOf("fr=") < 0) {
					window.location.href = window.location.href
							+ "?fr=relations";
				} else {
					window.location.href = window.location.href
				}
			} else {
				swal("操作失败")
			}
		},
		error : function() {
			// swal("系统异常");
		}
	})
}

function add_new_attr(service_id,port) {
	var msg = ''
	msg = msg + '<tr>'
	msg = msg + '<td><input name ="' + service_id+ '_name" value=""></td>'
	msg = msg + '<td><input name ="' + service_id+ '_attr_name" value=""></td>'
	msg = msg + '<td><input name ="' + service_id+ '_attr_value" value=""></td>'
	msg = msg + '<td><input type="hidden" name ="' + service_id+ '_attr_id" value="0"><button type="button" class="btn btn-success btn-xs" onclick="attr_delete(this);">删除</button></td>'
	msg = msg + '</tr>'
	$("#envVartable tr:last").after(msg);
}

function attr_save(service_id, tenant_name, service_name) {
	var id_obj = $('input[name=' + service_id + '_serviceNoChange]');
	var id =[];
	for (var i = 0; i < id_obj.length; i++) {
		id.push(id_obj[i].value)
	}
	var reg = /[\u4E00-\u9FA5\uF900-\uFA2D]/
	var regother = /[\uFF00-\uFFEF]/
	var nochange_name_obj = $('input[name=' + service_id + '_nochange_name]');
	var nochange_name = [];
	for (var i = 0; i < nochange_name_obj.length; i++) {
		var tmp = nochange_name_obj[i].value;
		if (reg.test(tmp) || regother.test(tmp)){
			swal("变量名不正确");
			return false;
		}
		if (tmp == "") {
			swal("必填项不能为空");
			return false;
		} else {
			nochange_name.push(tmp)
		}
	}
	
	var name_obj = $('input[name=' + service_id + '_name]');
	var name = [];
	for (var i = 0; i < name_obj.length; i++) {
		if (name_obj[i].value == "") {
			swal("必填项不能为空");
			return false;
		} else {
			name.push(name_obj[i].value)
		}
	}
	var attr_name_obj = $('input[name=' + service_id + '_attr_name]');
	var attr_name = [];
	for (var i = 0; i < attr_name_obj.length; i++) {
		var tmp = attr_name_obj[i].value;
		if (reg.test(tmp) || regother.test(tmp)){
			swal("变量名不正确");
			return false;
		}
		if (tmp == "") {
			swal("必填项不能为空");
			return false;
		} else {
			attr_name.push(tmp)
		}
	}
	var attr_value_obj = $('input[name=' + service_id + '_attr_value]');
	var attr_value = [];
	for (var i = 0; i < attr_value_obj.length; i++) {
		var tmp = attr_value_obj[i].value;
		if (reg.test(tmp) || regother.test(tmp)){
			swal("变量名不正确");
			return false;
		}
		if (tmp == "") {
			swal("必填项不能为空");
			return false;
		} else {
			attr_value.push(tmp)
		}
	}
	var attr_id_obj = $('input[name=' + service_id + '_attr_id]');
	var attr_id = [];
	for (var i = 0; i < attr_id_obj.length; i++) {
		var tmp = attr_id_obj[i].value;
		attr_id.push(tmp)
	}
	$.ajax({
		type : "POST",
		url : "/ajax/" + tenant_name + "/" + service_name + "/envvar",
		data : "nochange_name="+nochange_name.toString()+"&id="+id.toString()+"&name=" + name.toString() + "&attr_name="
			   + attr_name.toString() + "&attr_value=" + attr_value.toString()+"&attr_id="+attr_id.toString(),
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
			// swal("系统异常");
		}
	})
}

function attr_delete(obj){
	var trobj = $(obj).closest('tr');
	$(trobj).remove();
}



function buid_mnt(action, curServiceName, depServiceName, tenantName) {
    if (action != "add" && action != "cancel") {
        swal("系统异常");
        window.location.href = window.location.href;
    }
    $.ajax({
        type : "POST",
        url : "/ajax/" + tenantName + "/" + curServiceName + "/mnt",
        data : "dep_service_alias=" + depServiceName + "&action=" + action,
        cache : false,
        beforeSend : function(xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success : function(msg) {
            var dataObj = msg
            if (dataObj["status"] == "success") {
                swal("操作成功")
                if (window.location.href.indexOf("fr=") < 0) {
                    window.location.href = window.location.href
                            + "?fr=relations";
                } else {
                    window.location.href = window.location.href
                }
            } else {
                swal("操作失败")
            }
        },
        error : function() {
            // swal("系统异常");
        }
    })
}

function service_image(service_id, service_alias, tenantName) {
    $.ajax({
        type : "POST",
        url : "/ajax/" + tenantName + "/" + service_alias + "/upgrade",
        data : "service_id=" + service_id + "&action=imageUpgrade",
        cache : false,
        beforeSend : function(xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success : function(msg) {
            var dataObj = msg;
            if (dataObj["status"] == "success") {
                swal("操作成功,重启后生效")
                window.location.href = window.location.href
            } else if (dataObj["status"] == "owed") {
                swal("余额不足请及时充值")
            } else if (dataObj["status"] == "often") {
                swal("操作正在进行中，请稍后")
            } else if (dataObj["status"] == "over_memory") {
                swal("资源已达上限，不能升级")
            } else if (dataObj["status"] == "over_money") {
                swal("余额不足，不能升级")
            } else {
                swal("设置失败")
            }
        },
        error : function() {
            swal("系统异常");
        }
    })
}
