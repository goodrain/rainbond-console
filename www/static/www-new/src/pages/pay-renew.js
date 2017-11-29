import createPageController from '../utils/page-controller';
import widget from '../ui/widget';
import PayAppADT from '../utils/payAppADT-util';
import { 
	appBatchRenew,
	appBatchMemoryWithoutTime,
	appBatchMemoryWitTime,
	appBatchDiskWithoutTime,
	appBatchDiskWithTime
} from '../comms/app-apiCenter';
const Msg = widget.Message;
require('./pay-renew.css');
require('../components/appMemoryMonthly');
require('../components/appDiskMonthly');
require('../components/appMonthlyAddTime');
require('../components/appMemoryExpansion');
require('../components/monthly-time-select');
var template = require('./pay-renew-tpl.html');






const PayController  = createPageController({
	template: template,
	property:{
		//列表类型 1:全部 2:续费 3:内存包月设置时间 4:内存包月直接续费 5:硬盘包月设置时间  6:硬盘包月直接续费
		listType:'1',
		//保存列表对象
		dataList:null,
		//费用总计
		totalMoney:0,
		tenantName: '',
		renderData:{}
	},
	method:{
		//根据状态更新大的dom
		updateDomByMenuType:function(){
			//更新menu状态 start
			this.$wrap.find('.top-level').removeClass('active');
			this.$wrap.find('[menu-type='+this.listType+']').closest('.top-level').addClass('active');
			this.$wrap.find('.selected-text').html('');

			if(this.listType == '3'){
				this.$wrap.find('.memory-selected-text').html(':选择时长');
			}else if(this.listType == '4'){
				this.$wrap.find('.memory-selected-text').html(':不选择时长');
			}

			if(this.listType == '5'){
				this.$wrap.find('.disk-selected-text').html(':选择时长');
			}else if(this.listType == '6'){
				this.$wrap.find('.disk-selected-text').html(':不选择时长');
			}
			//更新menu状态 end



			//更新range 和 提交按钮、金额显示隐藏
			this.$wrap.find('.total-money-wrap span').html("0");
			this.timeSelect.setValue(1);
			this.$wrap.find('[name=disk-range]').val(1);
			this.$wrap.find('.disk-result').html(1);

			if(this.listType === '1'){
				this.$wrap.find('.money-row').hide();
				this.$wrap.find('.diskRange-row').hide();
				this.$wrap.find('.dateRange-row').hide();
				this.$wrap.find('.btns-row').hide();
				this.$wrap.find('.pay-renew-form').hide();
			}else if(this.listType == '2') {
				this.$wrap.find('.money-row').show();
				this.$wrap.find('.btns-row').show();
				this.$wrap.find('.diskRange-row').hide();
				this.$wrap.find('.dateRange-row').show();
				this.$wrap.find('.submit-memory-month').hide();
				this.$wrap.find('.submit-disk-month').hide();
				this.$wrap.find('.submit-renew').show();
			}else if(this.listType == '3' || this.listType == '4'){
				this.$wrap.find('.money-row').show();
				this.$wrap.find('.btns-row').show();
				this.$wrap.find('.diskRange-row').hide();
				this.$wrap.find('.submit-memory-month').show();
				this.$wrap.find('.submit-disk-month').hide();
				this.$wrap.find('.submit-renew').hide();

				if(this.listType == '3'){
					this.$wrap.find('.dateRange-row').show();
				}else{
					this.$wrap.find('.dateRange-row').hide();
				}

			}else if(this.listType == '5' || this.listType == '6') {
				this.$wrap.find('.money-row').show();
				this.$wrap.find('.btns-row').show();
				this.$wrap.find('.submit-memory-month').hide();
				this.$wrap.find('.submit-disk-month').show();
				this.$wrap.find('.submit-renew').hide();
				this.$wrap.find('.diskRange-row').show();

				if(this.listType == '5'){
					this.$wrap.find('.dateRange-row').show();
				}else{
					this.$wrap.find('.dateRange-row').hide();
				}
			}
		},
		createList:function(){
			if(this.dataList) {
				this.dataList.destroy();
			}

			var self = this;

			//全部列表
			if(this.listType == '1') {
				this.dataList = widget.create('tableList', {
					url:'/apps/'+this.tenantName+'/service-renew/',
					renderTo:this.$wrap.find('.list-wrap'),
					selectable: false,
					toCustomData: function(data){
						return new PayAppADT(data);
					},
					columns:[{
						name:'name',
						text: '应用名称'
					},{
						name:'memory',
						text: '内存'
					},{
						name: 'disk',
						text: '硬盘'
					},{
						name: 'endDate',
						text: '截止日期'
					},{
						name: 'action',
						text: '操作'
					}],
					render:{
						name: function(text, data, index, customData){
							return customData.getAppName();
						},
						memory: function(text, data, index, customData){
							var html = customData.getTotalMemory(true);
							if(customData.isMemoryPayed()){
								html += ' <span class="status-tip">包</span>'
							}
							return html;
						},
						disk: function(text, data, index, customData) {
							var html = customData.getDisk(true);
							if(customData.isDiskPayed()){
								html += ' <span class="status-tip">包</span>'
							}
							return html;
						},
						endDate: function(text, data, index, customData){
							return customData.getEndDate();
						},
						action: function(text, data, index, customData){
							var html = [];
							if(!customData.isMemoryPayed()){
								html.push('<button class="buy-memory btn btn-default" href="javascript:;">内存购买包月</button>');
							}

							if(customData.canAddMemoryDate() || customData.canAddDiskDate()){
								html.push('<button class="add-date btn btn-default" href="javascript:;">增加时长</button>');
							}

							if(customData.canAddMemorySize()){
								html.push('<button class="memory-add-size btn btn-default" href="javascript:;">内存增加额度</button>');
							}

							if(!customData.isDiskPayed()){
								html.push('<button class="buy-disk btn btn-default" href="javascript:;">磁盘购买包月</button>');
							}

							if(customData.canAddDiskSize()){
								html.push('<button class="disk-add-date btn btn-default" href="javascript:;">磁盘增加额度</button>');
							}
							return html.join('');
						}
					}
				})
			}

			//批量续费列表
			if(this.listType == '2'){
				this.dataList = widget.create('tableList', {
					url:'/apps/'+this.tenantName+'/service-renew/',
					queryFunction:function(){
						return {
							action: 'batch'
						}
					},
					renderTo:this.$wrap.find('.list-wrap'),
					selectable: true,
					toCustomData: function(data){
						return new PayAppADT(data);
					},
					columns:[{
						name:'name',
						text: '应用名称'
					},{
						name:'memory',
						text: '内存'
					},{
						name: 'disk',
						text: '硬盘'
					},{
						name: 'endDate',
						text: '截止日期'
					}],
					event: {
						onLoaded: function(){
							self.$wrap.find('.pay-renew-form').show();
						},
						onEmpty:[function(){
							self.$wrap.find('.pay-renew-form').hide();
						}],
						//当选择变化时
						onSelectedChange:[function(){
							self.updateTotalMoney();
						}]
					},
					render:{
						name: function(text, data, index, customData){
							return customData.getAppName();
						},
						memory: function(text, data, index, customData){
							return customData.getTotalMemory(true);
						},
						disk: function(text, data, index, customData) {
							return customData.getDisk(true);
						},
						endDate: function(text, data, index, customData){
							return customData.getEndDate();
						}
					}
				})
			}

			//选择时长内存包月
			if(this.listType == '3'){
				this.dataList = widget.create('tableList', {
					url:'/apps/'+this.tenantName+'/service-renew/',
					queryFunction:function(){
						return {
							action: 'batch-memory',
							type:'postpaid_disk'
						}
					},
					renderTo:this.$wrap.find('.list-wrap'),
					selectable: true,
					toCustomData: function(data){
						return new PayAppADT(data);
					},
					columns:[{
						name:'name',
						text: '应用名称'
					},{
						name:'memory',
						text: '使用内存'
					}],
					event: {
						onLoaded: function(){
							self.$wrap.find('.pay-renew-form').show();
						},
						onEmpty:[function(){
							self.$wrap.find('.pay-renew-form').hide();
						}],
						//当选择变化时
						onSelectedChange:[function(){
							self.updateTotalMoney();
						}]
					},
					render:{
						name: function(text, data, index, customData){
							return customData.getAppName();
						},
						memory: function(text, data, index, customData){
							return customData.getTotalMemory(true);
						}
					}
				})
			}


			//不选择时长内存包月
			if(this.listType == '4'){
				this.dataList = widget.create('tableList', {
					url:'/apps/'+this.tenantName+'/service-renew/',
					queryFunction:function(){
						return {
							action: 'batch-memory',
							type:'prepaid_disk'
						}
					},
					renderTo:this.$wrap.find('.list-wrap'),
					selectable: true,
					toCustomData: function(data){
						return new PayAppADT(data);
					},
					columns:[{
						name:'name',
						text: '应用名称'
					},{
						name:'memory',
						text: '使用内存'
					},{
						name: 'disk',
						text: '硬盘'
					}],
					event: {
						onLoaded: function(){
							self.$wrap.find('.pay-renew-form').show();
						},
						onEmpty:[function(){
							self.$wrap.find('.pay-renew-form').hide();
						}],
						//当选择变化时
						onSelectedChange:[function(){
							self.updateTotalMoney();
						}]
					},
					render:{
						name: function(text, data, index, customData){
							return customData.getAppName();
						},
						memory: function(text, data, index, customData){
							return customData.getTotalMemory(true);
						},
						disk: function(text, data, index, customData) {
							return customData.getDisk(true);
						}
					}
				})
			}

			//选择时长磁盘包月
			if(this.listType == '5'){
				this.dataList = widget.create('tableList', {
					url:'/apps/'+this.tenantName+'/service-renew/',
					queryFunction:function(){
						return {
							action: 'batch-disk',
							type:'postpaid_memory'
						}
					},
					renderTo:this.$wrap.find('.list-wrap'),
					selectable: true,
					toCustomData: function(data){
						return new PayAppADT(data);
					},
					columns:[{
						name:'name',
						text: '应用名称'
					},{
						name:'memory',
						text: '使用内存'
					}],
					event: {
						onLoaded: function(){
							self.$wrap.find('.pay-renew-form').show();
						},
						onEmpty:[function(){
							self.$wrap.find('.pay-renew-form').hide();
						}],
						//当选择变化时
						onSelectedChange:[function(){
							self.updateTotalMoney();
						}]
					},
					render:{
						name: function(text, data, index, customData){
							return customData.getAppName();
						},
						memory: function(text, data, index, customData){
							return customData.getTotalMemory(true);
						}
					}
				})
			}

			//不选择时长磁盘包月
			if(this.listType == '6'){
				this.dataList = widget.create('tableList', {
					url:'/apps/'+this.tenantName+'/service-renew/',
					queryFunction:function(){
						return {
							action: 'batch-disk',
							type:'prepaid_memory'
						}
					},
					renderTo:this.$wrap.find('.list-wrap'),
					selectable: true,
					toCustomData: function(data){
						return new PayAppADT(data);
					},
					columns:[{
						name:'name',
						text: '应用名称'
					},{
						name:'memory',
						text: '使用内存'
					}],
					event: {
						onLoaded: function(){
							self.$wrap.find('.pay-renew-form').show();
						},
						onEmpty:[function(){
							self.$wrap.find('.pay-renew-form').hide();
						}],
						//当选择变化时
						onSelectedChange:[function(){
							self.updateTotalMoney();
						}]
					},
					render:{
						name: function(text, data, index, customData){
							return customData.getAppName();
						},
						memory: function(text, data, index, customData){
							return customData.getTotalMemory(true);
						}
					}
				})
			}
		},
		
		setListType:function(type){
			this.listType = type;
		},
		//获取批量续费总的金额
		getTotalMoney:function(){

			if(this.listType == '2' || this.listType == '3') {
				var monthNum = this.timeSelect.getValue();
				var needMoneys = this.dataList.getSelectedArrayByKey('need_money');
				var totalOneMonthMoney = 0, totalMoney = 0;
				for(var i=0;i<needMoneys.length;i++){
					totalOneMonthMoney += Number(needMoneys[i]);
				}
				totalMoney = totalOneMonthMoney * 24 * 30 * monthNum;
				return totalMoney.toFixed(2);
			}

			if(this.listType == '4') {
				var needMoneys = this.dataList.getSelectedArrayByKey('need_money');
				var totalOneMonthMoney = 0, totalMoney = 0;
				for(var i=0;i<needMoneys.length;i++){
					totalOneMonthMoney += Number(needMoneys[i]);
				}
				totalMoney = totalOneMonthMoney * 24 * 30;
				return totalMoney.toFixed(2);
			}

			if(this.listType == '5') {
				var len = this.dataList.getSelected().length;
				if(len == 0){
					return 0;
				}

				var diskOneHourMoney = this.dataList.getSelected()[0]['unit_disk_fee'] * 24 * 30;
				var monthNum = this.timeSelect.getValue();
				var disk = this.$wrap.find('[name=disk-range]').val();
				var totalMoney = diskOneHourMoney * len * monthNum * disk;
				return totalMoney.toFixed(2);
			}
			

			if(this.listType == '6') {
				var selected = this.dataList.getSelected(), totalMoney = 0;
				var disk = this.$wrap.find('[name=disk-range]').val();
				for(var i=0;i<selected.length;i++){
					totalMoney += (selected[i]['unit_disk_fee'] * selected[i]['hours']);
				}
				totalMoney = totalMoney * disk;
				return totalMoney.toFixed(2);

			}
		},
		//更新批量续费金额
		updateTotalMoney:function(){
			this.$wrap.find('.total-money-wrap span').html(this.getTotalMoney());
		},
		handleBatchMemory: function(){
			if(this.listType == '3') {
				var selectedIds = this.dataList.getSelectedArrayByKey('service_id');
				var monthNum = this.timeSelect.getValue();
				return appBatchMemoryWitTime(
					this.tenantName,
					selectedIds,
					monthNum
				)
			}

			if(this.listType == '4') {
				var selectedIds = this.dataList.getSelectedArrayByKey('service_id');
				return appBatchMemoryWithoutTime(
					this.tenantName,
					selectedIds
				)
			}
		},
		handleBatchDisk: function(){
			if(this.listType == '5') {
				var selectedIds = this.dataList.getSelectedArrayByKey('service_id');
				var monthNum = this.timeSelect.getValue();
				var disk = this.$wrap.find('[name=disk-range]').val();
				return appBatchDiskWithTime(
					this.tenantName,
					selectedIds,
					disk,
					monthNum
				)
			}

			if(this.listType == '6') {
				var selectedIds = this.dataList.getSelectedArrayByKey('service_id');
				var disk = this.$wrap.find('[name=disk-range]').val();
				return appBatchDiskWithoutTime(
					this.tenantName,
					selectedIds,
					disk
				)
			}
		}
	},
	domEvents:{
		//按钮切换
		'[menu-type] click': function(e){
			var type = $(e.currentTarget).attr('menu-type');
			if(type){
				this.setListType(type);
				this.createList();
				this.updateDomByMenuType();
				this.$wrap.find('.empty-info').hide();
			}
		},
		//增加包月时长
		'.add-date click': function(e){
			var uid = $(e.currentTarget).parents('.list_item').attr('uid');
			var data = this.dataList.getDataByuid(uid);
			if(data){
				this.handleMonthlyAddTime(new PayAppADT(data));
			}
		},
		//内存包月
		'.buy-memory click': function(e) {
			var self = this;
			var uid = $(e.currentTarget).parents('.list_item').attr('uid');
			var data = this.dataList.getDataByuid(uid);
			if(data){
				var appADT = new PayAppADT(data);
				widget.create('appMemoryMonthly', {
					tenantName: appADT.getTenantName(),
					serviceAlias: appADT.getAppAlias(),
					onSuccess:function(){
						self.dataList.reload();
					}
				})
			}
		},
		//磁盘包月
		'.buy-disk click': function(e){
			var self = this;
			var uid = $(e.currentTarget).parents('.list_item').attr('uid');
			var data = this.dataList.getDataByuid(uid);
			if(data){
				var appADT = new PayAppADT(data);
				widget.create('appDiskMonthly', {
					tenantName: appADT.getTenantName(),
					serviceAlias: appADT.getAppAlias(),
					onSuccess:function(){
						self.dataList.reload();
					}
				})
			}
		},
		//增加时长
		'.add-date click': function(e) {
			var self = this;
			var uid = $(e.currentTarget).parents('.list_item').attr('uid');
			var data = this.dataList.getDataByuid(uid);
			if(data){
				var appADT = new PayAppADT(data);
				widget.create('appMonthlyAddTime', {
					tenantName: appADT.getTenantName(),
					serviceAlias: appADT.getAppAlias(),
					onSuccess:function(){
						self.dataList.reload();
					}
				})
			}
		},
		//内存扩容
		'.memory-add-size click': function(e){
			
			var self = this;
			var uid = $(e.currentTarget).parents('.list_item').attr('uid');
			var data = this.dataList.getDataByuid(uid);
			if(data){
				var appADT = new PayAppADT(data);
				widget.create('appMemoryExpansion', {
					tenantName: appADT.getTenantName(),
					serviceAlias: appADT.getAppAlias(),
					onSuccess:function(){
						self.dataList.reload();
					}
				})
			}
		},
		//批量续费确认付款
		'.submit-renew click': function(e){
			var self = this;
			var selectedIds = this.dataList.getSelectedArrayByKey('service_id');
			if(!selectedIds.length){
				Msg.warning('请选择要续费的应用');
				return;
			}
			var monthNum = this.timeSelect.getValue();
			var totalMoney = this.getTotalMoney();
			var confirm = widget.create('confirm', {
				title: '批量续费',
				content: '费用总计: '+totalMoney+' 元<br /> 确认批量续费吗？',
				event: {
					onOk:function(){
						appBatchRenew(
							self.tenantName,
							selectedIds,
							monthNum
						).done(function(data){
							confirm.destroy();
							self.dataList.reload();
							self.updateTotalMoney();
						})
					}
				}
			})
		},
		//内存包月
		'.submit-memory-month click': function(){
			var self = this;
			var selectedIds = this.dataList.getSelectedArrayByKey('service_id');
			if(!selectedIds.length){
				Msg.warning('请选择要包月的应用');
				return;
			}
			var totalMoney = this.getTotalMoney();
			var confirm = widget.create('confirm', {
				title: '内存包月',
				content: '费用总计: '+totalMoney+' 元<br /> 确认包月吗？',
				event: {
					onOk:function(){
						self.handleBatchMemory().done(function(){
							confirm.destroy();
							self.dataList.reload();
							self.updateTotalMoney();
						})
					}
				}
			})

		},
		//硬盘包月
		'.submit-disk-month click': function(){
			var self = this;
			var selectedIds = this.dataList.getSelectedArrayByKey('service_id');
			if(!selectedIds.length){
				Msg.warning('请选择要包月的应用');
				return;
			}

			var totalMoney = this.getTotalMoney();
			var confirm = widget.create('confirm', {
				title: '磁盘包月',
				content: '费用总计: '+totalMoney+' 元<br /> 确认包月吗？',
				event: {
					onOk:function(){
						self.handleBatchDisk().done(function(){
							confirm.destroy();
							self.dataList.reload();
							self.updateTotalMoney();
						})
					}
				}
			})
		},
		//监听磁盘range
		'[name=disk-range] input': function(e) {
			var val = $(e.currentTarget).val();
			this.$wrap.find('.disk-result').html(val);
			this.updateTotalMoney();
		}
	},
	onReady:function (){
		var self = this;
		this.render();
		setTimeout(() => {
			//创建时长选择器
			this.timeSelect = widget.create('monthly-time-select', {
				onChange: function(){
					self.updateTotalMoney();
				}
			})
			this.$wrap.find('.date-select').html(this.timeSelect.getElement());
			this.updateDomByMenuType();
			this.createList();
		})
		
		

	}
})

window.PayController = PayController;
export default PayController;
