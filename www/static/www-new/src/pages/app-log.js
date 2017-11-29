import createPageController from '../utils/page-controller';
import { getTenantAllAppsStatusAndMemory, 
	getAppLog, 
	getAppLogSocketUrl, 
	checkAppLogOutput,
	cancelAppLogOutput,
	setAppLogOutput,
	getAppContainer,
	getAppInfo
} from '../comms/app-apiCenter';
import { getCanReceiveLogApp } from '../comms/apiCenter';
import {
	getPageLogAppData
} from '../comms/page-app-apiCenter';
import AppLogSocket from '../utils/appLogSocket';
import widget from '../ui/widget';
var template = require('./app-log-tpl.html');

const Msg = widget.Message;


const createReceiveAppTmp = (apps) => {
	var longstr = "<form>";
    for (var i = 0; i < apps.length; i++) {
    	longstr += '<div class="checkbox"><label>';
        longstr += '<input type="radio" name="app" id="' + apps[i].service_id + '"data-type="' + apps[i].service_type + '"data-alias="' + apps[i].service_alias + '"value="' + apps[i].service_cname + '" />' + apps[i].service_cname;
    	longstr += '</label></div>';
    }
    longstr += '</form>'
    return longstr;
}

const createAppinstanceTmp = (dataObj) => {
	var msg = "<li><a href='javascript:void(0);'  data-key='' class='fn-example'> 全部日志</a></li>"
    var tindex = 1;
    delete dataObj.split;
    for (var key in dataObj) {
            msg += "<li>";
            msg += "<a href='javascript:void(0);'  data-key='"+ key +"' class='fn-example'> 实例" + tindex + "</a></li>"
            tindex += 1;
    }
    return msg;
}


/* 应用日志页面 业务逻辑控制器 */
const AppLog = createPageController({
	template: template,
	property: {
		tenantName:'',
		serviceAlias:'',
		serviceId:'',
		socket: null,
		instanceId: '',
		//应用状态控制
		status: 'start',
		//应用是否已经设置了日志输出
		isAppLogOutput: false,
		renderData:{
			appInfo:{},
			pageData:{}
		}
	},
	method: {
		//获取页面初始化数据
		getInitData: function(){
			getAppInfo(
				this.tenantName,
				this.serviceAlias
			).done((appInfo) => {
				this.renderData.appInfo = appInfo;
				getPageLogAppData(
					this.tenantName,
					this.serviceAlias
				).done((pageData) => {
					this.renderData.pageData = pageData;
					this.render();
					setTimeout(() => {
						this.initAppIntances();
						this.initLog();
						this.checkAppLogOutput();
					})
				})
			})
		},
		//监测日志是否设置输出
		checkAppLogOutput: function() {
			var self = this;
			checkAppLogOutput(
				this.tenantName,
				this.serviceAlias
			).done(function(){
				self.setIsApplogOutput(true)
			}).fail(function(){
				self.setIsApplogOutput(false)
			})
		},
		setIsApplogOutput: function(flag){
			this.isAppLogOutput = flag;
			if(this.isAppLogOutput) {
				$("#logbtn_out").html("取消日志输出").attr("id","logbtn_delete")
			}else{
				$("#logbtn_delete").html("日志输出").attr("id","logbtn_out");
			}
		},
		initLog: function(){
			var self = this;
			getAppLog(
				this.tenantName,
				this.serviceAlias,
				this.instanceId
			).done(function(logHtml){
				$("#docker_log").html(logHtml||'');
				self.initSocket();
			})
		},
		initSocket: function(){
			var self = this;
			if(this.socket) {
				try{
					this.socket.close();
					this.socket = null;
				}catch(e){

				}
			}
			getAppLogSocketUrl(
				this.tenantName,
				this.serviceAlias
			).done(function(url){
				self.socket = new AppLogSocket({
					url: url,
					instanceId: self.instanceId,
					serviceId: self.serviceId,
					onMessage: function(msg) {
						self.status == 'start' && $(msg).prependTo($("#docker_log"));
					}
				})
			})
			
		},
		//初始化应用实例数据
		initAppIntances: function() {
			getAppContainer(
				this.tenantName,
				this.serviceAlias
			).done(function(dataObj){
                $("#cur_container_content").html(createAppinstanceTmp(dataObj))
                
			})
		},
		showLogOutputDialog: function() {
			var self = this;
			getCanReceiveLogApp(
				this.tenantName
			).done(function(apps){

				var dialog = widget.create('dialog', {
					title: '指定日志应用',
					id:'logOutput',
					width: '500px',
					height: '300px',
					domEvents:{
						'.btn-success click': function(){
							var serviceId = dialog.getElement().find("input[type='radio']:checked").attr("id");
            				var serviceType = dialog.getElement().find("input[type='radio']:checked").attr("data-type");
							self.handleSetAppLogOutput(
								serviceId,
								serviceType
							).done(function(){
								self.setIsApplogOutput(true)
								Msg.success('操作成功');
								dialog.destroy();
								dialog = null;
							})
						}
					}
				})
				dialog.appendContent($('#setAppOutputDialogTmp').html());
                dialog.appendContent(createReceiveAppTmp(apps));
                dialog.getElement().find("input").eq(0).attr("checked", "true");
				
			})
			
		},
		handleSetAppLogOutput: function(serviceId, serviceType) {
			return setAppLogOutput(
				this.tenantName,
				this.serviceAlias,
				serviceId,
				serviceType
			)
		},
		handleCancelAppLogOutput: function() {
			var self = this;
			cancelAppLogOutput(
				this.tenantName,
				this.serviceAlias
			).done(function(data){
				self.setIsApplogOutput(false)
			})
		},
		openStatus: function(initSocket){
			this.status = "start";
	        $('.js-status-control').html("暂停");
	        initSocket && this.initSocket();
		},
		closeStatus: function() {
			this.status = "stop";
	        $('.js-status-control').html("开始");
	        this.socket.close();
		}
	},
	domEvents: {
		//日志事件
		'.fn-example click': function(e){
			var $target = $(e.currentTarget);
			this.instanceId = $target.attr('data-key');
			$('.log-type-text').html($target.html());
			this.openStatus();
			this.initLog();
		},
		//开始暂停事件绑定
		'.js-status-control click': function(){
			if (this.status == "stop") {
	            this.openStatus(true);
	        } else if (this.status == "start") {
	            this.closeStatus();
        	}
		},
		//设置日志输出事件
		'#logbtn_out click': function() {
			this.showLogOutputDialog();
		},
		//取消日志输出事件
		'#logbtn_delete click': function() {
			this.handleCancelAppLogOutput();
		}
	},
	onReady: function(){
		this.renderData.tenantName = this.tenantName;
		this.renderData.serviceAlias = this.serviceAlias;
		this.getInitData();
		
	}
})

window.AppLogController = AppLog;
export default AppLog;