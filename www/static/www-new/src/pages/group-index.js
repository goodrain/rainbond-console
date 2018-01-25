import createPageController from '../utils/page-controller';
import { 
	getTenantAllAppsStatusAndMemory,   
	betchOpenApp,
	betchDeployApp,
	betchCloseApp
} from '../comms/apiCenter';
import {
	deployApp, 
	openApp, 
	closeApp,
	changeGroup
} from '../comms/app-apiCenter';
import { shareGroup, addGroup, deleteGroup, updateGroupName } from '../comms/group-apiCenter';
import util from '../utils/util';
import widget from '../ui/widget';
import editGroup from '../components/editGroup';

const Msg = widget.Message;

/* 业务逻辑控制器 */
const GroupIndexController = createPageController({
	property: {
		//租户名
		tenantName: '',
		checkInterval: 6 * 1000,
		//应用群组id
		groupId:'',
		//群组名称
		groupName: '',
		//所有的组名
		allGroups:[],
		apps:[]
	},
	method: {
		//轮询监测应用列表的运行状态
		checkAppsInfo: function() {
		    return getTenantAllAppsStatusAndMemory(
				this.tenantName
			).done((data) => {
				if(data && data.list){
					this.apps = data.list || [];
				}
				console.log(this.apps)
				this.updateAppsInfo(data);
			})
		},
		loopCheck:function() {

			this.checkAppsInfo().always(() => {
				setTimeout(() => {
					this.loopCheck();
				}, this.checkInterval);
			})
		},
		//切换到列表视图
		changeToListView:function(){
			$('#imgBox').hide();
			$('#tabBox').show();
			$('#imgbtn').removeClass('btn-success');
			$('#tabbtn').addClass('btn-success');
		},
		//切换到拓扑图视图
		changeToImgView:function(){
			$('#imgBox').show();
			$('#tabBox').hide();
			$('#imgbtn').addClass('btn-success');
			$('#tabbtn').removeClass('btn-success');
		},
		//更新状态dom
		updateAppsInfo: function(result){
			var list = result.list;
			var totalMemory = result.totalMemory;
			for(var i=0,len=list.length; i < len; i++){
				var app = list[i];
				var statusMap = util.getStatusMap(app.status);
				var activeAction = app.activeAction;
				var disableAction = app.disabledAction;

				var $row = $('tr[data-id='+app.id+']');
				$row.attr('data-status', app.status);
				$("#service_status_"+app.id).html(app.statusCN).attr('class', statusMap.bgClass + ' pading5');
				$("#service_memory_"+app.id).html(app.runtime_memory + 'M');
				//显示可执行的操作
				activeAction.forEach((val, index) => {
					$row.find('[data-action='+val+']').show();
				})
				//隐藏不可执行的操作
				disableAction.forEach((val, index) => {
					$row.find('[data-action='+val+']').hide();
				})
			}
		},
		//获取选择的应用
		getSelectedApp: function(){
			var datas = [];
			$('input[name=SelectItem]:checked').each(function(){
				datas.push($(this).val());
			})
			return datas;
		},
		onSelectedChange: function() {
			var selectedDatas = this.getSelectedApp();
			if(selectedDatas.length > 0){
				$('[data-action=betch-restart]').prop('disabled', false);
				$('[data-action=betch-stop]').prop('disabled', false);
				$('[data-action=betch-deploy]').prop('disabled', false);
			}else{
				$('[data-action=betch-restart]').prop('disabled', true);
				$('[data-action=betch-stop]').prop('disabled', true);
				$('[data-action=betch-deploy]').prop('disabled', true);
			}
			$('#app-numbers span').html(selectedDatas.length);
		},
		isAppCanDo: function(id, action){
			var apps = this.apps || [];
			for(var i=0;i<apps.length;i++){
				if(apps[i].id == id){

					return apps[i].activeAction.indexOf(action) > -1
				}
			}
			return true;
		},
		handleDeploy: function(serviceAlias, category){
			deployApp(
				category, 
				this.tenantName, 
				serviceAlias
			).done(function(data){
				Msg.success('操作成功');
			})
		},
		handleRestart: function(serviceAlias, serviceId){
			var self = this;
			openApp(
				this.tenantName, 
				serviceAlias, 
				serviceId
			).done(function(){
				Msg.success('操作成功');
				self.checkAppsInfo();
			})
		},
		handleStop: function(serviceAlias, serviceId) {
			var self = this;
			closeApp(
				this.tenantName, 
				serviceAlias, 
				serviceId
			).done(function(){
				Msg.success('操作成功');
				self.checkAppsInfo();
			})
		},
		betchOpenApp: function() {
			var self = this, selectedIds = this.getSelectedApp();
			if(!selectedIds.length){
				Msg.warning('请选择要操作的应用');
				return;
			}

			selectedIds = selectedIds.filter(function (id){
				return self.isAppCanDo(id, 'restart');
			})

			if(!selectedIds.length){
				Msg.warning('没有可以执行此操作的应用');
				return;
			}

			if(selectedIds.length){
				betchOpenApp(
					this.tenantName,
					selectedIds
				).done(function(){
					Msg.success('操作成功');
					self.checkAppsInfo();
				})
			}
		},
		handleBetchClose: function() {
			var self = this, selectedIds = this.getSelectedApp();
			console.log(selectedIds)
			if(!selectedIds.length){
				Msg.warning('请选择要操作的应用');
				return;
			}

			selectedIds = selectedIds.filter(function (id){
				return self.isAppCanDo(id, 'stop');
			})

			if(!selectedIds.length){
				Msg.warning('没有可以执行此操作的应用');
				return;
			}

			if(selectedIds.length){
				betchCloseApp(
					this.tenantName,
					selectedIds
				).done(function(){
					Msg.success('操作成功');
					self.checkAppsInfo();
				})
			}
		},
		//批量启动
		handleBetchDeploy: function() {
			var self = this, selectedIds = this.getSelectedApp();

			console.log(selectedIds)
			if(!selectedIds.length){
				Msg.warning('请选择要操作的应用');
				return;
			}


			selectedIds = selectedIds.filter(function (id){
				return self.isAppCanDo(id, 'deploy');
			})

			if(!selectedIds.length){
				Msg.warning('没有可以执行此操作的应用');
				return;
			}

			if(selectedIds.length){
				betchDeployApp(
					this.tenantName,
					selectedIds
				).done(function(){
					Msg.success('操作成功');
					self.checkAppsInfo();
				})
			}else{

			}
		},
		//分享组
		handleShare: function(){
			shareGroup(
				this.tenantName,
				this.groupId
			).done(function(data){
				if(data.next_url){
					location.href = data.next_url;
				}
				
			})
		},
		//修改组名
		handleUpdateGroupName: function(e) {
			var self = this;
			//表单
			var form = widget.create('form', {
				hideLabel: true,
				items: [{
					name: 'groupName',
					type: 'text', 
					label: '新组名',
					required: true,
					requiredError: '请输入新的组名',
					value: this.groupName
				}]
			})
			//确认框
			var confirm = widget.create('confirm', {
				hideLabel: true,
				title: '组名修改',
				height: '180px',
				event:{
					onOk: function(){
						if(form.valid()) {
							var groupName = form.getValue('groupName');
							updateGroupName(
								self.tenantName,
								self.groupId,
								groupName
							).done(function(){
								setTimeout(() => {
									location.reload();
								}, 2000)
								
							})
						}
					},
					onCancel: function() {
						form.destroy();
						form = confirm = null;
					}
				}
			})
			confirm.setContent(form.getElement())
		},
		//删除组
		handleDeleteGroup: function(e) {
			var self = this;
			var confirm = widget.create('confirm', {
				title: '删除组',
				content: '您确定要删除当前组么？',
				event: {
					onOk: function() {
						deleteGroup(
							self.tenantName,
							self.groupId
						).done(function(data){
							confirm.destroy();
							confirm = null;
							setTimeout(function(){
								location.href = '/';
							}, 2000)
							
						})
					}
				}
			})
		},
		//新增组
		handleAddGroup: function(e) {
			var self = this;
			//表单
			var form = widget.create('form', {
				hideLabel: true,
				items: [{
					name: 'groupName',
					type: 'text', 
					label: '群组名称',
					placeholder: '请输入组名称',
					required: true,
					requiredError: '请输入群组名称'

				}]
			})
			//确认框
			var confirm = widget.create('confirm', {
				title: '添加新组',
				event:{
					onOk: function(){
						if(form.valid()) {
							var groupName = form.getValue('groupName');
							addGroup(
								self.tenantName,
								groupName
							).done(function(){
								Msg.success("操作成功!")
								setTimeout(() => {
									location.reload();
								}, 2000)
								
							})
						}
					},
					onCancel: function() {
						form.destroy();
						form = confirm			
					}
				}
			})
			confirm.setContent(form.getElement())
		},
		handleAppChangeGroup:function (serviceId, serviceCname, groupId) {
			var self = this;
			widget.create('editGroup', {
				tenantName: this.tenantName,
				groupId: groupId,
				serviceId: serviceId,
				serviceName: serviceCname,
				groupList:this.allGroups,
				onSuccess: function() {
					$('tr[data-id='+ serviceId +']').remove();
				}
			})
		}
	},
	domEvents: {
		//列表单选
		'input[name=SelectItem] click': function(e) {
			var allLen = $('input[name=SelectItem]').length;
			var selectedLen = $('input[name=SelectItem]:checked').length;
			if(allLen === selectedLen) {
				$('input[name=SelectAll]').prop('checked', true)
			}else{
				$('input[name=SelectAll]').prop('checked', false)
			}
			this.onSelectedChange();
		},
		// 全选／取消全选
		'input[name=SelectAll] change': function(e){
			var $target = $(e.target);
			var checked = $target.prop('checked');
			if(checked) {
				$('input[name=SelectItem]').prop('checked', true);
			}else{
				$('input[name=SelectItem]').prop('checked', false);
			}
			this.onSelectedChange();
		},
		//单个部署
		'[data-action=deploy] click': function(e) {
			var $target = $(e.currentTarget);
			var $tr = $target.parents('tr');
			var serviceAlias = $tr.attr('data-service-alias');
			var category = $tr.attr('data-category');
			this.handleDeploy(serviceAlias, category);
		},
		//单个启动应用
		'[data-action=restart] click': function(e) {
			var $target = $(e.currentTarget);
			var $tr = $target.parents('tr');
			var serviceAlias = $tr.attr('data-service-alias');
			var serviceId = $tr.attr('data-id');
			this.handleRestart(serviceAlias, serviceId);
		},
		//单个关闭应用
		'[data-action=stop] click': function(e) {
			var $target = $(e.currentTarget);
			var $tr = $target.parents('tr');
			var serviceAlias = $tr.attr('data-service-alias');
			var serviceId = $tr.attr('data-id');
			this.handleStop(serviceAlias, serviceId);
		},
		//批量启动app
		'#batchStart click': function(e) {
			this.betchOpenApp();
		},
		//批量关闭app
		'#batchEnd click': function(e) {
			this.handleBetchClose();
		},
		//批量部署app
		'#newStart click': function(e){
			this.handleBetchDeploy();
		},
		//分享事件
		'#groupShare click': function(e) {
			this.handleShare();
		},
		//切换到拓扑图界面事件
		'#imgbtn click': function(e) {
			this.changeToImgView();
		},
		//切换到拓扑图界面事件
		'#tabbtn click': function(e) {
			this.changeToListView();
		},
		//修改组名事件
		'#revise-groupname click': function(e) {
			this.handleUpdateGroupName(e);

		},
		//删除当前组事件
		'#reomve-groupname click': function(e) {
			this.handleDeleteGroup(e);
		},
		//新增组名事件
		'#add-groupname click': function(e) {
			this.handleAddGroup(e);
		},
		//应用更换分组
		'.fn-name click': function(e) {
			var $target = $(e.currentTarget);
			var $tr = $target.closest('tr');
			var serviceId = $tr.attr('data-id');
			var groupId = $tr.attr('data-group');
			var serviceCname = $tr.attr('data-service-cname');
			this.handleAppChangeGroup(serviceId, serviceCname, groupId);
		},
		//全屏 
		'.toFullScreen click': function(e) {
			$('#svg-box').addClass('fullScreen');
			$('#svg-box').find('iframe')[0].contentWindow.location.reload();
		},
		'.exitFullScreen click': function(e) {
			$('#svg-box').removeClass('fullScreen');
			$('#svg-box').find('iframe')[0].contentWindow.location.reload();
		}
	},
	onReady: function(){
		this.loopCheck();

		//未分组
		if(this.groupId == '-1'){
			$("#tabBox").show();
        	$("#imgBox").hide();
		}
	}
})

window.GroupIndexController = GroupIndexController;
export default GroupIndexController;