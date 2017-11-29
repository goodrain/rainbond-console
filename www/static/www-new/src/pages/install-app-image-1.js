/*
    镜像创建应用-1： 设置镜像基本信息
*/


import createPageController from '../utils/page-controller';
import { getTenantAllAppsStatusAndMemory, 
	
} from '../comms/install-app-apiCenter';
import { getCanReceiveLogApp } from '../comms/apiCenter';
import {
	getPageLogAppData
} from '../comms/page-app-apiCenter';
import AppLogSocket from '../utils/appLogSocket';
import widget from '../ui/widget';
var template = require('./app-log-tpl.html');
const Msg = widget.Message;



/* 应用日志页面 业务逻辑控制器 */
const InstallAppImageOne = createPageController({
	template: template,
	property: {
		tenantName:'',
		renderData:{
			pageData:{}
		}
	},
	method: {
		//获取页面初始化数据
		getInitData: function(){
			getPageLogAppData(
				this.tenantName,
				this.serviceAlias
			).done((pageData) => {
				this.renderData.pageData = pageData;
				this.render();
			})
		}
	},
	domEvents: {

	},
	onReady: function(){
		this.renderData.tenantName = this.tenantName;
		this.getInitData();
		
	}
})

window.InstallAppImageOneController = InstallAppImageOne;
export default InstallAppImageOne;