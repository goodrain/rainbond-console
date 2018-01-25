import http from '../utils/http';
import config from '../config/config';
import cookie from '../utils/cookie-util';


/*
	获取某个用户在某个团队下的详情
*/
export function getTeamUserInfo(dispatch, data={team_name, user_name}){

	return http({
		url:config.baseUrl + 'console/teams/'+data.team_name+'/'+data.user_name+'/details',
		type: 'get',
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
		type: 'post',
	}, dispatch)
}


/*
	设置团队成员权限
*/