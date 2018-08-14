/* 应用概览页面业务 */
(function(){



/* --------------  util start -------------- */

//生成日志条目dom字符串
function createLogTmp(data){
	var html = '';
	try{
		var arr = data.time.split('.')[0];
        var time1 = arr.split('T')[0];
        var time2 = arr.split('T')[1].split('Z')[0];
        var time3 = time2.split('+')[0];
        html = "<p class='clearfix'><span class='log_time'>" + time3 + "</span><span class='log_msg'> " + data.message + "</span></p>";
	}catch(e){
		console.log(e);
	}
	
	return html;
}

function isToday(str) {
    var d = new Date(str);
    var todaysDate = new Date();
    if (d.setHours(0, 0, 0, 0) == todaysDate.setHours(0, 0, 0, 0)) {
        return true;
    } else {
        return false;
    }
}

var type_json = {
    "deploy": "部署",
    "restart": "启动",
    "delete": "删除",
    "stop": "关闭",
    "HorizontalUpgrade": "水平升级",
    "VerticalUpgrade": "垂直升级",
    "callback": "回滚",
    "create": "创建",
    "own_money": "应用欠费关闭",
    "expired": "应用过期关闭",
    "share-ys": "分享到云市",
    "share-yb": "分享到云帮",
    "reboot"  :"应用重启" ,
    "git-change":"仓库地址修改",
    "imageUpgrade":"应用更新"
}

/* 创建时间轴列表模版 */
function createLogListTmp(logList){
	var status_json = {
        "success" : "成功",
        "failure" : "失败",
        "timeout" : "超时"
    }
    var final_status_json = {
        "complate" : "完成",
        "timeout" : "超时"
    }
    var bg_color = {
        "success" : "bg-success",
        "failure" : "bg-danger",
        "timeout" : "bg-danger"
    }
    if( jQuery.isEmptyObject(logList) )
    {
        return '<p style="text-align: center;font-size: 18px;">暂无日志<span class="span_src"><img src="/static/www/img/appOutline/log_src.png"></span></p>'
        
    }

    var html = [];
    for (var i = 0; i < logList.length; i++) {
        var log = logList[i];
        var arr = log["start_time"].split("T");
        var date = arr[0];
        var time = arr[1];
        var status;
        var color;
        if( log["final_status"] == "complete" )
        {
            status = status_json[log["status"]];
            color = bg_color[log["status"]];
        }
        else if( log["final_status"] == "timeout" ){
            status = final_status_json[log["final_status"]];
            color = 'bg-danger';
        }
        else{
            status = "进行中";
            color = 'bg-grey';
        }
        if( isToday(date) )
        {
            var str_log = '<li data-event-id="'+log["event_id"]+'" class="js-event-row"><time class="tl-time"><h4>'+time+'</h4></time>';
            $(".today_log").show();
        }
        else{
            var str_log = '<li data-event-id="'+log["event_id"]+'" class="js-event-row"><time class="tl-time"><h4>'+time+'</h4><p>'+date+'</p></time>';
        }
        if( log["status"] == "failure" )
        {
            str_log += '<i class="fa '+color+' tl-icon"></i><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>'+type_json[log["type"]]+status+'('+log["message"]+')'+' @'+log["user_name"]+'</span><div class="user"><p></p><p class="ajax_log_new" data-log="'+log["event_id"];
        }
        else{
            str_log += '<i class="fa '+color+' tl-icon"></i><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>'+type_json[log["type"]]+status+' @'+log["user_name"]+'</span><div class="user"><p></p><p class="ajax_log_new" data-log="'+log["event_id"];
        }
        str_log += '">查看详情</p><p class="hide_log">收起</p></div></div><div class="panel-body"><div class="log"><p class="log_type"><label class="active log-tab-btn" data-log="info">Info日志</label><label class="log-tab-btn" data-log="debug">Debug日志</label><label class="log-tab-btn" data-log="error">Error日志</label></p><div class="log_content log_'+log["event_id"]+'"></div></div></div></div></div></li>'
        if( log["type"] == "deploy" && log["old_deploy_version"] != "" )
        {
            var version = '当前版本('+log["old_deploy_version"]+')';
            if( log["old_code_version"] )
            {
                version = log["old_code_version"];
            }
            str_log += '<li><i class="fa tl-icon bg-version"></i><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>'+version+'</span>';
            str_log += '<div class="user"><button class="btn callback_version" data-version="'+log["old_deploy_version"]+'">回滚到此版本</button></div></div></div></div></li>'
        }
        html.push(str_log)
    }
    return html.join('');
}

/* --------------  util end --------------- */



/*  -------------- Ajax api start --------------- */

	/*
		创建应用的操作事件id
		@tenantName 租户名
		@action 操作事件名称 启动:restart, 关闭:stop, 重新部署:"", 服务更新:imageUpgrade
	*/
	function overViewGetEventId(tenantName, serviceAlias, action){
		var dfd = $.Deferred()
		getEventId(tenantName, serviceAlias, action)
		.done(function(data){
            var event = data["event"];
            var currentEventID = event["event_id"];
            var ok = true;

            var arr = event["event_start_time"].split("T");
            var date = arr[0];
            var time = arr[1].split('.')[0];


            var str_log = '<li class="js-event-row" data-event-id="'+event["event_id"]+'"><time class="tl-time"><h4>' + time + '</h4></time><i class="fa bg-grey tl-icon"></i><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>' + type_json[event["event_type"]] + '中@' + event["user_name"] + '</span><div class="user"><p>';
            str_log += '</p><p class="ajax_log_new" data-log="' + event["event_id"] + '" style="display: none;">查看详情</p><p class="hide_log" style="display: block;">收起</p></div></div><div class="panel-body"><div class="log"><p class="log_type" style="display: none;"><label class="active log-tab-btn" data-log="info">Info日志</label><label class="log-tab-btn" data-log="debug">Debug日志</label><label class="log-tab-btn" data-log="error">Error日志</label></p><div class="log_content log_height2 log_' + event["event_id"] + '"></div></div></div></div></div></li>'

            if (event["event_type"] == "deploy" && event["old_deploy_version"]) {
                var version = '当前版本(' + event["old_deploy_version"] + ')';
                if (event["old_code_version"]) {
                    version = event["old_code_version"];
                }
                str_log += '<li><i class="fa tl-icon bg-version"></i><div class="tl-content"><div class="panel panel-primary"><div class="panel-heading"><span>' + version + '</span>';
                str_log += '<div class="user"><button class="btn callback_version" data-version="' + event["old_deploy_version"] + '">回滚到此版本</button></div></div></div></div></li>'

            }
            $(".today_log").show();
            $(str_log).prependTo($("#keylog ul"));
      		dfd.resolve(currentEventID);
		}).fail(function(data){
			dfd.reject(data);
		})
		return dfd;
	}

	/*
		获取某个应用事件的log,
	*/
	function getEventlogByType(tenantName, serviceAlias, eventId, type) {
		return $.ajax({
	        type: "GET",
	        url: "/ajax/"+tenantName+"/"+serviceAlias+"/event/" + eventId + "/log?level="+type,
	        cache: false,
	        beforeSend: function (xhr, settings) {
	            var csrftoken = $.cookie('csrftoken');
	            xhr.setRequestHeader("X-CSRFToken", csrftoken);
	        }
	    })
	}

	/*
		确认付款
	*/
	function appPay(tenantName, serviceAlias) {
		return $.ajax({
            type: "post",
            url: "/ajax/" + tenantName + "/" + serviceAlias + "/pay-money",
            data: {},
            cache: false,
            beforeSend: function (xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function (msg) {
                if (msg["status"] == "success") {
                    swal("支付成功");
                    $(".layer-body-bg").css({"display": "none"});
                    window.location.href = window.location.href
                }
                else if (msg["status"] == "not_enough") {
                    swal("余额不足");
                }
                else {
                    swal(msg["info"] || "操作异常，请稍后再试");
                }
            },
            error: function () {
                swal("系统异常,请重试");
            }
        });
	}

	/*
		应用启动或关闭, 成功后调用socket显示日志
	*/
	function appOpenOrClose(serviceId, tenantName, serviceAlias, eventId, action){
		return $.ajax({
	        type: "POST",
	        url: "/ajax/" + tenantName + "/" + serviceAlias + "/manage",
	        data:{
	        	'service_id': serviceId,
	        	'action': action,
	        	'event_id': eventId
	        },
	        cache: false,
	        beforeSend: function (xhr, settings) {
	            var csrftoken = $.cookie('csrftoken');
	            xhr.setRequestHeader("X-CSRFToken", csrftoken);
	        },
	        success: function (msg) {
	            var dataObj = msg
	            if (dataObj["status"] == "success") {
	                swal.close();
	            } else if (dataObj["status"] == "often") {
	                swal("操作正在进行中，请稍后");
	                history.go(0);
	            } else if (dataObj["status"] == "owed") {
	                swal("余额不足请及时充值");
	                history.go(0);
	            } else if (dataObj["status"] == "expired") {
	                swal("试用已到期");
	                history.go(0);
	            } else if (dataObj["status"] == "over_memory") {
	                swal("免费资源已达上限，不能操作");
	                history.go(0);
	            } else if (dataObj["status"] == "over_money") {
	                swal("余额不足，不能操作");
	                history.go(0);
	            } else {
	                swal("操作失败");
	                history.go(0);
	            }
	        },
	        error: function () {
	            swal("系统异常");
	        }
	    })
	}


	/*
		获取下一页日志
	*/
	function getMoreLog(tenantName, serviceAlias, num) {
		return $.ajax({
            type: "GET",
            url: "/ajax/" + tenantName + "/" + serviceAlias + "/events?start_index=" + num,
            data: "",
            cache: false,
            beforeSend: function (xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        })
	}


	/*
		初始化页面操作日志列表
	*/
	function getInitLog(tenantName, serviceAlias) {
		return $.ajax({
            type: "GET",
            url: "/ajax/"+tenantName+"/"+serviceAlias+"/events",
            data: "action=operate",
            cache: false,
            beforeSend: function (xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        })
	}
/* -------------------- Ajax api end ------------------ */



/*  --------------- 业务逻辑控制器 start --------------- */
window.AppOverviewController = createPageController({
	property:{
		//判断某种操作正在执行中的标示 重新部署/启动/关闭/回滚版本, 默认必须为false
		isDoing: false,
		//应用类别
		category:'',
		//当前应用的id
		serviceId: '',
		//当前租户的name
		tenantName:'',
		//当前应用别名
		serviceAlias:'',
		//管理当前应用的地址
		manageUrl:'',
		//当前应用的状态
		status:'',
		//定时请求应用状态的时间间隔
		checkStatusInterval: 3000,
		//启动应用操作标示
		openAction:'restart',
		//关闭应用操作标示
		closeAction: 'stop',
		//服务更新操作标示　
		updateAction:'imageUpgrade',
		//重新部署操作标示
		deployAction:'deploy',
		//回滚版本操作标示
		rollbackAction:'callback',
		//重启应用标示
		rebootAction:'reboot',
		//webSocket 日志请求需要的url
		webSocketUrl:'',
		//未知　
		wild_domain:'',
		//未知
		http_port_str:''
	},
	method:{
		//初始化页面操作日志
		initLog: function(){
			var self =this;
			getInitLog(
				this.tenantName, 
				this.serviceAlias
			).done(function(msg){
				var dataObj = msg||{};
                var showlog = ""
                var logList = dataObj["log"]||[];
                var next_onOff = dataObj["has_next"];
                $('.load_more_new').attr("data-num", logList.length);
                if( next_onOff )
                {
                    $(".load_more_new").show();
                }
                if(logList){
                	var html = createLogListTmp(logList);
                	$(html).appendTo($("#keylog ul"));
                }

                var firstLog = logList[0];
                if(firstLog && firstLog["final_status"] == ""){
                	$("#keylog .log_type").eq(0).hide();
		            $("#keylog .hide_log").eq(0).html("查看详情");
		            //self.isDoing = true;
		            self.createLogSocket(firstLog["event_id"],firstLog["type"]);
                }
			})
		},
		//轮询监测应用状态
		checkStatus: function(){
			var self = this;
			getAppDetail(
				this.tenantName,
				this.serviceAlias
			)
			.done(function(msg){
				self.setStatus(msg);
				self.updatePayStatus(msg);
			})
			.always(function(){
				setTimeout(function(){
					self.checkStatus();
				}, self.checkStatusInterval)
			})
		},
		//设置应用的状态标示, 如果上次的状态跟这次的不一样才会执行dom更新操作， 优化性能
		setStatus: function(msg){
			msg = msg||{};
			if(this.status !== msg.status){
				this.onStatusChange(msg);
				this.status = msg.status;
			}
		},
		//当状态变化时的回调
		onStatusChange: function(msg){
			
			var obj=msg;
			if(obj["status"]!="failure"){
				if(obj["status"]=="running"){
					$('[action=visit]').show();
					$("#service_status_value").val("stop")
					$("#font"+this.serviceId).html("关闭");
					$("#service_status_close").show();
                    $("#service_status_open").hide();
					$("#service_status_operate").show().css({"backgroundColor":"#f63a47"});
					$("#onekey_deploy").show()
					$("#onekey_deploy").removeAttr("disabled")
					$("#service_status").html("运行中")
					$("#service_status-img").attr("src","/static/www/img/appOutline/appOutline0.png").addClass("roundloading");
					$("#service_visitor").show()
					$("#service_status").attr("class","text-center")
				}else if(obj["status"]=="starting"){
					$('[action=visit]').hide();
					$("#service_status_value").val("stop")
					$("#font"+this.serviceId).html("关闭")
					$("#service_status_close").show();
                    $("#service_status_open").hide();
					$("#service_status_operate").show().css({"backgroundColor":"#f63a47"});
					$("#onekey_deploy").show()
					$("#onekey_deploy").removeAttr("disabled")
					$("#service_status").html("启动中")
					$("#service_status-img").attr("src","/static/www/img/appOutline/appOutline7.png").addClass("roundloading");
					$("#service_status").attr("class","text-center")
					$("#service_visitor").hide()
					$("#multi_ports").hide()
				}else if(obj["status"]=="unusual"){
					$('[action=visit]').hide();
					$("#service_status_value").val("")
					$("#font"+this.serviceId).html("启动");
					$("#service_status_close").hide();
                    $("#service_status_open").show();
					$("#service_status_operate").show().css({"backgroundColor":"#28cb75"});
					$("#onekey_deploy").show();
					$("#service_status").html("运行异常")
					$("#service_status-img").attr("src","/static/www/img/appOutline/appOutline1.png").removeClass("roundloading");
					$("#service_visitor").hide();
					$("#multi_ports").hide()
					$("#service_status").attr("class","text-center")
				}else if(obj["status"]=="closed" || obj["status"]=="Owed" || obj["status"]=="expired"){
					$('[action=visit]').hide();
					$("#service_status_value").val("restart")
					$("#font"+this.serviceId).html("启动")
					$("#service_status_close").hide();
                    $("#service_status_open").show();
					$("#service_status_operate").show().css({"backgroundColor":"#28cb75"});
					$("#onekey_deploy").show();
					$("#onekey_deploy").removeAttr("disabled")
					$("#multi_ports").hide()
					if(obj["status"]=="closed"){
						$("#service_status").html("已关闭")
						$("#service_status-img").attr("src","/static/www/img/appOutline/appOutline1.png").removeClass("roundloading");
						$("#service_status").attr("class","text-center")
						$("#multi_ports").hide()
					}else{
						$("#service_status").html("余额不足已关闭")
						$("#service_status-img").attr("src","/static/www/img/appOutline/appOutline1.png").removeClass("roundloading");
						$("#service_status").attr("class","text-center")
						$("#multi_ports").hide()
					}
					$("#service_visitor").hide();
					$("#multi_ports").hide();
				}else if(obj["status"]=="undeploy"){
					$('[action=visit]').hide();
					$("#service_status_value").val("")
					$("#font"+this.serviceId).html("未部署");
					$("#service_status_operate").hide();
					$("#service_status_close").hide();
                    $("#service_status_open").hide();
					$("#onekey_deploy").show();
					$("#onekey_deploy").removeAttr("disabled")
					$("#service_status").html("未部署")
					$("#service_status-img").attr("src","/static/www/img/appOutline/appOutline1.png").removeClass("roundloading");
					$("#service_visitor").hide();
					$("#service_status").attr("class","text-center")
					$("#multi_ports").hide()
				} else if(obj["status"]=="checking") {
					$("#service_status").html("检测中");
					$('#onekey_deploy').hide();
					$('[action=visit]').hide();
					$('#service_status_close').show().removeAttr('disabled');
					$('#service_status_open').hide();
					$("#service_status-img").attr("src","/static/www/img/appOutline/appOutline4.png").removeClass("roundloading");

				}else if(obj["status"]=="stoping" || obj["status"]=="stopping") {
					$('[action=visit]').hide();
					$("#service_status_close").hide();
                    $("#service_status_open").hide();
					$("#service_status_operate").hide();
					$("#onekey_deploy").hide();
					$("#service_status").html("关闭中")
					$("#service_status-img").attr("src","/static/www/img/appOutline/appOutline0.png").removeClass("roundloading");
				}
				else{
					$('[action=visit]').hide();
					$("#service_status_value").val("")
					$("#font"+this.serviceId).html("未知");
					$("#service_status_close").hide();
                    $("#service_status_open").hide();
					$("#service_status_operate").hide()
					$("#onekey_deploy").hide();
					$("#service_status").html("未知")
					$("#service_status-img").attr("src","/static/www/img/appOutline/appOutline1.png").removeClass("roundloading");
					$("#service_visitor").hide();
					$("#service_status").attr("class","text-center")
					$("#multi_ports").hide()
				}
			}

		},
		//启动应用
		openApp: function(){
			var self = this;
			this.isDoing = true;
			overViewGetEventId(
				this.tenantName,
				this.serviceAlias,
				this.openAction
			).done(function(eventId){
				appOpenOrClose(
					self.serviceId,
					self.tenantName,
					self.serviceAlias,
					eventId,
					self.openAction
				).done(function(data){
					if(data.status === 'success'){
						self.createLogSocket(eventId, self.openAction);
					}else{
						self.isDoing = false;
					}
				}).fail(function(){
					self.isDoing = false;
				})

			}).fail(function(data){
				self.isDoing = false;
			})
		},
		//停止应用
		closeApp: function(){

			var self = this;
			this.isDoing = true;
			overViewGetEventId(
				this.tenantName,
				this.serviceAlias,
				this.closeAction
			).done(function(eventId){
				appOpenOrClose(
					self.serviceId,
					self.tenantName,
					self.serviceAlias,
					eventId,
					self.closeAction
				).done(function(data){
					if(data.status === 'success'){
						self.createLogSocket(eventId, self.closeAction);
					}else{
						self.isDoing = false;
					}
				}).fail(function(){
					self.isDoing = false;
				})
				
			}).fail(function(data){
				self.isDoing = false;
			})
		},
		//从新部署
		deployApp: function(){
			var self = this;
			this.isDoing = true;
			overViewGetEventId(
				this.tenantName,
				this.serviceAlias,
				this.deployAction
			).done(function(eventId){
				deployApp(
					self.category,
					self.tenantName,
					self.serviceAlias,
					eventId
				).done(function(data){
					if(data.status === 'success'){
						self.createLogSocket(eventId, self.deployAction);
					}else{
						self.isDoing = false;
					}
				}).fail(function(){
					self.isDoing = false;
				})
				
			}).fail(function(data){
				self.isDoing = false;
			})
		},
		//回滚版本
		rollbackApp: function(version){
			var self = this;
			this.isDoing = true;
			overViewGetEventId(
				this.tenantName,
				this.serviceAlias,
				this.rollbackAction
			).done(function(eventId){
				rollbackApp(
					self.tenantName,
					self.serviceAlias,
					eventId,
					version
				).done(function(data){
					self.createLogSocket(eventId, self.rollbackAction);
				}).fail(function(){
					self.isDoing = false;
				})
				
			}).fail(function(data){
				self.isDoing = false;
			})
		},
		//更新应用
		updateApp: function(){
			var self = this;
			swal({
		        title: "更新应用会对应用进行重新部署，期间应用可能会暂时无法提供服务，确定要更新吗？",
		        type: "warning",
		        showCancelButton: true,
		        confirmButtonColor: "#DD6B55",
		        confirmButtonText: "更新",
		        cancelButtonText: "取消",
		        closeOnConfirm: false,
		        closeOnCancel: false
		    }, function (isConfirm) {
		        if (isConfirm) {
		        	self.isDoing = true;
		        	overViewGetEventId(
						self.tenantName,
						self.serviceAlias,
						self.updateAction
					).done(function(eventId){
						updateApp(
			        		self.serviceId,
			        		self.tenantName,
			        		self.serviceAlias,
			        		eventId
			        	).done(function(data){
			        		$("#service_image_operate").hide();
			        		//重启应用
			        		self.rebootApp(eventId);
			        	}).fail(function(){
			        		self.isDoing = false;
			        	})
					}).fail(function(){
						self.isDoing = false;
						swal("创建更新操作错误，请重试");
					})
		        }
		    });
		},
		//重启动应用
		rebootApp: function(eventId) {
			var self = this;
			rebootApp(
				self.serviceId,
				self.tenantName,
				self.serviceAlias,
				eventId
			).done(function(){
				self.createLogSocket(eventId, self.rebootAction);
			}).fail(function(){
				self.isDoing = false;
			})
		},
		//根据　eventId 和 action 创建socket连接并生成消息
		createLogSocket: function(eventId, action) {
			var self = this;
			$("#keylog .panel-heading").eq(0).css({ "padding-bottom": "5px" });
			$("#keylog .log").eq(0).css({ "height": "20px" });
			$("#keylog .ajax_log_new").eq(0).hide();
			$("#keylog .hide_log").eq(0).show();
			$("#keylog .log_type").eq(0).hide();
			return new LogSocket({
				url: this.webSocketUrl,
				eventId: eventId,
				onMessage: function(data){
					var msgHtml = createLogTmp(data);
					$(msgHtml).prependTo($("#keylog .log_content").eq(0));
				},
				onClose: function() {
					self.isDoing = false;
					//$("#keylog li").eq(0).find('.panel-heading').css({ "padding-bottom": "0px" });
					$("#keylog li").eq(0).find('.log').removeClass('log_height').css({ "height": "0px" });
				},
				onSuccess: function(data) {
					var str = type_json[action] + "成功";
    				$("#keylog li").eq(0).find(".fa").removeClass("bg-grey").addClass("bg-success");
    				$("#keylog .panel").eq(0).find(".panel-heading span").html(str);
				},
				onFail: function(data) {
					$("#keylog li").eq(0).find(".fa").removeClass("bg-grey").addClass("bg-danger");
    				var str = type_json[action] + "失败(" + data.message + ")";
    				$("#keylog .panel").eq(0).find(".panel-heading span").html(str);
				},
				onComplete: function(data){
					$("#keylog li").eq(0).find('.ajax_log_new').show();
            		$("#keylog li").eq(0).find('.log_type').show();
            		$("#keylog li").eq(0).find('.hide_log').hide();
					$("#keylog li").eq(0).find('.log_content').removeClass('log_height2');
				}
			})
		},
		//访问应用在线地址
		visitApp: function(port){
			var port = port ? (port+'.') : '';
			var url = "http://" + port +this.serviceAlias+"."+this.tenantName+this.wild_domain+this.http_port_str;
	        window.open(url)
		},
		//管理应用
		manageApp: function() {
			if(this.manageUrl){
				window.open(this.manageUrl);
			}
		},
		//更新上一小时费用
		updatePayStatus: function(msg){
			var pay_status = msg["service_pay_status"];
	        var tips = msg["tips"];
	        if (pay_status == "no_money") {
	            $("#last_hour_fee").html("欠费 关闭")
	            $(".layer_pay").attr("data-tips", tips);
	        } else if (pay_status == "debugging") {
	            $("#last_hour_fee").html("调试中");
	            $(".layer_pay").attr("data-tips", tips);
	        } else if (pay_status == "unknown") {
	            $("#last_hour_fee").html("0元");
	            $(".layer_pay").attr("data-tips", tips);
	        } else if (pay_status == "wait_for_pay") {
	            $("#last_hour_fee").html("等待支付");
	            $(".layer_pay").attr("data-tips", tips);
	            $("#can_pay_btn").val("True");
	            $("#need_to_pay").html(msg["need_pay_money"]);
	            $("#start_time").html(msg["start_time_str"]);
	            $("#need_to_pay").css("color", "#28cb75");
	            $("#start_time").css("color", "#28cb75");

	        } else if (pay_status == "soon") {
	            $("#last_hour_fee").html("即将计费");
	            $(".layer_pay").attr("data-tips", tips);
	        } else if (pay_status == "show_money") {
	            $("#last_hour_fee").html(msg["cost_money"] + "元");
	            $(".layer_pay").attr("data-tips", tips);
	        } else {
	            $("#last_hour_fee").html("-");
	            $(".layer_pay").attr("data-tips", tips);
	        }
		},
		//显示某个事件的日志信息, type: info/debug/error
		getAndRenderEventLog: function(eventId, type) {
			getEventlogByType(this.tenantName, this.serviceAlias, eventId, type||'info')
			.done(function(data){
				$(".log_" + eventId + "").html('');
	            var dataObj = data;
	            var html=[];
	            var newLog = dataObj["data"];
	            for (i = 0; i < newLog.length; i++) {
	                var time = newLog[i]["time"].split('.')[0];
	                var time1 = time.split('T')[0];
	                var time2 = time.split('T')[1].split('Z')[0];
	                var time3 = time2.split('+')[0];
	                var log = "<p class='clearfix'><span class='log_time'>"+time3+"</span><span class='log_msg'> "+newLog[i]["message"]+"</span></p>";
	                html.unshift(log);
	           
	            }
	            $(".log_" + eventId + "").prepend(html.join(''));
			})
		},
		//获取下页时光轴
		getMoreLog: function(num) {
			var self = this;
			getMoreLog(
				this.tenantName, 
				this.serviceAlias, 
				num
			).done(function(msg){
				var dataObj = msg || {};
                var showlog = "";
                var logList = dataObj["log"] || [];
                var next_onOff = dataObj["has_next"];
                $('.load_more_new').attr("data-num", parseInt(num) + logList.length);
                if (next_onOff) {
                    $(".load_more_new").show();
                }else{
                	$(".load_more_new").hide();
                }

                if(logList && logList.length){
                	var html = createLogListTmp(logList);
                	$(html).appendTo($("#keylog ul"));
                }
			})
		},
		//获取应用的容器信息
		renderContainer: function() {
			getAppContainer(
				this.tenantName,
				this.serviceAlias
			).done(function(dataObj) {
				var msg = "";
	            var tindex = 1;
	            for (var key in dataObj) {
	                if (key != "split") {
	                    msg += "<li>";
	                    msg += "<a class='app-container-node' data-cid='"+key+"' data-hip='"+dataObj[key]+"' href='javascript:void(0);'> 节点" + tindex + "</a></li>"
	                    tindex += 1;
	                }
	            }
	            if (msg != "") {
	                $("#cur_container_content").html(msg)
	            }
			})
		},
		//查看容器节点
		visitContainerNode: function(c_id, h_ip){
			var self = this;
			createAppContainerSocket(
				this.tenantName,
				this.serviceAlias,
				c_id,
				h_ip
			).done(function(){
				window.location.href = "/apps/"+self.tenantName+"/"+self.serviceAlias+"/docker/"
			})
		}
		
	},
	domEvents:{
		//点击容器节点事件
		'.app-container-node click': function(e){
			var $target = $(e.target);
			var c_id = $target.data('cid');
			var h_ip = $target.data('hip');
			if(c_id && h_ip){
				this.visitContainerNode(c_id, h_ip);
			}
		},
		//点击管理容器，请求容器数据事件
		'#join_container click': function(e) {
			this.renderContainer();
		},
		//更新应用事件
		'#service_image_operate click': function(e) {
			if(this.isDoing) return;
			this.updateApp();
		},
		//管理应用事件　
		'.manageApp click': function(e) {
			this.manageApp();
		},
		//访问
		'.visit-btn click': function(e) {
			var port = $(e.target).data('port')||'';
			this.visitApp(port);
		},
		//访问应用地址事件
		'#service_visitor click': function(e) {
			this.visitApp();
		},
		//重新部署事件
		'#onekey_deploy click': function(e){
			if(this.isDoing){
				return;
			}
			this.deployApp();
		},
		//关闭应用事件
		'#service_status_close click': function(e) {
			if(this.isDoing){
				return;
			}
			this.closeApp();
		},
		//启动应用事件
		'#service_status_open click': function(e) {
			if(this.isDoing){
				return;
			}
			this.openApp();
		},
		//版本回滚事件
		'.callback_version click': function(e) {
			var self = this;
			if(this.isDoing){
				return;
			}
			var $target = $(e.target);
			var version = $target.data('version');
			if(version){
				swal({
		            title: "确定恢复当前版本吗？",
		            type: "warning",
		            showCancelButton: true,
		            confirmButtonColor: "#DD6B55",
		            confirmButtonText: "确定",
		            cancelButtonText: "取消",
		            closeOnConfirm: false,
		            closeOnCancel: false
		        }, function (isConfirm) {
		            if (isConfirm) {
		                self.rollbackApp(version);
		            } else {
		                swal.close();
		            }
		        });
			}
		},
		//查看详情
		'.ajax_log_new click': function(e) {
			var $target = $(e.target);
			var event_id = $target.attr("data-log");
	        $target.parents('li').find('.log_type label').removeClass('active');
	        $target.parents('li').find('.log_type label').eq(0).addClass('active');
	        if ($target.parents('li').find('.log_type').css("display") != "none") {
	            $(".log_" + event_id).html('');
	            this.getAndRenderEventLog(event_id, 'info');
	        }
	        $target.hide();
	        $target.parent().find('.hide_log').show();
	        $target.parents('li').find('.log').addClass('log_height');
	        $target.parents('li').find('.log_content').addClass('log_height2');
		},
		//收起日志
		'.hide_log click': function(e) {
			var $target = $(e.target);
			var onOff = $target.parents('.panel').find('.log').hasClass('log_height');
	        if (onOff) {
	            $target.parents('li').find('.log').removeClass('log_height');
	            $target.parents('li').find('.ajax_log_new').show();
	            $target.hide();
	            //$target.parents('.panel').find('.panel-heading').css({ "padding-bottom": "0px" });
	            $target.parents('.panel').find('.log').css({ "height": "0px" });
	        }
	        else {
	            $target.parents('li').find('.log').addClass('log_height');
	            $target.parents('li').find('.ajax_log_new').hide();
	            $target.show();
	        }
		},
		//切换日志事件
		'.log-tab-btn click': function(e) {
			var $target = $(e.target);
			if($target.hasClass('active')) return;
			var $btns = $target.parent().find('.log-tab-btn');
			var eventId = $target.parents('.js-event-row').data('event-id');
			var type = $target.data('log');
			if(eventId && type){
				$btns.removeClass('active');
				$target.addClass('active');
				this.getAndRenderEventLog(eventId, type);
			}
		},
		//显示付款提示框事件
		'.layer_pay click': function(e) {
			var can_pay = $("#can_pay_btn").val()
	        if (can_pay == "True") {
	            $(".layer-body-bg").css({"display": "block"});
	        }
		},
		//付款取消事件
		'button.cancel click': function(e) {
			$(".layer-body-bg").css({"display": "none"});
		},
		//付款弹框关闭事件
		'.del click': function(e) {
			$(".layer-body-bg").css({"display": "none"});
		},
		//确认付款
		'.sure_pay click': function(e) {
			var self = this;
	        appPay(
	        	self.tenantName, 
	        	self.serviceAlias
	        )
	    
		},
		//费用鼠标提示信息，需重构
		'.fn-tips mouseenter': function(e){
			var $target = $(e.currentTarget);
			var tips = $target.attr("data-tips");
            var pos = $target.attr("data-position");
            var x = $target.offset().left;
            var y = $target.offset().top;
            var oDiv = '<div class="tips-box"><p><span>' + tips + '</span><cite></cite></p></div>';
            $("body").append(oDiv);
            var oDivheight = $(".tips-box").height();
            var oDivwidth = $(".tips-box").width();
            var othiswid = $target.width();
            var othisheight = $target.height();
            if (pos) {
                if (pos == "top") {
                    //
                    $(".tips-box").css({"top": y - oDivheight - 25});
                    if (oDivwidth > othiswid) {
                        $(".tips-box").css({"left": x - (oDivwidth - othiswid) / 2});
                    } else if (oDivwidth < othiswid) {
                        $(".tips-box").css({"left": x + (othiswid - oDivwidth) / 2});
                    } else {
                        $(".tips-box").css({"left": x});
                    }
                    $(".tips-box").find("cite").addClass("top");
                    //
                } else if (pos == "bottom") {
                    //
                    $(".tips-box").css({"top": y + othisheight + 25});
                    if (oDivwidth > othiswid) {
                        $(".tips-box").css({"left": x - (oDivwidth - othiswid) / 2});
                    } else if (oDivwidth < othiswid) {
                        $(".tips-box").css({"left": x + (othiswid - oDivwidth) / 2});
                    } else {
                        $(".tips-box").css({"left": x});
                    }
                    $(".tips-box").find("cite").addClass("bottom");
                    //
                } else if (pos == "left") {
                    $(".tips-box").css({"top": y + 5, "left": x - othiswid - 5});
                    $(".tips-box").find("cite").addClass("left");
                } else if (pos == "right") {
                    $(".tips-box").css({"top": y + 5, "left": x + othiswid + 5});
                    $(".tips-box").find("cite").addClass("right");
                } else {
                    //
                    $(".tips-box").css({"top": y - oDivheight - 25});
                    if (oDivwidth > othiswid) {
                        $(".tips-box").css({"left": x - (oDivwidth - othiswid) / 2});
                    } else if (oDivwidth < othiswid) {
                        $(".tips-box").css({"left": x + (othiswid - oDivwidth) / 2});
                    } else {
                        $(".tips-box").css({"left": x});
                    }
                    $(".tips-box").find("cite").addClass("top");
                    //
                }
            } else {
                //
                $(".tips-box").css({"top": y - oDivheight - 25});
                if (oDivwidth > othiswid) {
                    $(".tips-box").css({"left": x - (oDivwidth - othiswid) / 2});
                } else if (oDivwidth < othiswid) {
                    $(".tips-box").css({"left": x + (othiswid - oDivwidth) / 2});
                } else {
                    $(".tips-box").css({"left": x});
                }
                $(".tips-box").find("cite").addClass("top");
            }
		},
		//费用鼠标提示信息，需重构
		'.fn-tips mouseleave': function(e){
			$(".tips-box").remove();
		},
		//下一页日志
		'.load_more_new click': function(e) {
			var $target = $(e.currentTarget);
			var num = $target.attr('data-num');
			if(num){
				this.getMoreLog(num);
			}
		}
	},
	onReady:function(){
		this.initLog();
		this.checkStatus();

		//需要重构
		var port_length = $("#port_length").val();
		if(port_length != "1"){
			$("#multi_ports").show();
		}

		//需要重构
		var li_length = $("#status_areas li").length;
        if (li_length == 4) {
            $("#status_areas li").width("25%");
        }
	}
})
/*  --------------- 业务逻辑控制器 end --------------- */
})()