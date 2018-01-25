import createPageController from '../utils/page-controller';
import {
	getAppInfo,
	openAppInner,
	closeAppInner,
	openAppOuter,
	closeAppOuter,
	addPort,
	editPort,
	editProtocol,
	editPortAlias,
	addDomain,
	delDomain,
	delAppPort,
	loadPortUrl
} from '../comms/app-apiCenter';
import {
	getPagePortAppData
} from '../comms/page-app-apiCenter';

import widget from '../ui/widget';
import bindDomain from '../components/bind-domain';
const Msg = widget.Message;
const template = require('./app-port-tpl.html');




const createAddPortTmp = () => {
	return $('#createPortTmp').html();  
}

const createDomainTmp = (domain) => {
	var html = '<p js-data-domain="'+domain+'">'+
       				'<span>'+domain+'</span>'+
       				'<a style="margin-left:10px;" href="javascript:;" data-domain="'+domain+'" class="delDomain">解绑</button>'+
       			'</p>';
    return html;
}


/* 业务逻辑控制器 */
const AppPort = createPageController({
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
			var self = this;
			getAppInfo(
				this.tenantName,
				this.serviceAlias
			).done((appInfo) => {
				this.renderData.appInfo = appInfo;
				getPagePortAppData(
					this.tenantName,
					this.serviceAlias
				).done((pageData) => {
					this.renderData.pageData = pageData;

					this.render();
					setTimeout(() => {
						//加载端口url信息
						$(".port-table").each(function(){
						   var $table = $(this);
				           var port = $table.attr('js-port');
				           var protocol = $table.attr('js-protocol');
				           if(port && protocol) {
				           	   self.loadPortUrl(port, protocol)
				           }
				      	});
					})
				})
			})
		},
		//获取应用端口的outerUrl 和 innerUrl
		loadPortUrl: function(port, protocol) {
			loadPortUrl(
				this.tenantName,
				this.serviceAlias,
				port, protocol
			).done(function(data) {
				$("#sever_show_" + port).find("span").html(data.jsInnerUrl || '-');
				$("#port_show_" + port).find("a").html(data.jsOuterUrl || '-').attr("href",data.jsOuterHerf);
			})
		},
		handleAddPort: function(port, protocol){
			var self = this;
			return addPort(
				this.tenantName,
				this.serviceAlias,
				port, protocol
			).done(function(res){
				 self.getInitData();
			})
		},
		sowEidtPortDialog: function(port) {
			var self = this;
			var form = widget.create('form', {
				hideLabel: true,
				items:[{
					name: 'port',
					type: 'text',
					value: port,
					label: '端口'
				}]
			})

			var dialog = widget.create('dialog', {
				title: '修改端口 ',
				width: '400px',
				height: '200px',
				domEvents:{
					'.btn-success click': function(){
						var newPort = form.getValue('port');
						if(newPort == port){
							form.destroy();
							dialog.destroy();
							form = dialog = null;
							return;
						}
						if(self.checkPort(newPort)){
							editPort(
								self.tenantName,
								self.serviceAlias,
								port,
								newPort
							).done(function(){
								form.destroy();
								dialog.destroy();
								self.getInitData();
							})
						}
					}
				},
				event: {
					'onCancel': function() {
						form.destroy();
						form = dialog = null;
					}
				}
			})
			dialog.setContent(form.getElement());

		},
		sowEidtProtocolDialog: function(port, protocol) {
			var self = this;
			var form = widget.create('form', {
				hideLabel: true,
				items:[{
					name: 'protocol',
					type: 'select',
					value: protocol,
					items: [{
						text: 'http',
						value: 'http'
					},{
						text: 'tcp',
						value: 'tcp'
					},
					{
						text: 'udp',
						value: 'udp'
					},
					{
						text: 'mysql',
						value: 'mysql'
					}],
					label: '协议'
				}]
			})

			var dialog = widget.create('dialog', {
				title: '修改协议 ',
				width: '400px',
				height: '200px',
				domEvents:{
					'.btn-success click': function(){
						var newProtocol = form.getValue('protocol');

						if(newProtocol === protocol) {
							form.destroy();
							dialog.destroy();
							form = dialog = null;
						}else{
							editProtocol(
								self.tenantName,
								self.serviceAlias,
								port, newProtocol
							).done(function(){
								form.destroy();
								dialog.destroy();
								form = dialog = null;
								self.getInitData();
							})
						}
					}
				},
				event: {
					'onCancel': function() {
						form.destroy();
						form = dialog = null;
					}
				}
			})
			dialog.setContent(form.getElement());
		},
		sowEidtPortAliasDialog: function(port, portAlias) {
			var self = this;
			var form = widget.create('form', {
				hideLabel: true,
				items:[{
					name: 'portAlias',
					type: 'text',
					value: portAlias,
					label: '别名'
				}]
			})

			var dialog = widget.create('dialog', {
				title: '修改别名 ',
				width: '400px',
				height: '200px',
				domEvents:{
					'.btn-success click': function(){
						var newPortAlias = form.getValue('portAlias');
						if(newPortAlias === portAlias) {
							form.destroy();
							dialog.destroy();
							form = dialog = null;
						}else{
							editPortAlias(
								self.tenantName,
								self.serviceAlias,
								port, newPortAlias
							).done(function(){
								form.destroy();
								dialog.destroy();
								form = dialog = null;
								self.getInitData();
							})
						}
					}
				},
				event: {
					'onCancel': function() {
						form.destroy();
						form = dialog = null;
					}
				}
			})
			dialog.setContent(form.getElement());
		},
		checkPort: function(value){
			value = value || '';
			if(!(/^[0-9]+$/.test(value))){
				Msg.warning("端口必须为数字!");
				return;
			}

			if(this.language === 'docker' || this.language === 'docker-image' || this.language === 'docker-compose'){

				if(!(value>=1 && value<=65535)){
				  Msg.warning("端口号必须在0~65535之间！");
                  return false;
                }

			}else{
				if(!(value>=1025 && value<=65535)){
				   Msg.warning("端口号必须在1025~65535之间！");
                   return false;
                }
			}
            return true;
		},
		handleDelDomain: function(port, doMain){
			return delDomain(
				this.tenantName,
				this.serviceAlias,
				this.serviceId,
				port,
				doMain
			)
		},
		showDelDomainConfirm: function(port, doMain) {
			var self = this;
			if(doMain.indexOf("//") > -1){
		        doMain = doMain.split("//")[1];
		    }
			
			var confirm = widget.create('confirm', {
				title: '解绑域名',
				content: '确定要解绑 '+doMain +' 域名吗?',
				event:{
					onOk: function(){
						self.handleDelDomain(port, doMain).done(function(){
							confirm.destroy();
							confirm = null;
							self.getInitData();
						})
					}
				}
			})
		},
		handleAddDomain: function(port, domain) {
			return addDomain(
				this.tenantName,
				this.serviceAlias,
				this.serviceId,
				port, domain
			)
		},
		showAddDomainDialog: function(port) {
			var self = this;
			var dialog = widget.create('bindDomain', {
				tenantName: this.tenantName,
				serviceAlias: this.serviceAlias,
				serviceId: this.serviceId,
				port: port,
				onSuccess: function(protocol, domain) {
					$('.domain-box').each(function(){
						if($(this).attr('port') === port){
							$(this).append(createDomainTmp(domain));
						}
					})
				}
			})
		},
		handleDelPort: function(port) {
			return delAppPort(
				this.tenantName,
				this.serviceAlias,
				port
			).done(function(){
				Msg.success('操作成功');
			})
		},
		showDelPortConfirm: function(port){
			var self = this;
			var confirm = widget.create('confirm', {
				title: '应用端口删除',
				content: '<h3>确定要删除此端口 '+port+' 吗？</h3>',
				event: {
					onOk: function(){
						self.handleDelPort(port).done(function(){
							$('table[js-port='+port+']').remove();
							confirm.destroy();
						})
					}
				}
			})
		},
		handlePortInnerOpen: function(port) {
			var self = this;
			openAppInner(
				this.tenantName,
				this.serviceAlias,
				port
			).done(function(data){
				self.getInitData();
			}).fail(function(){
			    self.getInitData();
			})
		},
		handlePortInnerClose: function(port) {
			var self = this;
			closeAppInner(
				this.tenantName,
				this.serviceAlias,
				port
			).done(function(data){
				self.getInitData();
			}).fail(function(){
				self.getInitData();
			})
		},
		handlePortOuterOpen: function(port) {
			var self = this;
			openAppOuter(
				this.tenantName,
				this.serviceAlias,
				port
			).done(function(data){
				self.getInitData();
			}).fail(function(){
				self.getInitData();
			})
		},
		handlePortOuterClose: function(port) {
			var self = this;
			closeAppOuter(
				this.tenantName,
				this.serviceAlias,
				port
			).done(function(data){
				self.getInitData();
			}).fail(function(){
				self.getInitData();
			})
		}
	},
	domEvents:{
		//新增服务端口事件
		'#add_service_port click': function(e) {
			$("#create-port-wrap").append(createAddPortTmp());
		},
		//删除新增端口条目
		'.port-cancel click': function(e) {
			$(e.currentTarget).closest('.port-open').remove();
		},
		//新增端口提交事件
		'.port-save click': function(e) {
			var $form = $(e.currentTarget).closest('form');
			var port = $form.find('[name=port_port]').val();
			var protocol = $form.find('[name=port_protocol]').val();
			if(this.checkPort(port)){
				this.handleAddPort(port, protocol)
			}
		},
		//端口删除
		'.port-delete click': function(e) {
			var port = $(e.currentTarget).parents('.port-table').attr('js-port');
			if(port) {
				this.showDelPortConfirm(port);
			}
		},
		//修改端口
		'.js-edit-port click': function(e) {
			var $target = $(e.currentTarget);
			var port = $target.closest('.port-table').attr('js-port');
			if(port) {
				this.sowEidtPortDialog(port);
			}
		},
		//修改协议
		'.js-edit-protocol click': function(e) {
			var $target = $(e.currentTarget);
			var port = $target.closest('.port-table').attr('js-port');
			var protocol = $target.closest('.port-table').attr('js-protocol');
			if(port) {
				this.sowEidtProtocolDialog(port, protocol);
			}
		},
		//修改端口别名
		'.js-edit-port-alias click': function(e) {
			var $target = $(e.currentTarget);
			var portAlias = $target.closest('.port-table').attr('port-alias');
			var port = $target.closest('.port-table').attr('js-port');
			if(port && portAlias) {
				this.sowEidtPortAliasDialog(port, portAlias);
			}
		},
		//解绑域名事件
		'.delDomain click': function(e) {
			var $target = $(e.currentTarget);
			var port = $target.closest('.port-table').attr('js-port');
			var doMain = $target.attr('data-domain');
			if(doMain) {
				this.showDelDomainConfirm(port, doMain);
			}
		},
		//新增绑定域名事件
		'.fn-bind-domain click': function(e) {
			var $target = $(e.currentTarget);
			var port = $target.closest('.port-table').attr('js-port');
			if(port) {
				this.showAddDomainDialog(port);
			}
		},
		//对外服务开关事件
		'.port-inner-open click': function(e) {
			var $target = $(e.currentTarget);
			var port = $target.closest('.port-table').attr('js-port');
			this.handlePortInnerOpen(port);
		},
		//对外服务开关事件
		'.port-inner-close click': function(e) {
			var $target = $(e.currentTarget);
			var port = $target.closest('.port-table').attr('js-port');

			this.handlePortInnerClose(port);
			
		},
		//对外访问开关事件
		'.port-outer-open click': function(e) {
			var $target = $(e.currentTarget);
			var port = $target.closest('.port-table').attr('js-port');

			this.handlePortOuterOpen(port);
			
		},
		//对外访问开关事件
		'.port-outer-close click': function(e) {
			var $target = $(e.currentTarget);
			var port = $target.closest('.port-table').attr('js-port');
			this.handlePortOuterClose(port);
			
		}

	},
	onReady: function(){
		this.renderData.tenantName = this.tenantName;
		this.renderData.serviceAlias = this.serviceAlias;
		this.getInitData();
		
	}
})

window.AppPortController = AppPort;
export default AppPort;