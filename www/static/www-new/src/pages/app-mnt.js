import createPageController from '../utils/page-controller';
import { getTenantAllAppsStatusAndMemory } from '../comms/apiCenter';
import {
	addDir,
	removeDir,
	connectAppDisk, 
	cutConnectedAppDisk,
	getAppInfo
} from '../comms/app-apiCenter';
import {
	getPageMntAppData
} from '../comms/page-app-apiCenter';

import widget from '../ui/widget';
import volumeUtil from '../utils/volume-util';
require('../components/add-volumepath');
require('../components/add-shared-volumepath');

const Msg = widget.Message;
const template = require('./app-mnt-tpl.html');






//创建持久化条目模版
const createDirTmp = (data) => {
	return '<tr><td>'+data.volume_name+'</td><td>'+data.volume_path+'</td><td>'+volumeUtil.getTypeCN(data.volume_type)+'</td><td class="text-right"><button type="button" data-id="'+data.ID+'" class="btn btn-default btn-sm removeDir">删除</button></td></tr>'
}

/* 业务逻辑控制器 */
const AppMnt = createPageController({
	template: template,
	property: {
		//租户名
		tenantName: '',
		serviceAlias: '',
		servicecName: '',
		//当前应用语言类型
		language:'',
		code_from:'',
		serviceId:'',
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
				getPageMntAppData(
					this.tenantName,
					this.serviceAlias
				).done((pageData) => {
					var vList = pageData.volume_list||[];
					var mList = pageData.mounted_apps || [];
					vList.forEach((item) => {
						item.volume_type_cn = volumeUtil.getTypeCN(item.volume_type);
					})
					mList.forEach((item) => {
						item.dep_vol_type_cn = volumeUtil.getTypeCN(item.dep_vol_type);
					})

					this.renderData.pageData = pageData;
					this.render();
				})
			})
		},
		handleRemoveDir:function(id) {
			return removeDir(
				this.tenantName,
				this.serviceAlias,
				id
			)
		},
		handleConnectAppDisk: function(destServiceAlias) {
			var self = this;
			connectAppDisk(
				this.tenantName,
				this.serviceAlias,
				destServiceAlias
			).done(function(data){
				Msg.success("操作成功");
				self.getInitData();
			})
		},
		handleCutConnectAppDisk: function(id) {
			var self = this;
			cutConnectedAppDisk(
				this.tenantName,
				this.serviceAlias,
				id
			).done(function(data){
				Msg.success("操作成功");
				self.getInitData();
			})
		},
		showAddVolumeDialog: function(){
			var self = this;
			var dialog = widget.create('addVolumepath', {
				serviceInfo: this.renderData.pageData.tenantServiceInfo,
				onOk: function(name, path, type){
					addDir(
						self.tenantName,
						self.serviceAlias,
						name,
						path,
						type
					).done(function(data){
						self.getInitData();
						dialog.destroy();
					})
				}
			})
		}
	},
	domEvents:{
		//添加持久化目录
		'#add_volume_attr click': function(e) {
			this.showAddVolumeDialog();
		},
		//删除持久化目录条目
		'.removeDir click': function(e) {
			var $target = $(e.currentTarget);
			var id = $target.attr('data-id');
			if(id){
				this.handleRemoveDir(id).done(function(){
					$target.parents('tr').remove();
				})
			}
		},
		//挂载事件　
		'.connectAppDisk click': function(e) {
			var destServiceAlias = $(e.currentTarget).parents('tr').attr('data-dest-service-alias');
			if(destServiceAlias) {
				this.handleConnectAppDisk(destServiceAlias);
			}
		},
		//取消挂载事件
		'.cutConnectAppDisk click': function(e) {
			var id = $(e.currentTarget).attr("data-id");
			if(id) {
				this.handleCutConnectAppDisk(id);
			}
		},
		'.connectSharedAppDisk click': function(e){
			var dialog = widget.create('addSharedVolumepath', {
				tenantName: this.tenantName,
				serviceAlias: this.serviceAlias,
				serviceList: this.renderData.pageData.tenantServiceInfo,
				serviceAlias: this.renderData.pageData.serviceAlias,
				mntServiceIds: this.renderData.pageData.mntsids,
				onOk: () => {
					this.getInitData();
				},
				onFail: () => {
					this.getInitData();
				}
			})
		}
	},
	onReady: function(){
		this.getInitData();
	}
})

window.AppMntController = AppMnt;
export default AppMnt;