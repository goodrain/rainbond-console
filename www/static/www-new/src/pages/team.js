import createPageController from '../utils/page-controller';
import { } from '../comms/team-apiCenter';
import { getAppContainer, getCanReceiveLogApp } from '../comms/apiCenter';
import { addMember, setMemberPerm, removeMember, removeMemberPerm } from '../comms/team-apiCenter';
import AppLogSocket from '../utils/appLogSocket';
import widget from '../ui/widget';
import validationUtil from '../utils/validationUtil';
import {
	getPageTeamData
} from '../comms/page-app-apiCenter';
var template = require('./team-tpl.html');

const Msg = widget.Message;


/* 团队页面 业务逻辑控制器 */
const Team = createPageController({
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
			getPageTeamData(
				this.tenantName
			).done((pageData) => {
				this.renderData.pageData = pageData;
				this.render();
			})
		},
		//邀请成员处理方法
		handleInvite: function(email, perm) {
			var self = this;
			addMember(
				this.tenantName,
				email,
				perm
			).done(function(){
				self.onInviteSuccess();
			})
		},
		onInviteSuccess: function() {
			$('#invite_email').val("");
			this.getInitData();
		},
		handleSetPerm: function(user, perm, checked) {
			if(checked) {
				return setMemberPerm(
					this.tenantName,
					user,
					perm
				)
			} else {
				return removeMemberPerm(
					this.tenantName,
					user
				)
			}
		},
		handleRemoveMember: function(user) {
			removeMember(
				this.tenantName,
				user
			).done(function(data){
				$('tr[entry-user='+user+']').remove();
			})
		},
		showRemoveConfirm: function(user) {
			var self = this;
			var confirm = widget.create('confirm', {
				title:' 删除成员 '+user,
				content: '确定要执行此操作吗？',
				event:{
					onOk: function() {
						confirm.destroy();
						self.handleRemoveMember(user);
					}
				}
			})
		}
	},
	domEvents: {
		//邀请事件
		'#invite_user_btn click': function() {
			var email = $('#invite_email').val();
			var perm = $('#ivite_perm').val();

			if(!validationUtil.valid('email', email)){
				Msg.warning("邮箱格式不正确，请检查后重试")
				return false;
			}
			this.handleInvite(email, perm);
		},
		//设置权限事件
		'.js-perm click': function(e) {
			var $target = $(e.currentTarget);
			if(!$target.attr('disabled')) {
				var checked = $target.prop('checked');
				var perm = $target.attr('identity');
				var user = $target.parents('tr').attr('entry-user');
				var next_identities = $target.parent().nextAll();
				this.handleSetPerm(
					user, 
					perm, 
					checked
				).done(function(data){
					if(checked) {
						next_identities.children('input').prop('checked',true).prop('disabled',true);
					}else{
						next_identities.each(function(){
							var $input = $(this).find('input');
							var perm = $input.attr('identity');
							if(perm != 'access'){
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
		//删除成员
		'.member-remove click': function(e) {
			var $target = $(e.currentTarget);
			var user = $target.parents('tr').attr('entry-user');
			this.showRemoveConfirm(user);

		}
	},
	onReady:function(){
		this.renderData.tenantName = this.tenantName;
		this.getInitData();
	}
})

window.TeamController = Team;
export default Team;