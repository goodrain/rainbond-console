import cookie from './cookie';

const actionMap = {
	admin: '管理员',
	developer: '开发者',
	viewer: '观察者',
	access: '访问者',
	owner: '拥有者'
}

const teamUtil = {
	actionToCN(action=[]){
		var res = [];
		res = action.map((item) => {
			return actionMap[item]
		});
		return res.join(', ')
	},
	getRegionByName(teamBean, region_name) {
		var regions = teamBean.region || [];
		
		var region = regions.filter((item) => {
			 return item.team_region_name === region_name;
		})
		return region[0];
	},
	//是否可以编辑团队名称
	canEditTeamName(teamBean={}) {
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('modify_team_name') > -1
	},
	//是否可以删除团队
	canDeleteTeam(teamBean={}) {
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('drop_tenant') > -1
	},
	//是否可以添加团队成员
	canAddMember(teamBean={}) {
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('add_tenant_members') > -1
	},
	//是否可以编辑团队成员权限
	canEditMemberAction(teamBean={}) {
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('modify_team_member_permissions') > -1
	},
	//是否可以删除团队成员
	canDeleteMember(teamBean={}) {
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('drop_tenant_members') > -1
	},
	//对否可以移交团队
	canChangeOwner(teamBean={}) {
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('transfer_ownership') > -1
	},
	//是否可以分享应用
	canShareApp(teamBean={}) {
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('app_publish') > -1
	}
}

export default teamUtil;