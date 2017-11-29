/* 应用概览页面业务 */

import React, {Component} from 'react';
import {connect} from 'react-redux';
import {} from 'antd';
import LogSocket from '../utils/LogSocket';
import util from '../utils/util';
import {
	getEventId

} from '../comms/apiCenter';

import {
	openApp,
	closeApp,
	getAppDetail,
	deployApp,
	rollbackAppByEventId,
	updateAppByEventId,
	openAppByEventId,
	closeAppByEventId,
	deployAppByEventId,
	rebootAppByEventId,
	getEventlogByType,
	getAppContainer,
	createAppContainerSocket,
	appPay
} from '../comms/app-apiCenter';





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
        return '<p style="text-align: center;font-size: 18px;">平台升级历史日志暂时无法提供<span class="span_src"><img src="/static/www/img/appOutline/log_src.png"></span></p>'
        
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



class AppDeploy extends Component {
	constructor(props){
		super(props);
		this.state = {
			pageInfo: {}
		}
	}
	componentWillMount(){
		
	}
	//初始化页面操作日志
	initLog(){
		var self =this;
		getInitLog(
			this.tenantName, 
			this.serviceAlias
		).done(function(msg){
			var dataObj = msg||{};
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
            //某种操作事件进行中, 则创建socket， 渲染事件日志
            if(firstLog && firstLog["final_status"] == ""){
            	$("#keylog .log_type").eq(0).hide();
	            $("#keylog .hide_log").eq(0).html("查看详情");
	            self.createLogSocket(firstLog["event_id"],firstLog["type"]);
            }
		})
	}
	//轮询监测应用状态
	checkStatus(){
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
	}
	//设置应用的状态标示, 如果上次的状态跟这次的不一样才会执行dom更新操作， 优化性能
	setStatus(msg){
		msg = msg||{};
		if(this.status !== msg.status){
			this.onStatusChange(msg);
			this.status = msg.status;
		}
	}
	//当状态变化时的回调
	onStatusChange(msg){
		
		var obj=msg;
		if(obj["status"]!="failure"){
			var statusMap = util.getStatusMap(obj["status"]);
			//隐藏该状态下不能操作的按钮
			var disabledAction = statusMap.disabledAction;
			$.each(disabledAction, function(index, action){
				$('[action='+action+']').hide();
			})
			//显示该状态下可以操作的按钮
			var activeAction = statusMap.activeAction;
			$.each(activeAction, function(index, action){
				$('[action='+action+']').show();
			})
			//更新状态描述
			var statusCN = statusMap.statusCN;
			$("#service_status").html(statusCN);
			//更新状态图标
			var iconUrl = statusMap.iconUrl;
			$("#service_status-img").attr("src",iconUrl);
			if(obj["status"] === 'running'){
				$("#service_status-img").addClass('roundloading')
			}else{
				$("#service_status-img").removeClass('roundloading')
			}
		}
	}
	//启动应用
	openApp(){
		var self = this;
		this.isDoing = true;
		overViewGetEventId(
			this.tenantName,
			this.serviceAlias,
			this.openAction
		).done(function(eventId){
			openAppByEventId(
				self.serviceId,
				self.tenantName,
				self.serviceAlias,
				eventId,
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
	}
	//停止应用
	closeApp(){
		var self = this;
		this.isDoing = true;
		overViewGetEventId(
			this.tenantName,
			this.serviceAlias,
			this.closeAction
		).done(function(eventId){
			closeAppByEventId(
				self.serviceId,
				self.tenantName,
				self.serviceAlias,
				eventId,
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
	}
	//从新部署
	deployApp(){
		var self = this;
		this.isDoing = true;
		overViewGetEventId(
			this.tenantName,
			this.serviceAlias,
			this.deployAction
		).done(function(eventId){
			deployAppByEventId(
				self.category,
				self.tenantName,
				self.serviceAlias,
				eventId,
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
	}
	//回滚版本
	rollbackApp(version){
		var self = this;
		this.isDoing = true;
		overViewGetEventId(
			this.tenantName,
			this.serviceAlias,
			this.rollbackAction
		).done(function(eventId){
			rollbackAppByEventId(
				self.tenantName,
				self.serviceAlias,
				version,
				eventId
			).done(function(data){
				self.createLogSocket(eventId, self.rollbackAction);
			}).fail(function(){
				self.isDoing = false;
			})
		}).fail(function(data){
			self.isDoing = false;
		})
	}
	//更新应用
	updateApp(){
		var self = this;
		var confirm = widget.create('confirm', {
			title: '更新应用',
			height: '250px',
			content:"更新应用会对应用进行重新部署，期间应用可能会暂时无法提供服务，确定要更新吗？",
			event:{
				onOk: function() {
					self.isDoing = true;
		        	overViewGetEventId(
						self.tenantName,
						self.serviceAlias,
						self.updateAction,
					).done(function(eventId){
						updateAppByEventId(
			        		self.serviceId,
			        		self.tenantName,
			        		self.serviceAlias,
			        		eventId
			        	).done(function(data){
			        		$("#service_image_operate").hide();
			        		//重启应用
			        		self.rebootApp(eventId);
			        		confirm.destroy();
			        	}).fail(function(){
			        		self.isDoing = false;
			        	})
					}).fail(function(){
						self.isDoing = false;
						Msg.danger("创建更新操作错误，请重试");
					})
				}
			}
		})
	}
	//重启动应用
	rebootApp(eventId) {
		var self = this;
		rebootAppByEventId(
			self.serviceId,
			self.tenantName,
			self.serviceAlias,
			eventId
		).done(function(){
			self.createLogSocket(eventId, self.rebootAction);
		}).fail(function(){
			self.isDoing = false;
		})
	}
	//根据　eventId 和 action 创建socket连接并生成消息
	createLogSocket(eventId, action) {
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
	}
	//访问应用在线地址
	visitApp(port){
		var port = port ? (port + '.') : '';
		var url = "http://" + port +this.serviceAlias+"."+this.tenantName+this.wild_domain+this.http_port_str;
        window.open(url)
	}
	//管理应用
	manageApp() {
		if(this.manageUrl){
			window.open(this.manageUrl);
		}
	}
	//显示某个事件的日志信息, type: info/debug/error
	getAndRenderEventLog(eventId, type) {
		getEventlogByType(this.tenantName, this.serviceAlias, eventId, type||'info')
		.done(function(data){
			$(".log_" + eventId + "").html('');
            var dataObj = data;
            var html=[];
            var newLog = dataObj["data"];
            for (var i = 0; i < newLog.length; i++) {
                var time = newLog[i]["time"].split('.')[0];
                var time1 = time.split('T')[0];
                var time2 = time.split('T')[1].split('Z')[0];
                var time3 = time2.split('+')[0];
                var log = "<p class='clearfix'><span class='log_time'>"+time3+"</span><span class='log_msg'> "+newLog[i]["message"]+"</span></p>";
                html.unshift(log);
           
            }
            $(".log_" + eventId + "").prepend(html.join(''));
		})
	}
	getMoreLog(num) {
		var self = this;
		getMoreLog(
			this.tenantName, 
			this.serviceAlias, 
			num
		).done(function(msg){
			var dataObj = msg || {};
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
	}
	//获取应用的容器信息
	renderContainer() {
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
	}
	//查看容器节点
	visitContainerNode(c_id, h_ip){
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
	showPayConfirm() {
			var self = this;
			var confirm = widget.create('confirm', {
				title: '付费确认',
				content: $('#payDialogTmp').html(),
				height:'auto',
				event: {
					onOk: function(){
						appPay(
							self.tenantName,
							self.serviceAlias
						).done(function(data){
							confirm.destroy();
							self.needPay = 0;
							self.payStartTime = '';
						})
					}
				}
			})
			var $ele = confirm.getElement();
			$ele.find('#need_to_pay').html(this.needPay);
			$ele.find('#start_time').html(this.payStartTime);
		
		
	}
	render(){
		const appInfo  = this.props.appInfo || {};
		return (
		   <div>
		   		<div className="flex-box" id="status_areas">
		        <div className="flex-singe chunkbox">
		            <div className="app-overview-status-info">
		                <table>
		                    <tr>
		                        <td>状态</td>
		                        <td id="service_status"></td>
		                    </tr>
		                    <tr>
		                        <td>内存使用</td>
		                        <td id="service_memory"></td>
		                    </tr>
		                    <tr>
		                        <td>磁盘使用</td>
		                        <td id="service_disk"></td>
		                    </tr>
		                    <tr>
		                        <td>上一小时流量</td>
		                        <td id="service_net"></td>
		                    </tr>
		                </table>
		            </div>
		        </div>

		        {
		        	appInfo ? 
		        	<div className="flex-singe chunkbox">
			            <div className="app-overview-money-info">
			                <table>
			                    <tr>
			                        <td>上一小时内存费用</td>
			                        <td id="service_memory_money">-</td>
			                    </tr>
			                    <tr>
			                        <td>上一小时磁盘费用</td>
			                        <td id="service_disk_money">-</td>
			                    </tr>
			                    <tr>
			                        <td>上一小时流量费用</td>
			                        <td id="service_net_money">-</td>
			                    </tr>
			                    <tr>
			                        <td>总共累积消费</td>
			                        <td id="service_total_money">-</td>
			                    </tr>
			                </table>
			            </div>
			        </div>
			        :
			        ''
		        }
		        
		    </div>
		    <section className="clearfix">
		        <!-- 02 left -->
				<div className="pull-left">
					<ul className="clearfix handle-box-left">
						<input type="hidden" id="port_length" value="{{http_outer_service_ports|length}}">
		                <!--  left-001  -->
						{% if hasHttpServices %}
						<li>
							<div class="btn-group" action="visit">
		    				    {% if visit_port_type == "multi_outer" %}
		    						{% if http_outer_service_ports|length == 1 %}
		    							{% for port in http_outer_service_ports %}
		    							<button class="btn btn-success" data-port="{{ port.container_port }}" type="button" data-toggle="dropdown" id="service_visitor">访问</button>
		    							{% endfor %}
		    						{% else %}
		    						<button type="button" class="btn btn-success" data-toggle="dropdown">访问<span class="caret"></span></button>
		    						<ul class="dropdown-menu" role="menu">
		    							{% for port in http_outer_service_ports %}
		    								<li><a class="visit-btn" data-port="{{ port.container_port }}" href="javascript:void(0)">{{ port.container_port }}端口</a></li>
		    							{% endfor %}
		    						{% endif %}
		    					{% else %}
		    					<button type="button" class="btn btn-success dropdown-toggle" data-toggle="dropdown" id="service_visitor">访问</button>
							{% endif %}
						    </div>
						</li>
								<!--{% if visit_port_type == "multi_outer" %}-->
									<!--{% if http_outer_service_ports|length == 1 %}-->
										<!--<li class="button">-->
										<!--<select class="form-control-inline" id="multi_ports" data="ttt" name="multi_port_bind"  style="width:100px; height: 30px; line-height: 30px; font-size: 20px; display: none ;">-->
									<!--{% else %}-->
										<!--<select class="form-control-inline" id="multi_ports" name="multi_port_bind"  style="width:100px; height: 30px; line-height: 30px; font-size: 20px;">-->
									<!--{% endif %}-->
									<!--{% for port in http_outer_service_ports %}-->
										<!--{% if port.container_port == serviceDomain.container_port %}-->
										<!--<option value="{{ port.container_port }}"-->
											<!--selected="selected">{{ port.container_port }}</option>-->
										<!--{% else %}-->
										<!--<option value="{{ port.container_port }}">{{ port.container_port }}</option>-->
										<!--{% endif %}-->
									<!--{% endfor %}-->

		                            <!--</select>-->
		                            <!--{%endif%}-->

		                {% endif %}
		                <!--  left-001  -->
		                <!--  left-002  -->
		                <li>
		                    {% ifequal tenantServiceInfo.service_type "mysql" %}
		                        {% if service_manager.deployed %}
		                            {% if 'manage_service' in user.actions %}
		                                <button type="button" class="btn btn-success manageApp" id="service_visitor">管理
		                                </button>
		                            {% endif %}
		                        {% else %}
		                            {% if 'manage_service' in user.actions %}
		                                <button type="button" class="btn btn-success manageApp" id="service_visitor">添加管理服务
		                                </button>
		                            {% endif %}
		                        {% endif %}
		                    {% endifequal %}
		                    {% if updateService %}
		                        <button type="button" class="btn btn-success" id="service_image_operate">
		                            服务更新
		                        </button>
		                    {% endif %}
		                </li>
		                <!--  left-002  -->
		                    {% if not community and tenantServiceInfo.category = "application" %}
		                        <!--<li class="button">-->
		                            <!--<a href="/apps/{{ tenantName }}/{{ serviceAlias }}/share/step1?fr=share" class="bgColor"-->
		                               <!--target="_blank">分享</a>-->
		                        <!--</li>-->
		                    {% endif %}
		            </ul>
		        </div>
		        <!-- 02 left -->
		        <!-- 02 right -->
		        <div class="pull-right">
		            <ul class="clearfix handle-box-right">
		                <!-- right-001 -->
		                {% ifequal tenantServiceInfo.category "application" %}
		                    {% if user.is_sys_admin %}
		                            <!--
		                            <li class="button" style="display:none;">
		                                    <button type="button" class="bgColor" id="service_publish" onclick="window.open('/apps/{{tenantName}}/{{serviceAlias}}/publish');">发布</button>
		                            </li>
		                            -->
		                    {% endif %}
		                {% endifequal %}
		                <!-- right-001 -->
		                <!-- right-002 -->
		                {% if user.is_sys_admin or docker_console or tenantName == 'gooood' or tenantName == 'gooood0' or tenantName == 'baoxianjie' or tenantName == 'showmac' or tenantName == 'jamesocy' %}
		                <li action="manage_container">
		                    <div class="btn-group">
		                        <button type="button" name="join_container" class="btn btn-success dropdown-toggle" data-toggle="dropdown"  id="join_container" /> 管理容器 <span class="caret"></span></button>
		                        <ul class="dropdown-menu dropdown-menu-right" role="menu" id="cur_container_content">
		                                        <!--<li><a href="#">节点1</a></li>-->
		                        </ul>
		                    </div>
		                </li>
		                {% endif %}
		                <!-- right-002 -->
		                <!-- right-003 -->
		                {% if 'manage_service' in user.actions %}
		                <li class="button">
		                    <input type="hidden" id="service_status_value" name="service_status_value" value="" />
		                    <button action="stop" style="display:none;" type="button" class="btn btn-danger" id="service_status_close"><font id="font{{tenantServiceInfo.service_id}}">关闭</font></button>
		                    <button action="restart"style="display:none;" type="button" class="btn btn-success" id="service_status_open"><font id="font{{tenantServiceInfo.service_id}}">开启</font></button>
		                </li>
		                {% endif %}
		                <!-- right-003 -->
		                <!-- right-004 -->
		                {% ifequal tenantServiceInfo.category "application" %}
		                            <!--{% if user.is_sys_admin %}-->
		                            <!--<li class="button">-->
		                            <!--<button type="button" class="bgColor" id="service_publish" onclick="window.open('/apps/{{tenantName}}/{{serviceAlias}}/publish');"><i class="fa fa-eye"></i>发布</button>-->
		                            <!--</li>-->
		                            <!--{% endif %}-->
		                    
		                    {% if 'code_deploy' in user.actions %}
		                    <li class="button">
		                        <button action="deploy" type="button" class="btn btn-success" id="onekey_deploy">重新部署</button>
		                    </li>
		                    {% endif %}
		                {% endifequal %}
		                <!-- right-004 -->
		            </ul>
		        </div>
		        <!-- 02 right -->
			</section>
			<section class="panel panel-default">
		        <div class="panel-heading">操作记录</div>
		        <div class="panel-body">
		            <input type="hidden" name="service_name" id="service_name" value="{{tenantServiceInfo.service_alias}}"/>
		            <div id="keylog">
		                <span class="today_log">今天</span>
		                <ul class="timeline list-unstyled">
		                </ul>
		                <p style="text-align: center;">
		                    <span data-num="0" class="load_more_new" style="display:none;">
		                        <img src="{% static "www/img/load_more_log.png" %}">
		                    </span>
		                </p>
		            </div>
		        </div>
			</section>
		   </div>
		)
	}
}

export default connect((state, props) => {
	return {
		appInfo : state.appInfo
	}
})(AppDeploy);