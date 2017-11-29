
/* 用户充值页面控制器 */
import createPageController from '../utils/page-controller';
import { getTenantAllAppsStatusAndMemory } from '../comms/apiCenter';
import {
	getPageUserPayData
} from '../comms/page-app-apiCenter';
import widget from '../ui/widget';

const Msg = widget.Message;
const template = require('./user-pay-tpl.html');


/* 业务逻辑控制器 */
const UserPay = createPageController({
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
			getPageUserPayData(
				this.tenantName
			).done((pageData) => {
				this.renderData.pageData = pageData;
				this.render();
				setTimeout(() => {
					this.loadPayList();
				})
			})
		},
		//加载记录
		loadPayList: function(page) {
			var curdatescope= $("#datescope").val() || 7;
			var curpagesize= $("#pageSizeScope").val() || 10;
			page = page || 1;
			$("#rechargeList").load('/ajax/'+this.tenantName+'/rechargelist?datescope='+curdatescope+'&perpage='+curpagesize+'&page='+page+'&r='+Math.random());
		},
		checkMoney: function(){
			var money = this.getMoney();
			if(money == ""){
				Msg.warning("请填写所要充值的金额");
				return false;
			}
			if(isNaN(money)){
				Msg.warning("充值金额非数值类型，请核对后再输入");
				return false;
			}
			if(Number(money) == "0"){
				Msg.warning("充值金额不能为0");
				return false;
			}
			return true;
		},
		getMoney: function() {
			return $('#recharge_money').val();
		},
		paySub: function() {
			if(this.checkMoney()){
				$("#rechargeForm").submit();
			}
		}
	},
	domEvents: {
		'.page-btn click': function(e){
			var $target = $(e.currentTarget);
			var pageNumber = $target.attr('data-page');
			this.loadPayList(pageNumber);
		},
		'.paySub click': function(e) {
			this.paySub();
		},	
		'#datescope change': function(e) {
			this.loadPayList();
		},
		'#pageSizeScope change': function(e) {
			this.loadPayList();
		}
	},
	onReady: function(){
		this.renderData.tenantName = this.tenantName;
		this.getInitData();
	}
})

window.UserPayController = UserPay;
export default UserPay;