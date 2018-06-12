import cookie from './cookie';
import globalUtil from './global';
import teamUtil from './team';
import regionUtil from './region';

const userUtil = {
	isLogin() {
		return !!(cookie.get('token'));
	},
	getDefaultTeamName(bean) {
		var dTeam = this.getDefaultTeam(bean);
		if (dTeam) {
						return dTeam.team_name
		}
		return '';
	},
	getDefaultTeam(bean) {
		if (bean && bean.teams && bean.teams.length) {
						return bean.teams[0]
		}
		return '';
	},
	getDefaultRegionName(bean) {
		var dTeam = this.getDefaultTeam(bean);
		if (dTeam && dTeam.region.length) {
						return dTeam.region[0].team_region_name
		}
		return '';
	},
	getTeamByTeamName(user, currTeamName) {
		const currTeam = user
						.teams
						.filter((item) => {
										return item.team_name === currTeamName;
						})[0];
		return currTeam;
	},
	//用户是否在某个团队下，拥有某个数据中心
	hasTeamAndRegion(user, team_name, region_name) {
		const team = this.getTeamByTeamName(user, team_name);
		if (!team) {
			return false;
		}
		const region = (team.region || []).filter((item) => {
			return item.team_region_name === region_name;
		})[0]
		return region;
	},
	//获取某个团队的默认数据中心
	
	//是否开通了gitlab账号
	hasGitlatAccount(user) {
		return user.git_user_id !== 0
	},
	//是否是系统管理员
	isSystemAdmin(userBean) {
		return userBean.is_sys_admin
	},
	//是否是企业管理员
	isCompanyAdmin(userBean){
		return userBean.is_user_enter_amdin
	},
	//获取当前的soketUrl
	getCurrRegionSoketUrl(currUser){
		var currTeam = this.getTeamByTeamName(currUser, globalUtil.getCurrTeamName());
		var currRegionName = globalUtil.getCurrRegionName();
	
		if (currTeam) {
		  var region = teamUtil.getRegionByName(currTeam, currRegionName);
	
		  if (region) {
			return regionUtil.getEventWebSocketUrl(region);
		  }
		}
		return '';
	}

}

export default userUtil;