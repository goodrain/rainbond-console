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
	//是否可以添加角色
	canAddRole(teamBean={}){
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('tenant_manage_role') > -1
	},
	//是否可以修改角色
	canEditRole(teamBean={}){
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('tenant_manage_role') > -1
	},
	//是否可以删除角色
	canDelRole(teamBean={}){
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('tenant_manage_role') > -1
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
	//是否有权限开通数据中心
	canAddRegion(teamBean={}){
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('tenant_open_region') > -1
	},
	//是否可以添加团队成员
	canAddMember(teamBean={}) {
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('manage_team_member_permissions') > -1
	},
	//是否可以编辑团队成员权限
	canEditMemberRole(teamBean={}) {
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('manage_team_member_permissions') > -1
	},
	//是否可以删除团队成员
	canDeleteMember(teamBean={}) {
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('manage_team_member_permissions') > -1
	},
	//是否是创建者 
	isCreater(teamBean={}){
		var actions = teamBean.role_name_list || [];
		return actions.indexOf('owner') > -1
	},
	//是否是团队管理员
	isAdmin(teamBean={}){
		var actions = teamBean.role_name_list || [];
		return actions.indexOf('admin') > -1
	},
	//是否可以查看财务中心
	canViewFinance(teamBean={}){
		return this.isCreater(teamBean) || this.isAdmin(teamBean);
	},
	//对否可以移交团队 
	canChangeOwner(teamBean={}) {
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('transfer_ownership') > -1
	},
	//是否可以分享应用
	canShareApp(teamBean={}) {
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('share_service') > -1
	},
	//是否可以管理应用组
	canManageGroup(teamBean={}) {
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('manage_group') > -1
	},
	//是否可以管理插件
	canManagePlugin(teamBean={}){
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('manage_plugin') > -1
	},
	//是否可以查看应用
	canViewApp(teamBean={}){
		var actions = teamBean.tenant_actions || [];
		return actions.indexOf('view_service') > -1
	},
}

export default teamUtil;