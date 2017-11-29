import createPageController from '../utils/page-controller';
import { 
	addAutoExtendRule,
	delAutoExtendRule,
	openAutoExtendRule,
	closeAutoExtendRule,
	appUpgradeType,
	appUpgradePodNum,
	appUpgradeMemory,
	changeGroup,
	editInfo,
	getAutoExtendRule,
	getAppInfo
} from '../comms/app-apiCenter';
import {
	getPageExpansionAppData
} from '../comms/page-app-apiCenter';

import widget from '../ui/widget';
import validationUtil from '../utils/validationUtil';
var  template = require('./app-expansion-tpl.html');

const Msg = widget.Message;

const createRuleTmp = (data) => {
	var html = [], index=1;
	for(var id in data){
		var tr = "<tr data-id='"+id+"'>";
		tr += "<td>" + index + "</td>";
		tr += "<td>" + data[id].statuscn + "</td>";
		tr += "<td>" + data[id].count + "</td>";
		tr += "<td>"+data[id].desc+"</td>";
		tr += "<td class='text-right'><button class='btn btn-default btn-sm delRule'>删除</button>";
		if (data[id].status) {
            tr +=  "<button style=' margin-left:15px;' class='btn btn-default btn-sm closeRule'>关闭</button>"
        } else {
            tr +=  "<button style=' margin-left:15px;' class='btn btn-success btn-sm openRule'>开启</button>"
        }
        tr += '<td>'
        tr+='</tr>';
        index ++;
        html.push(tr);
	}
	return html.join('');
}



/* 业务逻辑控制器 */
const AppExpansion = createPageController({
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
			pageData:null,
			appInfo: null,
			tenantName:'',
			serviceAlias:''
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
				getPageExpansionAppData(
					this.tenantName,
					this.serviceAlias
				).done((pageData) => {
					this.renderData.pageData = pageData;
					this.render();
					setTimeout(() => {
						//加载自动伸缩规则信息
						this.loadRuleData();
					})
					
				})
			})
		},
		//加载自动伸缩规则列表
		loadRuleData:function() {
			getAutoExtendRule(
				this.tenantName,
				this.serviceAlias
			).done(function(data){
				
				$("#ruleBody").html(createRuleTmp(data));
			})
		},
		//验证自动伸缩规则数据
		checkRuleData: function(data) {
			var min = data.minvalue;
			var max = data.maxvalue;
			if(!validationUtil.valid('zzs', min) || !validationUtil.valid('zzs', max)){
				Msg.warning("大于和小于的值只能为正整数，请检查后重试");
				return false;
			}


			if(parseInt(min) > parseInt(max)){
				Msg.warning("大值不能小于小值，请检查后重试");
				return false;
			}

			return true;
		},
		handleAddAutoExtendRule: function(data){
			if(!this.checkRuleData(data)) return;
			addAutoExtendRule(
				this.tenantName,
				this.serviceAlias,
				data
			).done((data) => {
				this.loadRuleData();
			})
		},
		handleDelRule: function(id){
			delAutoExtendRule(
				this.tenantName,
				this.serviceAlias,
				id
			).done(() => {
				this.loadRuleData();
			})
		},
		handleCloseRule: function(id) {
			closeAutoExtendRule(
				this.tenantName,
				this.serviceAlias,
				id
			).done(() => {
				this.loadRuleData();
			})
		},
		handleOpenRule: function(id) {
			openAutoExtendRule(
				this.tenantName,
				this.serviceAlias,
				id
			).done(() => {
				this.loadRuleData();
			})
		},
		handleAppUpgradeType: function(type) {
			appUpgradeType(
				this.tenantName,
				this.serviceAlias,
				type
			)
		},
		handleAppUpgradePodNum: function(podNum) {
			appUpgradePodNum(
				this.tenantName,
				this.serviceAlias,
				podNum
			)
		},
		handleAppUpgradeMemory: function(memory) {
			var self = this;
			var confirm = widget.create('confirm', {
				title:'内存调整提示',
				height:'250px',
				content:'<p style="color:#999;text-align:center;font-size:14px;">为保证应用访问速度及运行性能，请合理调整内存大小！<br />如调整后性能受到影响，可尝试扩容解决</p><h3>确认调整吗？</h3>',
				event:{
					onOk:function(){
						appUpgradeMemory(
							self.tenantName,
							self.serviceAlias,
							memory
						)
						confirm.destroy();
					}
				}
			})
			
		}
	},
	domEvents:{
		//新增规则事件
		'#add_rule click': function(e) {
			$("#autorole").show();
		},
		//隐藏规则表单
		'.hideRuleForm click': function(e) {
			$("#autorole").hide();
		},
		//确定添加规则表单
		'.subRule click': function(e) {
			var port = $("select[name='port']").val();
	        var item = $("select[name='item']").val();
	        var maxvalue = $("input[name='maxvalue']").val();
	        var minvalue = $("input[name='minvalue']").val();
	        var nodenum = $("select[name='nodenum']").val()

	        var data = {
	            port: port,
	            item: item,
	            maxvalue: maxvalue,
	            minvalue: minvalue,
	            nodenum: nodenum
	        }
	        this.handleAddAutoExtendRule(data);
		},
		//删除自动伸缩规则
		'.delRule click': function(e) {
			var id = $(e.currentTarget).parents('tr').attr('data-id');
			if(id){
				this.handleDelRule(id);
			}
		},
		//关闭自动伸缩规则
		'.closeRule click': function(e) {
			var id = $(e.currentTarget).parents('tr').attr('data-id');
			if(id){
				this.handleCloseRule(id);
			}
		},
		//开启自动伸缩规则
		'.openRule click': function(e) {
			var id = $(e.currentTarget).parents('tr').attr('data-id');
			if(id){
				this.handleOpenRule(id);
			}
		},
		//手动伸缩扩容方式修改事件
		'.appUpgradeType click': function(e) {
			var type = $('#extend_method').val();
			if(type) {
				this.handleAppUpgradeType(type);
			}
		},
		//手动伸缩实例数修改事件
		'.appUpgradePodNum click': function(e) {
			var podNum = $('#serviceNods').val();
			if(podNum) {
				this.handleAppUpgradePodNum(podNum)
			}
		},
		//手动伸缩内存修改事件
		'.appUpgradeMemory click': function(e) {
			var memory = $('#serviceMemorys').val();
			if(memory) {
				this.handleAppUpgradeMemory(memory)
			}
		}
	},
	onReady: function(){
		var self = this;
		this.renderData.tenantName = this.tenantName;
		this.renderData.serviceAlias = this.serviceAlias;
		this.getInitData();
	}
})

window.AppExpansionController = AppExpansion;
export default AppExpansion;