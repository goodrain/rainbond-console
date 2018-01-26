/* 应用概览页面业务 */
import createPageController from '../utils/page-controller';
import widget from '../ui/widget';
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
	appPay,
	getAppInfo,
	NewrebootApp,
	NewrebootByEventId,
	getNotInstalledPlugin,
	getAppRequestTime,
	getAppRequest
} from '../comms/app-apiCenter';
import {
	getPageOverviewAppData
} from '../comms/page-app-apiCenter';
const Msg = widget.Message;
var template = require('./app-overview-tpl.html');
import appActionLogUtil from '../utils/app-action-log-util';
import dateUtil from '../utils/date-util';



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

/*
	创建时间轴单条记录模板
*/
function createLogItemTmp(log, data){
	var html = [];
    	html.push('<li data-event-id="'+log.event_id+'" class="js-event-row">');
    	html.push('<time class="tl-time">');
	    	html.push('<h4>'+(dateUtil.format(appActionLogUtil.getActionTime(log), 'hh:mm:ss'))+'</h4>');
	    	html.push('<p>'+(dateUtil.dateToCN(appActionLogUtil.getActionTime(log), 'yyyy-MM-dd'))+'</p>');
    	html.push('</time>');
    	html.push('<i class="fa '+(appActionLogUtil.getActionStatusInfo(log).bgColor)+' tl-icon"></i>');
    	html.push('<div class="tl-content">');
    		html.push('<div class="panel panel-primary">');
    			html.push('<div class="panel-heading">');
    				var title = (appActionLogUtil.getActionCN(log)+appActionLogUtil.getActionStatusInfo(log).text);
    				if(appActionLogUtil.isFail(log)){
    					title += '('+log.message+')';
    				}
    				title += '@'+appActionLogUtil.getActionUser(log);
    				html.push('<span>'+title+'</span>');
    				html.push('<div class="user btns">');
    					if(appActionLogUtil.canRollback(log)){
    						html.push('<a href="javascript:;" class="callback_version" data-version="'+appActionLogUtil.getRollbackVersion(log)+'">回滚到此版本</a>');
    					}
    					html.push('<a href="javascript:;" class="ajax_log_new" data-log="'+log.event_id+'">查看详情</a>');
    					html.push('<a href="javascript:;" class="hide_log">收起</a>')
    				html.push('</div>')
    			html.push('</div>')
    			html.push('<div class="panel-body">');
    			if(appActionLogUtil.isDeploy(log) && log.code_version){
					html.push('<div class="version-info">');
						html.push('<span class="pull-left ws-nowrap" style="width:60%" title="'+(appActionLogUtil.getCommitLog(log) || '')+'">代码信息：'+appActionLogUtil.getCommitLog(log)+'</span>');
						html.push('<span class="pull-right">#'+appActionLogUtil.getCodeVersion(log)+' by '+appActionLogUtil.getCommitUser(log)+'</span>');
					html.push('</div>');
				}
					html.push('<div class="log">')
						html.push('<p class="log_type">');
							html.push('<label class="active log-tab-btn" data-log="info">Info日志</label>');
							html.push('<label class="log-tab-btn" data-log="debug">Debug日志</label>');
							html.push('<label class="log-tab-btn" data-log="error">Error日志</label>');
						html.push('</p>')
						html.push('<div class="log_content log_'+log["event_id"]+'"></div>');
					html.push('</div>')
    			html.push('</div>');
    		html.push('</div>')
    	html.push('</div>')
	html.push('</li>');
	return html.join('');
}


/* 创建时间轴列表模版 */
function createLogListTmp(logList){
    if( jQuery.isEmptyObject(logList) )
    {
        return '<p style="text-align: center;font-size: 18px;">暂无记录<span class="span_src"><img src="/static/www/img/appOutline/log_src.png"></span></p>'
    }
    var htmls = '';
    for (var i = 0; i < logList.length; i++) {
    	var log = logList[i];
        htmls+=createLogItemTmp(log)
    }
    return htmls;
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

            var html = [];
	    	html.push('<li data-event-id="'+event.event_id+'" class="js-event-row">');
	    	html.push('<time class="tl-time">');
		    	html.push('<h4>'+time+'</h4>');
		    	html.push('<p>今天</p>');
	    	html.push('</time>');
	    	html.push('<i class="fa bg-grey tl-icon"></i>');
	    	html.push('<div class="tl-content">');
	    		html.push('<div class="panel panel-primary">');
	    			html.push('<div class="panel-heading">');
	    				var title = type_json[event["event_type"]] + '中@' + event["user_name"];
	    				html.push('<span>'+title+'</span>');
	    				html.push('<div class="user btns">');
	    					html.push('<a href="javascript:;" class="ajax_log_new" data-log="'+currentEventID+'">查看详情</a>');
	    					html.push('<a href="javascript:;" class="hide_log">收起</a>')
	    				html.push('</div>')
	    			html.push('</div>')
	    			html.push('<div class="panel-body">');
						html.push('<div class="log">')
							html.push('<p class="log_type">');
								html.push('<label class="active log-tab-btn" data-log="info">Info日志</label>');
								html.push('<label class="log-tab-btn" data-log="debug">Debug日志</label>');
								html.push('<label class="log-tab-btn" data-log="error">Error日志</label>');
							html.push('</p>')
							html.push('<div class="log_content log_height2 log_' + event["event_id"]+'"></div>');
						html.push('</div>')
	    			html.push('</div>');
	    		html.push('</div>')
	    	html.push('</div>')
			html.push('</li>');

            $(html.join('')).prependTo($("#keylog ul"));
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
	function getInitLog(tenantName, serviceAlias, start_time) {
		return $.ajax({
            type: "GET",
            url: "/ajax/"+tenantName+"/"+serviceAlias+"/events",
            data: {
            	action:'operate',
            	start_time: start_time ? start_time : dateUtil.format(new Date(), 'yyyy-MM-dd hh:mm')
            },
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
	template: template,
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
		http_port_str:'',
		//需要充值的钱
		needPay: 0,
		plugins:[],
		//充值后开始计费的日期
		payStartTime: '',
		renderData: {
			appInfo: {},
			pageData: {}
		}
	},
	method:{
		//获取页面初始化数据
		getInitData: function(){
			getAppInfo(
				this.tenantName,
				this.serviceAlias
			).done((appInfo) => {
				this.renderData.appInfo = appInfo;
				getPageOverviewAppData(
					this.tenantName,
					this.serviceAlias
				).done((pageData) => {
					this.renderData.pageData = pageData;
					this.render();
					// this.publicCloudShow(pageData.is_public_cloud);
					setTimeout(() => {
						this.initLog();
						this.checkStatus();
						$('.fn-tips').tooltip();
						$("#datetimepicker")
						.datetimepicker({format: 'YYYY-MM-DD HH:mm', locale: moment.locale('zh-cn')})
						.on('dp.change', (ev) => {
						    this.initLog(true);
						});
					})

					getNotInstalledPlugin(
						this.tenantName,
						this.serviceAlias
					).done((data) => {
						this.plugins = (data.relations || []).slice(0, 5);
						this.renderPlugin();

						if(this.isInstalledAnalysis()){
							$('.installed-new-plugin').show();
							$('.uninstall-new-plugin').hide();
							this.loadMonitorData();
						}
					})
				})
			})
		},
		//渲染安装的插件
		renderPlugin: function(){
			var html = [];
			if(this.plugins.length){
				html.push('<ul style="margin-top: 25px" class="installed-plug">')
				for(var i=0;i<this.plugins.length;i++){
					var item = this.plugins[i];
					html.push('<li class="ws-nowrap '+(!item.is_switch ? 'disabled' : '')+'"><a href="/apps/'+this.tenantName+'/'+this.serviceAlias+'/detail/?fr=plugin&plugin_id='+item.plugin_id+'" title="'+item.plugin_info.plugin_alias+'">'+item.plugin_info.plugin_alias+'</a></li>')
				}
				html.push('</ul>')
    
			}else{
				html.push('<div style="margin-top:60px">')
                    html.push('<div class="tips">')
                        html.push('<p>尚未安装插件</p>')
                        html.push('<a href="/apps/'+this.tenantName+'/'+this.serviceAlias+'/detail/?fr=plugin">去安装</a>')
                    html.push('</div>')
                html.push('</div>')
			}
			$('#plugin-list-wrap').html(html.join(''));
		},
		//加载监控数据
		loadMonitorData: function(){
			$.when(
				getAppRequestTime(
					{
						tenantName:this.tenantName,
						serviceAlias: this.serviceAlias,
						serviceId: this.serviceId
					}	
				),
				getAppRequest(
					{
						tenantName:this.tenantName,
						serviceAlias: this.serviceAlias,
						serviceId: this.serviceId
					}
				)
			).done((res1, res2)=>{
				var result1 = res1.bean.result;
				var result2 = res2.bean.result;
				if(result1 && result1.length){
	        		var res = Number(result1[0].value[1]) || 0;
	        		if(res >= 0){
	        			$('.app_requesttime').html(res.toFixed(0));
	        		}else{
	        			$('.app_requesttime').html(res.toFixed(1));
	        		}
	        	}
	        	if(result2 && result2.length){
	        		var res = Number(result2[0].value[1]) || 0;
	        		$('.app_request').html(res.toFixed(0));
	        		
	        	}

	        	setTimeout(()=>{
	        		this.loadMonitorData();
	        	}, 6000)
			})
		},
		//是否安装了性能分析插件
		isInstalledAnalysis: function(){
			for(var i=0;i<this.plugins.length;i++){
				if(this.plugins[i].plugin_info.category === 'analyst-plugin:perf'){
					return true;
				}
			}
			return false;
		},
		//初始化页面操作日志
		initLog: function(reload){
			var self =this;
			getInitLog(
				this.tenantName, 
				this.serviceAlias,
				$("#datetimepicker").val()
			).done(function(msg){

				if(reload){
					$("#keylog ul").html('');
					if(self.socket){
						self.socket.close();
						self.socket = null;
					}
					$(".load_more_new").hide();
				}


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
		            var eventId = $("#keylog .ajax_log_new").eq(0).attr('data-log');
		            self.getAndRenderEventLog(firstLog["event_id"]).always(() => {
		            	self.createLogSocket(firstLog["event_id"],firstLog["type"]);
		            })
		            
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
				//self.updatePayStatus(msg);
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
			this.onStatusChange(msg);
			this.status = msg.status;
		},
		//当状态变化时的回调
		onStatusChange: function(msg){
			var self = this;
			var obj=msg;
			if(obj["status"]!="failure"){
				var attachInfo = obj.service_attach_info || {};
				var lastCostInfo = obj.last_hour_consume || {};
				//更新内存信息
				$('.show_money').html((lastCostInfo.memory * lastCostInfo.node_num) || 0);
				//更新磁盘信息
				$('.show_disk').html(lastCostInfo.disk || 0);


				//隐藏该状态下不能操作的按钮
				var disabledAction = obj.disabledAction || [];
				$.each(disabledAction, function(index, action){
					$('[action='+action+']').hide();
				})
				//显示该状态下可以操作的按钮
				var activeAction = obj.activeAction || [];
				$.each(activeAction, function(index, action){
					$('[action='+action+']').show();
				})
				//更新状态描述
				var statusMap = util.getStatusMap(obj["status"]);
				//var statusCN = statusMap.statusCN;
				var statusCN = obj.status_cn;
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

		},
		//公有云私有云显示隐藏
		publicCloudShow(onoff){
			if(onoff){
				$("#MemoryCost").show();
				$("#DiskBox").show();
				$("#FlowBox").show();
				$("#CostBox").show();
			}else{
				$("#MemoryCost").hide();
				$("#DiskBox").hide();
				$("#FlowBox").hide();
				$("#CostBox").hide();
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
		},
		//重新启动
		NewrebootApp: function(){
			var self = this;
			this.isDoing = true;
			overViewGetEventId(
				this.tenantName,
				this.serviceAlias,
				this.rebootAction
			).done(function(eventId){
				NewrebootByEventId(
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
		},
		//更新应用
		updateApp: function(){
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
		},
		//重启动应用
		rebootApp: function(eventId) {
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
		},
		//根据　eventId 和 action 创建socket连接并生成消息
		createLogSocket: function(eventId, action) {
			var self = this;
			$("#keylog .panel-heading").eq(0).css({ "padding-bottom": "5px" });
			$("#keylog .log").eq(0).css({ "height": "20px" });
			$("#keylog .ajax_log_new").eq(0).hide();
			$("#keylog .hide_log").eq(0).show();
			$("#keylog .log_type").eq(0).hide();

			this.socket = new LogSocket({
				url: this.webSocketUrl,
				eventId: eventId,
				onMessage: function(data){
					var msgHtml = createLogTmp(data);
					$(msgHtml).prependTo($("#keylog .log_content").eq(0));
				},
				onClose: function() {
					self.isDoing = false;
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
		
		//非域名访问应用在线地址
		visitApp: function(port){
			var port = port ? (port + '.') : '';
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
	            $(".layer_pay").attr("data-original-title", tips);
	        } else if (pay_status == "debugging") {
	            $("#last_hour_fee").html("调试中");
	            $(".layer_pay").attr("data-original-title", tips);
	        } else if (pay_status == "unknown") {
	            $("#last_hour_fee").html("0元");
	            $(".layer_pay").attr("data-original-title", tips);
	        } else if (pay_status == "wait_for_pay") {
	            $("#last_hour_fee").html("等待支付");
	            $(".layer_pay").attr("data-original-title", tips);
	            this.needPay = msg["need_pay_money"];
	            this.payStartTime = msg["start_time_str"];

	        } else if (pay_status == "soon") {
	            $("#last_hour_fee").html("即将计费");
	            $(".layer_pay").attr("data-original-title", tips);
	        } else if (pay_status == "show_money") {
	            $("#last_hour_fee").html(msg["cost_money"] + "元");
	            $(".layer_pay").attr("data-original-title", tips);
	        } else {
	            $("#last_hour_fee").html("-");
	            $(".layer_pay").attr("data-original-title", tips);
	        }
		},
		//显示某个事件的日志信息, type: info/debug/error
		getAndRenderEventLog: function(eventId, type) {
			return getEventlogByType(this.tenantName, this.serviceAlias, eventId, type||'info')
			.done(function(data){

				$(".log_" + eventId + "").html('');
	            var dataObj = data;
	            var html=[];
	            var newLog = dataObj["data"] || [];
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
			var adPopup = window.open('about:blank');
			createAppContainerSocket(
				this.tenantName,
				this.serviceAlias,
				c_id,
				h_ip
			).done(function(){
				adPopup.location.href = "/apps/"+self.tenantName+"/"+self.serviceAlias+"/docker/";
			}).fail(function(){
				adPopup.close();
			})
		},
		showPayConfirm: function() {
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
		//域名地址访问
		'.visit-domain click': function(e){
			var $target = $(e.currentTarget);
			var domain = $target.attr('data-domain')
			if(domain){
				window.open(domain)
			}
			
		},
		//访问
		'.visit-btn click': function(e) {
			var port = $(e.target).data('port')||'';
			this.visitApp(port);
		},
		//访问应用地址事件
		'#service_visitor click': function(e) {
			var port = $(e.target).data('port')||'';
			this.visitApp(port);
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
		//重启应用事件
		'#onekey_reboot click': function(e){
			if(this.isDoing){
				return;
			}
			this.NewrebootApp();
		},
		//版本回滚事件
		'.callback_version click': function(e) {
			var self = this;
			if(this.isDoing){
				return;
			}
			var $target = $(e.target);
			var version = $target.data('version');

			var confirm = widget.create('confirm', {
				title: '版本回滚',
				content: '确定恢复当前版本吗？',
				event: {
					onOk: function() {
						self.rollbackApp(version);
						confirm.destroy();
						confirm = null;
					}
				}
			})
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
			if(this.needPay){
				this.showPayConfirm();
			}
		},
		//确认付款
		'.sure_pay click': function(e) {
			var self = this;
	        appPay(
	        	self.tenantName,
	        	self.serviceAlias
	        )
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
		this.renderData.tenantName = this.tenantName;
		this.renderData.serviceAlias = this.serviceAlias;
		this.getInitData()
	}
})
/*  --------------- 业务逻辑控制器 end --------------- */

export default AppOverviewController;