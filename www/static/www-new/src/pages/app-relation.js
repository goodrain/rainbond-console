import createPageController from '../utils/page-controller';
import { 
	isAppEnhanced, 
	createAppRelation, 
	cancelAppRelation,
	getAppInfo,
	openAppSuper,
	closeAppSuper
} from '../comms/app-apiCenter';
import {
	getPageRelationAppData
} from '../comms/page-app-apiCenter';
import widget from '../ui/widget';
const Msg = widget.Message;
var  template = require('./app-relation-tpl.html');


/* 应用依赖业务逻辑控制器 */
const AppRelation = createPageController({
	template: template,
	property: {
		tenantName:'',
		serviceAlias:'',
		renderData: {
			appInfo:{},
			pageData: {}
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
				getPageRelationAppData(
					this.tenantName,
					this.serviceAlias
				).done((pageData) => {
					this.renderData.pageData = pageData;
					this.render();
					setTimeout(() => {
						this.checkIsEnhanced();
						$('.fn-tips').tooltip();
					})
				})
			})
		},
		//检查应用是否开启应用增强，来显示设置按钮
		checkIsEnhanced: function() {
			isAppEnhanced(
				this.tenantName,
				this.serviceAlias
			).done(function(data){
				if(data === true){
					$(".fn-high-relation").show();
					$('.openHightraly').hide();
					$('.closeHightraly').show();
				}else{
					$(".fn-high-relation").hide();
					$('.openHightraly').show();
					$('.closeHightraly').hide();
				}
			}).fail(function(){
				$(".fn-high-relation").hide();
			})
		},
		handleCreateAppRelation: function(destServiceAlias) {
			var self = this;
			createAppRelation(
				this.tenantName,
				this.serviceAlias,
				destServiceAlias
			).done(function(){
				Msg.success('操作成功');
				self.getInitData();
			})
		},
		handleCancelAppRelation: function(destServiceAlias) {
			var self = this;
			cancelAppRelation(
				this.tenantName,
				this.serviceAlias,
				destServiceAlias
			).done(function(){
				Msg.success('操作成功');
				self.getInitData();
			})
		},
		//TODO: 需要在理解业务后重构此方法
		handleSettingAppRelation(depServiceName) {
			var tenantName = this.tenantName;
			var curServiceName = this.serviceAlias;
		    $.ajax({
		        type: "GET",
		        url: "/ajax/" + tenantName + "/" + curServiceName + "/l7info",
		        data: { "dep_service_id": depServiceName },
		        cache: false,
		        async: false,
		        beforeSend: function (xhr, settings) {
		            var csrftoken = $.cookie('csrftoken');
		            xhr.setRequestHeader("X-CSRFToken", csrftoken);
		        },
		        success: function (data) {
		            var servenlayer = data;
		            var domainUrl = servenlayer["domain"];
		            var hasDoMainUrl = domainUrl != 'close' && domainUrl != 'off';
		            

		            //  展示 弹出层 start
		            var oStrH = '<form class="form-horizontal">'+
				            		'<div class="form-group">'+
				            			'<span class="col-sm-2 control-label">转发</span>'+
				            			'<div class="col-sm-8">'+
				            				'<input type="checkbox" name="domainurl"  id="domainurl" '+(hasDoMainUrl ? 'checked="checked"' : '')+'  class="checkhide" />'+
				            			'</div>'+
				            		 '</div>'+
				            		 '<div class="domain-form-group form-group" '+( hasDoMainUrl ? '' : 'style="display:none"' )+'>'+
				            			'<span class="col-sm-2 control-label">domain</span>'+
				            			'<div class="col-sm-8">'+
				            				'<input class="form-control" type="text" value="' + (hasDoMainUrl ? domainUrl : '') + '" id="dourl"/>'+
				            			'</div>'+
				            		 '</div>'+
				            		 '<div class="form-group">'+
				            			'<span class="col-sm-2 control-label">熔断</span>'+
				            			'<div class="col-sm-8">'+
				            				'<select class="form-control" id="fusing"><option value="0">0</option><option value="128">128</option><option value="256">256</option><option value="512">512</option><option value="1024">1024</option></select>'+
				            				'<span class="help-block">说明：熔断器数值表示同一时刻最大所允许向下游访问的最大连接数，设置为0时则完全熔断。</span>'+
				            			'</div>'+
				            		 '</div>'+
				                '</form>'



		            var cricuit = servenlayer["cricuit"];
		            var dialog = widget.create('dialog', {
		            	title: '设置',
		            	domEvents: {
		            		'.btn-success click': function() {
		            			submit();
		            		}
		            	}
		            })
		            dialog.setContent(oStrH);

		            $("#fusing option").each(function () {
		                var othis = $(this);
		                var thisval = $(this).attr("value");
		                if (thisval == cricuit) {
		                    $(othis).attr("selected", true);
		                }
		            });

		            //网址输入框改变 start
		            $("#domainurl").change(function () {
		                var damainonoff = $("#domainurl").prop("checked");
		                if (damainonoff == true) {
		                    $(".domain-form-group").show();
		                } else {
		                    $(".domain-form-group").hide();
		                }
		            });
		            //网址光标移出 end

		            //确定提交参数 start
		            function submit () {
		                var obox = {};
		                //var headerbox=[];
		                var oneonoff = $("#domainurl").prop("checked");
		                var domainval = $("#dourl").val();
		                var cricuitval = $("#fusing option:selected").attr("value");


		                if(oneonoff) {
		                	if(!domainval) {
		                		Msg.warning("请填写domain");
		                		return false;
		                	}
		                }


		                if (oneonoff == true) {
		                    obox["domain"] = domainval;
		                }
		                obox["cricuit"] = cricuitval;
		                ///ajax
		                var oboxstr = JSON.stringify(obox)
		                $.ajax({
		                    type: "POST",
		                    url: "/ajax/" + tenantName + "/" + curServiceName + "/l7info",
		                    data: {
		                        "dep_service_id": depServiceName,
		                        "l7_json": oboxstr
		                    },
		                    cache: false,
		                    async: false,
		                    beforeSend: function (xhr, settings) {
		                        var csrftoken = $.cookie('csrftoken');
		                        xhr.setRequestHeader("X-CSRFToken", csrftoken);
		                    },
		                    success: function (data) {
		                        
		                        if (data.status == "success") {
		                            Msg.success("设置成功！");
		                            dialog.destroy();
		                        } else {
		                            Msg.warning("设置失败！");
		                        }
		                    },
		                    error: function () {
		                        Msg.danger("系统异常");
		                    }
		                });
		                ///ajax
		            }
		        },
		        error: function () {
		            Msg.danger("系统异常");
		        }
		    });
		},
		handleViewConnectInfo:function(tmp){
			widget.create('dialog', {
				title:'连接信息',
				content: tmp,
				height: '400px',
				autoDestroy: true,
				btns:[{
					classes: 'btn btn-default btn-cancel',
					text: '关闭'
				}]
			})
		},
		handleOpenAppSuper: function(){
			var self = this;
			openAppSuper(
				this.tenantName,
				this.serviceAlias
			).done(function(data){
				self.getInitData();
			}).fail(function(data){
				$('[name=hightraly]').prop('checked', false)
			})
		},
		handleCloseAppSuper: function(){
			var self = this;
			closeAppSuper(
				this.tenantName,
				this.serviceAlias
			).done(function(data){
				self.getInitData();
			}).fail(function(data){
				$('[name=hightraly]').prop('checked', true)
			})
		}
	},
	domEvents: {
		//关联以来事件　
		'.createAppRelation click': function(e) {
			var destServiceAlias = $(e.currentTarget).parents('tr').attr('data-dest-service-alias');
			if(destServiceAlias) {
				this.handleCreateAppRelation(destServiceAlias);
			}
		},
		//取消依赖事件
		'.cancelAppRelation click': function(e) {
			var destServiceAlias = $(e.currentTarget).parents('tr').attr('data-dest-service-alias');
			if(destServiceAlias) {
				this.handleCancelAppRelation(destServiceAlias);
			}
		},
		//服务依赖 设置事件
		'.setting-app-relation click': function(e) {
			var destServiceAlias = $(e.currentTarget).parents('tr').attr('data-dest-service-alias');
			if(destServiceAlias) {
				this.handleSettingAppRelation(destServiceAlias);
			}
		},
		//查看链接信息
		'.viewConnectInfo click': function(e) {
			var $target = $(e.currentTarget);
			var tmp = $target.closest('tr').find('.connectInfoTmp');
			this.handleViewConnectInfo(tmp.html());
		},
		//开启应用特性增强
		'.openHightraly click': function(e) {
			this.handleOpenAppSuper();
		},
		//关闭应用特性增强
		'.closeHightraly click': function(e) {
			this.handleCloseAppSuper();
		}
	},
	onReady: function(){
		this.renderData.tenantName = this.tenantName;
		this.renderData.serviceAlias = this.serviceAlias;
		this.getInitData();
	}
})
window.AppRelationController = AppRelation;
export default AppRelation;