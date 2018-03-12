import http from '../utils/http';
import config from '../config/config';
import cookie from '../utils/cookie-util';


/*
	获取某个用户在某个团队下的详情
*/
export function getTeamUserInfo(dispatch, data={team_name, user_name}){

	return http({
		url:config.baseUrl + 'console/teams/'+data.team_name+'/'+data.user_name+'/details',
		type: 'get'
	}, dispatch)
}

/*
	移交团队管理权限
*/
export function setTeamAdmin(dispatch, data={team_name, user_name}){
	return http({
		url:config.baseUrl + 'console/teams/'+data.team_name+'/'+data.user_name+'/details',
		type: 'post',
	}, dispatch)
}

/*
	获取团队的权限都有哪些
	@return {
	  "msg": "get permissions success",
	  "body": {
	    "bean": {},
	    "list": [
	      "admin",
	      "developer",
	      "viewer",
	      "access"
	    ]
	  },
	  "code": 200,
	  "msgcn": "获取权限成功"
	}
*/
export function getTeamActions(dispatch){
	return http({
		url:config.baseUrl + 'console/teams/user/identity',
		type: 'post'
	}, dispatch)
}


/*
	设置团队成员权限
*/
export function setTeamMemberAction(dispatch, data={team_name, user_name, identity}){
	return http({
		url:config.baseUrl + 'console/teams/'+data.team_name+'/'+data.user_name+'/modidentity',
		type: 'post',
		data:{
			identity: data.identity
		}
	}, dispatch)
}

/*
	 新建团队
*/
export function buildTeam(dispatch, data={team_name, useable_regions}){
	return http({
		url:config.baseUrl + 'console/teams/add-teams',
		type: 'post',
		data:data
	}, dispatch)
}

/*
	获取某个团队下的所有用户
*/
export function getMembers(dispatch, data={team_name, page, pageSize}){
	return http({
		url:config.baseUrl + 'console/teams/'+data.team_name+'/users',
		type: 'get',
		data:{
			page: data.page,
			pageSize: pageSize
		}
	}, dispatch)
}

/*
	添加成员
*/
export function addMember(dispatch, data={team_name, user_name}){
	return http({
		url:config.baseUrl + 'console/teams/'+data.team_name+'/add-user',
		type: 'post',
		data:{
			user_name: data.user_name
		}
	}, dispatch)
}

/*
	删除团队成员
*/
export function removeMember(dispatch, data={team_name, user_ids}){
	return http({
		url:config.baseUrl + 'console/teams/'+data.team_name+'/add-user',
		type: 'delete',
		data:{
			user_ids: data.user_ids
		}
	}, dispatch)
}

/*
	 修改团队名称
*/
export function rename(dispatch, data={team_name, new_team_name}){
	return http({
		url:config.baseUrl + 'console/teams/'+data.team_name+'/modifyname',
		type: 'post',
		data:{
			new_team_name: data.new_team_name
		}
	}, dispatch)
}

/*
	删除当前团队
*/

export function removeTeam(dispatch, data={team_name}){
	return http({
		url:config.baseUrl + 'console/teams/'+data.team_name+'/delete',
		type: 'delete'
	}, dispatch)
}

/*
	获取当前团队的数据中心
*/
export function getTeamRegions(dispatch, data={team_name}){
	return http({
		url:config.baseUrl + 'console/teams/'+data.team_name+'/region/query',
		type: 'get'
	}, dispatch)
}

/*
	获取某个团队的详情
*/
export function getTeamInfo(dispatch, data={team_name}){
	return http({
		url:config.baseUrl + 'console/team/'+data.team_name+'/overview',
		type: 'get'
	}, dispatch)
}

