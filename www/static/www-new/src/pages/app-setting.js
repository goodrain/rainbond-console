import createPageController from '../utils/page-controller';
import { 
	updateAppcName, 
	changeAppBrance,
	addAppMember,
	removeAppMember,
	setAppMemberPerm,
	removeAppMemberPerm,
	delApp,
	addEnvVar,
	delEnvVar,
	changeGroup,
	editInfo,
	loadGitBranch,
	getRunningHealthCheckInfo,
	getStartingHealthCheckInfo,
	activeAndDisableHealthCheck,
	getAppInfo,
	getAppCharacter,
	delAppCharacter,
	addAppCharacter
} from '../comms/app-apiCenter';
import widget from '../ui/widget';
import validationUtil from '../utils/validationUtil';

import {
	getPageSettingAppData
} from '../comms/page-app-apiCenter';

require('../components/healthCheck');
const Msg = widget.Message;
const template = require('./app-setting-tpl.html');


//创建新增环境变量的条目模版

const createVarTmp = ()  => {
	var msg = '<tr>'
    msg = msg + '<input type="hidden" class="form-control" name="attr_id" value="0">'
    msg = msg + '<td><input class="form-control" name="attr_name" type="text" value=""></td>'
    msg = msg + '<td><input class="form-control" name="attr_value" type="text" value=""></td>'
    msg = msg + '<td><input class="form-control" name="name" type="text" placeholder="可以不填写" value=""></td>' +
    '<td>' + 
        '<button type="button" class="attr-save btn btn-success">确定</button> ' +
        '<button type="button" class="attr-cancel btn btn-default">取消</button></td>' +
    '</td>'
    msg = msg + '</tr>';
    return  msg;
}

const createEnvVarTmp = (res) => {
  var pk = res.pk;
  var attr_name = res.attr_name;
  var attr_value = res.attr_value;
  var name = res.name;
  var msg = '<tr data-attr-name="'+attr_name+'">';
  msg = msg + '<input type="hidden" name="attr_id" value='+pk+'>';
  msg = msg + '<td class="attr_name_field">'+attr_name+'</td>';
  msg = msg + '<td>'+attr_value+'</td>';
  msg = msg + '<td>'+name+'</td>';
  msg = msg + '<td class="text-right"><button type="button" class="attr-delete btn btn-default btn-sm" >删除</button></td>';
  msg = msg+ '<tr>';
  return msg;
}



//健康监测配置
const healthCheckUtil = {
    getStatusCN: function(is_used){
        if(is_used === true){
            return '已启用'
        }

        if(is_used === false){
           return '已禁用'
        }

        return '未设置'
    }
}


/* 业务逻辑控制器 */
const AppSetting = createPageController({
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
		//启动时健康监测是否启用
		isStartingHealthCheckUsed: '',
		//运行时健康监测是否启用
		isRuningHealthCheckUsed: '',
		//启动时健康监测id
		startingProbeId:'',
		//运行时健康监测id
		runningProbeId:'',
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
				getPageSettingAppData(
					this.tenantName,
					this.serviceAlias
				).done((pageData) => {
					this.renderData.pageData = pageData;
					this.render();
					setTimeout(() => {
						//加载分支信息
						if($('#git_branch').length) {
							this.loadGitBranch();
						}

						//初始化健康监测信息
						this.initHealthCheckInfo();
						
					});
					this.showAppCharacter();
				})
			})
		},
		//初始化健康监测信息
		initHealthCheckInfo: function(){
			var self = this;
			//获取运行时健康监测信息
			getRunningHealthCheckInfo(
				this.tenantName,
				this.serviceAlias
			).done(function(data){
				self.runningProbeId = data.body.bean.probe_id;
            	self.isRuningHealthCheckUsed = data.body.bean.is_used;
            	self.onRunStatusChange();
			}).fail(function(data){
				self.onRunStatusChange();
			})

			//获取启动时健康监测信息
			getStartingHealthCheckInfo(
				this.tenantName,
				this.serviceAlias
			).done(function(data){
				self.startingProbeId = data.body.bean.probe_id;
            	self.isStartingHealthCheckUsed = data.body.bean.is_used;
            	self.onStartStatusChange();
			}).fail(function(data){
				self.onStartStatusChange();
			})
		},
		getPortsString:function(){
			var ports = this.renderData.pageData.ports || [];
			return ports;
		},
		//检测应用是否开启应用特性增强
		checkIsAppSuper: function() {
			isAppEnhanced(
				this.tenantName,
				this.serviceAlias
			).done(function(boolean){
				if(boolean === true){
					$('[name=hightraly]').prop('checked', true);
				}
			})
		},
		//当启动时状态变化时
		onStartStatusChange:function () {
			var isUsed = this.isStartingHealthCheckUsed;
		    if (isUsed === true) {
		        $('.disableStartCheck').show();
		        $('.activeStartCheck').hide();
		    }else if(isUsed === false) { 
		        $('.disableStartCheck').hide();
		        $('.activeStartCheck').show();
		    }else {
		        $('.disableStartCheck').hide();
		        $('.activeStartCheck').hide();
		    }
		    $('.viewStartHealth').show();
		    $('.startHealthCheck').html(healthCheckUtil.getStatusCN(isUsed));
		    
		},
		 //当运行时状态变化时
		onRunStatusChange:function () {
			var isUsed = this.isRuningHealthCheckUsed;
		    if (isUsed === true) {
		        $('.disableRunCheck').show();
		        $('.activeRunCheck').hide();
		    }else if(isUsed === false) {
		        $('.disableRunCheck').hide();
		        $('.activeRunCheck').show();
		    }else{
		    	
		        $('.disableRunCheck').hide();
		        $('.activeRunCheck').hide();
		    }
		    $('.viewRunHealth').show();
		    $('.runHealthCheck').html(healthCheckUtil.getStatusCN(isUsed));
		    
		},
		//获取应用代码分支地址
		loadGitBranch: function() {
			
			loadGitBranch(
				this.tenantName,
				this.serviceAlias
			).done(function(data) {
				for (var i in data.branchs) {
                    var opt = $("<option/>").val(data.branchs[i]).html(data.branchs[i])
                    if (data.branchs[i] == data.current) {
                        opt.prop('selected', true)
                    }
                    $('#git_branch').prepend(opt)
                }
			})
		},
		handleUpdateName: function(name) {
			return updateAppcName(
				this.tenantName,
				this.serviceAlias,
				name
			)
		},
		showChangeNameDialog: function(){
			var self = this;
			var form = widget.create('form', {
				hideLabel: true,
				items:[{
					name: "servicecname",
					type: 'text',
					label: "新名称",
					value: this.servicecName,
					required: true,
					requiredError: '请输入新名称',
					maxlength: 20
				}]
			})
			var dialog = widget.create('dialog', {
				id: 'changeNameDialog',
				closeable: false,
				width: "450px",
				height: "200px",
				title: "应用名称修改",
				domEvents: {
					'.btn-success click': function() {
						if(form.valid()){
							var name = form.getValue('servicecname');
							self.handleUpdateName(name).done(function(data){
								Msg.success('操作成功');
								self.servicecName = name;
								$("#appname").html(name);
								$(".lit-appname").html(name);
								form.destroy();
								dialog.destroy();
								form = dialog = null;
							})
						}
					},
					'.btn-cancel click' :function() {
						form.destroy();
						form = dialog = null;
					}
				}
			})
			dialog.setContent(form.getElement());
		},
		handleChangeAppBranch: function(branch) {
			changeAppBrance(
				this.tenantName,
				this.serviceAlias,
				branch
			).done(function(data){
				Msg.success("切换完毕, 下次部署后生效");
			})
		},
		handleAddMember: function(email, perm) {
			var self = this;
			addAppMember(
				this.tenantName,
				this.serviceAlias,
				email,
				perm
			).done(function(){
				self.getInitData();
			})
		},
		handleRemoveMember: function(user) {
			removeAppMember(
				this.tenantName,
				this.serviceAlias,
				user
			).done(function(data){
				Msg.success('操作成功');
				$('tr[entry-user='+user+']').remove();
			})
		},
		showRemoveAppMemberConfirm: function(user) {
			var self = this;
			var confirm = widget.create('confirm', {
				title:' 删除成员 '+user,
				content: '<h3>确定要执行此操作吗？</h3>',
				event:{
					onOk: function() {
						confirm.destroy();
						self.handleRemoveMember(user);
					}
				}
			})
		},
		handleSetMemberPerm: function(user, perm, checked) {
			if(checked){
				return setAppMemberPerm(
					this.tenantName,
					this.serviceAlias,
					user,
					perm
				)
			}else{
				return removeAppMemberPerm(
					this.tenantName,
					this.serviceAlias,
					user
				)
			}
			
		},
		handleDelApp: function() {
			delApp(
				this.tenantName,
				this.serviceAlias
			).done(function(){
				Msg.success('操作成功, 删除进行中...');
				setTimeout(()=>{
					 location.href = "/"
				}, 2000)
			})
		},
		showDelAppConfirm: function() {
			var self = this;
		    var notify_text = "<h3>确定删除当前服务吗？</h3>";
		    if (this.code_from == "gitlab_new") {
		        notify_text = "<h4>关联git代码将同步删除，确定删除当前服务吗？</h3>"
		    }

		    var confirm = widget.create('confirm', {
		    	title: '应用删除',
		    	content: notify_text,
		    	event: {
		    		onOk: function() {
		    			self.handleDelApp();
		    			confirm.destroy();
		    		}
		    	}
		    })
		},
		handleAddEnvVar: function(attrName, attrValue, desc) {
			return addEnvVar(
				this.tenantName,
				this.serviceAlias,
				attrName, attrValue, desc
			).done(function(res) {
				$("#envVartable tr:last").after(createEnvVarTmp(res));
			})
		},
		handleDelEnvVar: function(attrName) {
			return delEnvVar(
				this.tenantName,
				this.serviceAlias,
				attrName
			)
		},
		handleChangeGroup: function(groupId) {
			return changeGroup(
				this.tenantName,
				this.serviceId,
				groupId
			)
		},
		showChangeGroupDialog: function(){
			var self = this;
			var dialog = widget.create('dialog', {
				title: '修改分组',
				width: '400px',
				height: '200px',
				domEvents: {
					'.btn-success click': function () {
						var groupId = dialog.getElement().find('.groups-select').val();
						var groupName = dialog.getElement().find('option:selected').html();
						self.handleChangeGroup(groupId).done(function(){
							location.href="/";
						})
					}
				}
			})
			dialog.appendContent($('.groups-select').clone(true));
		},
		handleEditInfo: function(newname, newgroup, newgit) {
			return editInfo(
				this.tenantName,
				this.serviceAlias,
				newname, newgroup, newgit
			)
		},
		showEditInfoDialog: function() {
			var self = this;
			var dialog = gWidget.create('dialog', {
                title:'编辑信息',
                id:'editbox',
                width:'450px',
                height:'350px',
                autoDestroy: true,
                domEvents:{
                  '.btn-success click': function(){
                      var newname = $.trim($("#newname").prop("value"));
                      var newgroup = $("#newgroup option:selected").prop("value");
                      var newgit = $("#newgit").prop("value");
                      if (newname.length == 0){
                          Msg.warning("应用名称不能为空")
                          return false;
                      }
                      self.handleEditInfo(newname, newgroup, newgit).done(function(){
                      	  dialog.destroy();
                      	  self.getInitData();
                      })
                  }
                },
                btns:[
                   {
                    text:'确定',
                    classes:'btn btn-success'
                   },
                   {
                    text:'取消',
                    classes:'btn btn-default btn-cancel'
                   }
                ]
             })
             dialog.setContent($('#checkTmp').html());  
		},
		handleOpenAppSuper: function(){
			openAppSuper(
				this.tenantName,
				this.serviceAlias
			).done(function(data){

			}).fail(function(data){
				$('[name=hightraly]').prop('checked', false)
			})
		},
		handleCloseAppSuper: function(){
			closeAppSuper(
				this.tenantName,
				this.serviceAlias
			).done(function(data){

			}).fail(function(data){
				$('[name=hightraly]').prop('checked', true)
			})
		},
		//删除应用特性
		delAppCharacterLabel : function(tenantName,serviceAlias,labelid){
			delAppCharacter(
		    	tenantName,
				serviceAlias,
				labelid
			).done(function(data){
				if(data.ok == true){
					Msg.warning('操作成功！');
					$('#label' + labelid).remove();
				}else{
					Msg.warning('操作失败，请稍后重试');
				}
			}).fail(function(data){
				Msg.warning('操作失败，请稍后重试');
			})
		},
		//显示删除应用特性层
		showdelAppCharacter : function(labelid) {
			var self = this;
		    var notify_text = "<h3>确定删除当前应用特性吗？</h3>";
		    var confirm = widget.create('confirm', {
		    	title: '删除特性',
		    	content: notify_text,
		    	event: {
		    		onOk: function() {
		    			self.delAppCharacterLabel(self.tenantName,self.serviceAlias,labelid);
		    			confirm.destroy();
		    		}
		    	}
		    })
		},
		//展示应用特性
		showAppCharacter: function(){
			getAppCharacter(
				this.tenantName,
				this.serviceAlias
			).done(function(data){
				if(data['used_labels'].length != 0){
					var charStr = '';
					for(var i=0; i< data['used_labels'].length ; i++){
						charStr += '<p id="label'+ data['used_labels'][i].label_id +'"><span>' + data['used_labels'][i].label_alias + '</span><a href="javascript:;" class="glyphicon glyphicon-remove fn-del-appcharacter" data-id="'+ data['used_labels'][i].label_id +'"></a></p>';
					}
					$("#app-character").html(charStr);
				}
			}).fail(function(data){
				
			})
		},
		//展示层内容
		showchooseAppCharacterLabel : function(){
			var self = this;
			getAppCharacter(
				this.tenantName,
				this.serviceAlias
			).done(function(data){
				if(data.ok == true){
					var charStr = '';
					if(data['unused_labels'].length != 0){
						charStr += '<p style="color:#838383; font-size:16px; line-height:30px; margin-bottom:0;">节点特性:</p><div>'
						for(var i=0; i< data['unused_labels'].length ; i++){
							charStr += '<label id='+ data['unused_labels'][i].label_id +'" class="labelcheck clearfix"><input type="checkbox" data-id="'+ data['unused_labels'][i].label_id +'" value="'+ data['unused_labels'][i].label_alias +'" /><span>' + data['unused_labels'][i].label_alias + '</span></label>';
						}
						charStr += "</div>"
						self.showchooseAppCharacter(charStr);
					}else{
						Msg.warning('暂时没有可选标签');
					}
				}else{
					Msg.warning(data.msg);
				}
			}).fail(function(data){
				Msg.warning(data.msg);
			})
		},
		//选择应用特性层
		showchooseAppCharacter:function(chooseStr){
			var self = this;
			var dialog = gWidget.create('dialog', {
                title:'选择应用特性',
                id:'characterbox',
                width:'450px',
                height:'350px',
                autoDestroy: true,
                domEvents:{
                   '.btn-success click': function(){
                   	    var jsonlabel = {};
                   		var labelarr = [];
                   		$("#characterbox").find("input").each(function(){
                   			if($(this).prop('checked')){
                   				var appid = $(this).attr("data-id");
                   				labelarr.push(appid);
                   			}
                   		});
                   		if(labelarr.length != 0){
                   			addAppCharacter(self.tenantName,self.serviceAlias,labelarr);
                   			dialog.destroy();
                   			self.getInitData();
                   		}else{
                   			Msg.warning('请选择标签！');
                   		}
                    }
                },
                btns:[
                   {
                    text:'确定',
                    classes:'btn btn-success'
                   },
                   {
                    text:'取消',
                    classes:'btn btn-default btn-cancel'
                   }
                ]
            })
            dialog.setContent(chooseStr);  
		}
		// end
	},
	domEvents:{
		//修改基本信息事件
		'#edit click': function() {
			this.showEditInfoDialog();
		},
		//改名
		'.fn-rename click': function(e) {
			this.showChangeNameDialog();
		},
		//改组事件
		'.fn-name click': function(e) {
			this.showChangeGroupDialog();
		},
		//修改分支事件
		'.changeAppBranch click': function(e) {
			var branch = $('.git-branch-change').val();
			this.handleChangeAppBranch(branch);
		},


		//邀请成员
		'#invite_user_btn click': function(e) {
			var email = $('#invite_email').val();
			var perm = $('#ivite_perm').val();

			if(!validationUtil.valid('email', email)){
				Msg.warning("邮箱格式不正确，请检查后重试")
				return false;
			}
			this.handleAddMember(email, perm);
		},
		//删除成员
		'.member-remove click': function(e) {
			var $target = $(e.currentTarget);
			var user = $target.parents('tr').attr('entry-user');
			this.showRemoveAppMemberConfirm(user);
		},
		//设置成员权限事件
		'.js-perm click': function(e) {
			var $target = $(e.currentTarget);
			if(!$target.attr('disabled')) {
				var checked = $target.prop('checked');
				var perm = $target.attr('identity');
				var user = $target.parents('tr').attr('entry-user');
				var next_identities = $target.parent().nextAll();
				this.handleSetMemberPerm(
					user, 
					perm,
					checked
				).done(function(data){
					if(checked) {
						next_identities.each(function(){
							$(this).find('input').prop('checked',true).prop('disabled',true)
						})
					}else{
						next_identities.each(function(){
							var $input = $(this).find('input');
							var perm = $input.attr('identity');
							if(perm != 'viewer'){
								$input.prop('checked',false).prop('disabled',false)
							}
						})
						
					}
				}).fail(function(){
					if(checked){
						$target.removeAttr('checked');
					}else{
						$target.prop('checked', 'checked');
					}

				})
			}
		},
		//删除应用事件
		'#cur_delete_service click': function(e) {
			this.showDelAppConfirm();
		},
		// 新增环境变量 按钮点击事件
		'#add_service_attr click': function() {
			$("#envVartable tbody").append(createVarTmp());
		},
		//删除新增环境变量模版条目
		'.attr-cancel click': function(e) {
			$(e.currentTarget).closest('tr').remove();
		},
		//新增环境变量提交按钮
		'.attr-save click': function(e) {
			var $tr = $(e.currentTarget).closest('tr');
			var attrName = $tr.find('[name=attr_name]').val();
			var attrValue = $tr.find('[name=attr_value]').val();
			var desc = $tr.find('[name=name]').val();
			if(!validationUtil.valid('envvar', attrName)) {
				Msg.warning("变量名格式不正确，请检查后重试");
				return;
			}
			if(!attrValue) {
				Msg.warning("请填写变量值");
				return;
			}
			this.handleAddEnvVar(attrName, attrValue, desc).done(function(res){
				$tr.remove();
			})
		},
		//删除环境变量
		'.attr-delete click': function(e) {
			var $tr = $(e.currentTarget).closest('tr');
			var attrName = $tr.attr('data-attr-name');
			if(attrName) {
				this.handleDelEnvVar(attrName).done(function(){
					$tr.remove();
				})
			}
		},
		//启动时查看/编辑
        '.viewStartHealth click': function(e){
            //收集所有的端口信息
            var self = this;
            var ports = this.getPortsString();
            if(!ports.length){
                Msg.danger('请先为应用配置端口');
                return;
            }

             var viewAndEditStartHealthCheck = widget.create('viewAndEditStartHealthCheck', {
                serviceAlias:self.serviceAlias,
                tenantName:self.tenantName,
                port:ports,
                mode:'readiness',
                onAddSuccess:function(data){
                    Msg.success('操作成功！')
                    //启动时健康监测是否启用
					self.isStartingHealthCheckUsed = data.body.bean.is_used;
					self.startingProbeId = data.body.bean.probe_id;
                    self.onStartStatusChange();
                },
                onEditSuccess:function(){
                    Msg.success('操作成功！')
                }
             });
        },
        //启动时启用
        '.activeStartCheck click': function(e){
        	var self = this;
        	if(!self.startingProbeId || self.isStartingHealthCheckUsed) return;
             activeAndDisableHealthCheck(
                this.tenantName,
                this.serviceAlias,
                this.startingProbeId
             ).done(function(data){
                Msg.success('操作成功！')
                self.isStartingHealthCheckUsed = true;
                self.onStartStatusChange();
             })
        },
        //启动时禁用
        '.disableStartCheck click': function(e){
        	var self = this;
            if(!self.startingProbeId  || !self.isStartingHealthCheckUsed) return;
            activeAndDisableHealthCheck(
               this.tenantName,
               this.serviceAlias,
               this.startingProbeId
            ).done(function(data){
               Msg.success('操作成功！')
               self.isStartingHealthCheckUsed = false;
               self.onStartStatusChange();
            })
        },
		// 运行时查看/编辑
        '.viewRunHealth click':function(){
        	var self = this;
            //收集所有的端口信息
            var ports = this.getPortsString();

            if(!ports.length){
                Msg.danger('请先为应用配置端口');
                return;
            }

            var viewAndEditStartHealthCheck = widget.create('viewAndEditStartHealthCheck', {
                serviceAlias:this.serviceAlias,
                tenantName:this.tenantName,
                viewTitle:'运行时监测',
                editTitle: '请设置对运行时检测的具体要求',
                port:ports,
                mode:'liveness',
                onAddSuccess:function(data){
                    self.runningProbeId = data.body.bean.probe_id;
                    self.isRuningHealthCheckUsed = data.body.bean.is_used;
                    Msg.success('操作成功！');
                    self.onRunStatusChange();
                },
                onEditSuccess:function(){
                    gWidget.Message.success('操作成功！')
                }
             });
        },
        //运行时启用
        '.activeRunCheck click': function(){
        	var self= this;
            if(!this.runningProbeId || this.isRuningHealthCheckUsed) return;
            activeAndDisableHealthCheck(
                this.tenantName,
                this.serviceAlias,
                self.runningProbeId
            ).done(function(data){
                Msg.success('操作成功！');
                self.isRuningHealthCheckUsed = true;
                self.onRunStatusChange();
            })
        },
        //运行时禁用
        '.disableRunCheck click': function(){
        	var self = this;
             if(!self.runningProbeId || !this.isRuningHealthCheckUsed) return;
             activeAndDisableHealthCheck(
                this.tenantName,
                this.serviceAlias,
                self.runningProbeId
             ).done(function(data){
                Msg.success('操作成功！');
                self.isRuningHealthCheckUsed  = false;
                self.onRunStatusChange();
             })
        },
        //选择特性
        '.fn-choose-char click':function(){
        	this.showchooseAppCharacterLabel();
        },
        //删除特性
        '.fn-del-appcharacter click':function(e){
        	var $target = $(e.currentTarget);
			var labelid = $target.attr("data-id");
			this.showdelAppCharacter(labelid);
        }
	},
	onReady: function(){
		this.renderData.tenantName = this.tenantName;
		this.renderData.serviceAlias = this.serviceAlias;
		this.getInitData();
	}
})

window.AppSettingController = AppSetting;
export default AppSetting;