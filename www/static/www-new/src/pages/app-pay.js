import createPageController from '../utils/page-controller';
import { 
	getMemoryMonthlyInfo,
	getAppMonthlyInfo,
	appMonthlyAddTime,
	getDiskMonthlyInfo,
	appDiskMonthly,
	appDiskMonthlyNoMonth,
	appMemoryMonthly,
	appMemoryMonthlyExpansionInfo,
	postMemoryMonthlyExpansion,
	getAppInfo
} from '../comms/app-apiCenter';
import { getCanReceiveLogApp } from '../comms/apiCenter';
import {
	getPagePayAppData
} from '../comms/page-app-apiCenter';
import widget from '../ui/widget';

const Msg = widget.Message;
var  template = require('./app-pay-tpl.html');

/* 应用日志页面 业务逻辑控制器 */
const AppPay = createPageController({
	template: template,
	property: {
		tenantName:'',
		serviceAlias:'',
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
				getPagePayAppData(
					this.tenantName,
					this.serviceAlias
				).done((pageData) => {
					this.renderData.pageData = pageData;
					this.render();
				})
			})
		},
		//内存包月选择时长付款
		handleMemorySelectTimePay: function(data) {
			var self = this;
			//内存包月一个月多少钱
			var oneMonthMoney = data.oneMonthMoney;
			//最后需要付款的钱
			var needPay = oneMonthMoney;
			var form = widget.create('form', {
				rowNum: 1,
				items:[{
					label: '包月时长',
					type: 'info',
					value: '<input style="display:inline-block;width:60%" type="range" min="1" max="24" step="1" id="TimeLong" value="1"><span><cite id="TimeLongText" class="text-success">1</cite>个月</span>'
				},{
					label: '费用总计',
					type: 'info',
					value: '<span id="TimeLongMoney" class="text-success">'+oneMonthMoney+'</span>元'
				}]
			})
			var dialog = widget.create('dialog', {
				title: '购买内存包月',
				content: form.getElement(),
				height:'250px',
				btns:[{
					classes: 'btn btn-success',
					text: '确认付款'
				},{
					classes: 'btn btn-default btn-cancel',
					text: '取消'
				}],
				domEvents: {
					//点击确认付款按钮
					'.btn-success click': function() {
						var monthNum = dialog.getElement().find('#TimeLong').val();
						appMemoryMonthly(
							self.tenantName,
							self.serviceAlias,
							monthNum,
							needPay
						).done(function(data){
							form.destroy();
							dialog.destroy();
							form = dialog = null;
							self.getInitData();
						})
					},
					//当包月条长度变化时
					'#TimeLong input': function() {
						needPay = (dialog.getElement().find('#TimeLong').val() * oneMonthMoney).toFixed(2);
	                	$("#TimeLongMoney").html(needPay);
	                	$('#TimeLongText').html($('#TimeLong').val())
					}
				}
			})
		},
		//内存包月不选择时长， 直接付款
		handleMemoryDirectPay: function(data) {
			var self = this;
			var form = widget.create('form', {
				rowNum: 1,
				items:[{
					label: '包月时长',
					type: 'info',
					value: '<p class="the_same text-danger">内存与磁盘包月时长应保持一致，剩余时间<span class="text-success day">'+data.remainDay+'</span>天<span  class="text-success hour">'+data.remainHour+'</span>小时</p>'
				},{
					label: '费用总计',
					type: 'info',
					value: '<span id="TimeLongMoney" class="text-success">'+data.toPayMoney+'</span>元'
				}]
			})
			var dialog = widget.create('dialog', {
				title: '购买内存包月',
				content: form.getElement(),
				height:'250px',
				btns:[{
					classes: 'btn btn-success',
					text: '确认付款'
				},{
					classes: 'btn btn-default btn-cancel',
					text: '取消'
				}],
				domEvents: {
					//点击确认付款按钮
					'.btn-success click': function() {
						appMemoryMonthly(
							self.tenantName,
							self.serviceAlias,
						).done(function(data){
							form.destroy();
							dialog.destroy();
							form = dialog = null;
							self.getInitData();
						})
					}
				}
			})
		},
		showMemoryExpansionDialog: function(data){

			var $showNodeNum = null;
			//节点数input
			var $nodeNumInput = null;

			//显示内存数
			var $showMemory = null;
			var $memoryInput = null;
			var $showMoney = null;

			//根据选择的内存数 计算要提交的内存数， 如果大于1024M 则取1024的整数倍， 即向上取正到GB
			function computedMemory(memory) {
				if(memory < 1024 ){
					return memory;
				}else{
					return Math.floor(memory/1024) * 1024;
				}
			}

			//计算要显示的内存数,  带单位
			function computedShowMemory(memory){
				if(memory < 1024 ){
					return memory +' M';
				}else{
					return Math.floor(memory/1024) + ' G';
				}
			}

			//计算要显示的金额
			function computedMoney() {
				var memory = computedMemory($memoryInput.val());
				var nodeNum = data.canSetNodeNums ? $nodeNumInput.val() : 1;
				var money = ( nodeNum * memory - data.minMemory ) * data.unitMoney;
				$showMoney.html(money.toFixed(2));
				return money;
			}

			var self = this;
			var form = widget.create('form', {
				rowNum: 1,
				items:[{
					label: '节点数',
					name: 'nodeNum',
					type:'info',
					value: '<input style="display:inline-block;width:60%" type="range" min="'+data.minNode+'" max="20" step="1" id="NodeNum" value="'+data.minNode+'" /><span><cite id="NodeText" class="text-success">'+data.minNode+'</cite>个</span>'
				},{
					label: '单节点内存',
					type:'info',
					value: '<input style="display:inline-block;width:60%" type="range" min="'+data.minMemory+'" max="'+data.maxMemory+'" step="128" id="OneMemory" value="'+data.minMemory+'" ／><span><cite id="OneMemoryText" class="text-success"></cite></span>'
				},{
					label: '新增费用',
					type:'info',
					name: 'money',
					value: '<span id="deployMoney" class="text-success">'+(data.payMoney || 0)+'</span><span>元（按当前包月时长计算）</span>'
				}]
			})

			var dialog = widget.create('dialog', {
				title: '增加内存包月额度',
				content: form.getElement(),
				height:'300px',
				btns:[{
					classes: 'btn btn-success',
					text: '确认付款'
				},{
					classes: 'btn btn-default btn-cancel',
					text: '取消'
				}],
				domEvents:{
					'.btn-success click': function(){
						var payMoney = computedMoney();
						if(payMoney <= 0) {
							form.destroy();
							dialog.destroy();
							form = dialog = null;
						}else{
							postMemoryMonthlyExpansion(
								self.tenantName,
								self.serviceAlias,
								computedMemory($memoryInput.val()),
								$('#NodeNum').val()
							).done(function(){
								form.destroy();
								dialog.destroy();
								form = dialog = null;
								self.getInitData();
							})
						}
						
					},
					'#NodeNum input': function(){
						if(!data.canSetNodeNums){ return };
						$('#NodeText').html($('#NodeNum').val());
						computedMoney();
					},
					'#OneMemory input': function(){
						$('#OneMemoryText').html(
							computedShowMemory(
								computedMemory($('#OneMemory').val())
							)
						)
						computedMoney();

					}
				}
			})

			var $dialog = dialog.getElement();
			$showMoney = $dialog.find('#deployMoney');
			//显示节点数
			$showNodeNum = $dialog.find('#NodeText');
			//节点数input
			$nodeNumInput = $dialog.find('#NodeNum');

			//显示内存数
			$showMemory = $dialog.find('#OneMemoryText');
			$memoryInput = $dialog.find('#OneMemory');
			//初始化显示内存数
			$showMemory.html(computedShowMemory(data.minMemory));

			//如果不能设置节点数量
			if(!data.canSetNodeNums){
				form.hideInput('nodeNum');
			}

			if(!data.showMoney){
				form.hideInput('money');
			}
		},
		//内存包月扩容
		handleMemoryExpansion: function() {
			var self = this;
			appMemoryMonthlyExpansionInfo(
				this.tenantName,
				this.serviceAlias
			).done(function(data){
				self.showMemoryExpansionDialog(data);
			})
		},
		//内存包月
		handleMemoryMonthly: function() {
			var self = this;
			getMemoryMonthlyInfo(
				this.tenantName,
				this.serviceAlias
			).done(function(data){
				//硬盘还没有选择包月时长， 内存可以选择的情况
				if(data.choosable){
					self.handleMemorySelectTimePay(data)
				}else{
					self.handleMemoryDirectPay(data);
				}
			})
		},
		//显示硬盘包月弹框
		showDiskMonthlyDialog: function(data, choosable){
			var self = this;
			var unitMoney = choosable ? data.oneMonthOneGmoney : data.oneGmoney;
			var needPay = unitMoney;

			//创建表单
			var form = widget.create('form', {
				rowNum: 1,
				items:[{
					label: '包月时长',
					type: 'info',
					name: 'monthInfo',
					value: '<p class="the_same text-danger">磁盘与内存包月时长应保持一致，剩余时间<span  class="text-success">'+data.remainDay+'</span>天<span  class="text-success">'+data.remainHour+'</span>小时</p>'
				},{
					label: '包月时长',
					type: 'info',
					name: 'monthInput',
					value: '<input style="display:inline-block;width:60%" type="range" min="1" max="24" step="1" id="LongDisk" value="1"><span><cite id="LongDiskText" class="text-success">1</cite>个月</span>'
				},{
					label: '包月额度',
					type: 'info',
					value: '<input style="display:inline-block;width:60%" type="range" min="1" max="200" step="1" id="LongDiskSize" value="1"><span><span><cite id="DiskSizeText" class="text-success">1</cite>G</span>'
				},{
					label: '费用总计',
					type: 'info',
					value: '<span id="LongDiskMoney" class="text-success">'+ needPay +'</span>元'
				}]
			})
			//创建弹框
			var dialog = widget.create('dialog', {
				title: '购买磁盘包月',
				content: form.getElement(),
				height:'300px',
				btns:[{
					classes: 'btn btn-success',
					text: '确认付款'
				},{
					classes: 'btn btn-default btn-cancel',
					text: '取消'
				}],
				domEvents: {
					//点击确认付款按钮
					'.btn-success click': function() {
						
						var $wrap = dialog.getElement();
							var monthNum = $wrap.find('#LongDisk').val();
							var diskSize = $wrap.find('#LongDiskSize').val();
							appDiskMonthly(
								self.tenantName,
								self.serviceAlias,
								diskSize,
								monthNum
							).done(function(data){
								form.destroy();
								dialog.destroy();
								form = dialog = null;
								self.getInitData();
							})
					},
					//当包月条长度变化时
					'#LongDisk input': function() {
						if(!choosable){
							return;
						}
						var $wrap = dialog.getElement();
						needPay = (unitMoney * $wrap.find('#LongDisk').val() * $wrap.find('#LongDiskSize').val()).toFixed(2);
	                	$('#LongDiskText').html($wrap.find('#LongDisk').val())
	                	$("#LongDiskMoney").html(needPay);
					},
					//硬盘大小变化时
					'#LongDiskSize input': function() {
						var $wrap = dialog.getElement();
						if(!choosable){
							needPay = (unitMoney * $wrap.find('#LongDiskSize').val()).toFixed(2);
						}else{
							needPay = (unitMoney * $wrap.find('#LongDiskSize').val() * $wrap.find('#LongDisk').val()).toFixed(2);
						}
						
						$("#LongDiskMoney").html(needPay);
						$('#DiskSizeText').html($wrap.find('#LongDiskSize').val())
					}
				}
			})

			//按是否可以选择时长来隐藏显示form表单的某项
			if(choosable) {
				form.hideInput('monthInfo');
			}else{
				form.hideInput('monthInput');
			}
		},
		//硬盘包月
		handleDiskMonthly: function() {
			var self = this;
			getDiskMonthlyInfo(
				this.tenantName,
				this.serviceAlias
			).done(function(data){
				self.showDiskMonthlyDialog(data, data.choosable);

			})
		},
		//显示增加包月时长弹框
		showMonthlyAddTimeDialog: function(data) {
			var self = this;
			//内存包月一个月多少钱
			var oneMonthMoney = data.oneMonthMoney;
			//最后需要付款的钱
			var needPay = oneMonthMoney;
			var form = widget.create('form', {
				rowNum: 1,
				labelCol: 3,
				items:[{
					label: '包月时长',
					type: 'info',
					value: '<input type="range" min="1" max="24" step="1" id="TimeLong" value="1" style="display:inline-block;width:60%"><span><cite id="TimeLongText" class="text-success">1</cite>个月</span>'
				},{
					label: '费用总计',
					type: 'info',
					value: '<div><span id="TimeLongMoney" class="text-success">'+oneMonthMoney+'</span>元（按所有包月项目同步增加时长计算）</div>'
				}]
			})
			var dialog = widget.create('dialog', {
				title: '增加包月时长',
				content: form.getElement(),
				height:'300px',
				btns:[{
					classes: 'btn btn-success',
					text: '确认付款'
				},{
					classes: 'btn btn-default btn-cancel',
					text: '取消'
				}],
				domEvents: {
					//点击确认付款按钮
					'.btn-success click': function() {
						var monthNum = dialog.getElement().find('#TimeLong').val();
						appMonthlyAddTime(
							self.tenantName,
							self.serviceAlias,
							monthNum
						).done(function(data){
							form.destroy();
							dialog.destroy();
							form = dialog = null;
							self.getInitData();
						})
					},
					//当包月条长度变化时
					'#TimeLong input': function (){
						needPay = (dialog.getElement().find('#TimeLong').val() * oneMonthMoney).toFixed(2);
	                	$("#TimeLongMoney").html(needPay);
	                	$('#TimeLongText').html(dialog.getElement().find('#TimeLong').val());
					}
				}
			})
		},
		//增加包月时长
		handleMonthlyAddTime: function() {
			var self = this;
			getAppMonthlyInfo(
				this.tenantName,
				this.serviceAlias
			).done(function(data){
				self.showMonthlyAddTimeDialog(data);
			})
		}
	},
	domEvents: {
		//内存包月
		'.memoryMonthly click': function() {
			this.handleMemoryMonthly();
		},
		//内存包月增加时长
		'.monthlyAddTime click': function() {
			this.handleMonthlyAddTime();
		},
		//内存包月扩容
		'.memoryExpansion click': function() {
			this.handleMemoryExpansion();
		},
		//硬盘包月
		'.diskMonthly click': function() {
			this.handleDiskMonthly();
		}
	},
	onReady: function(){
		this.renderData.tenantName = this.tenantName;
		this.renderData.serviceAlias = this.serviceAlias;
		this.getInitData();
	}
})

window.AppPayController = AppPay;
export default AppPay;