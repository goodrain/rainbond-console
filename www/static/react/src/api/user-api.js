import http from '../utils/http';
import config from '../config/config';
import cookie from '../utils/cookie-util';


/*
	获取用户信息
*/
export function getUserInfo(dispatch){

	return http({
		url:config.baseUrl + 'console/users/details',
		type: 'get',
		isTipError: false,
		async: false
	}, dispatch)
}


/*
	注册用户
*/
export function register(dispatch, data={}){
	return http({
		url:config.baseUrl + 'console/users/register',
		type: 'post',
		data:data
	}, dispatch)
}


/*
	用户登录
*/
export function login(dispatch, data={nick_name, password}){
	return http({
		url:config.baseUrl + 'console/users/login',
		type: 'post',
		data:data
	}, dispatch)
}


/*
	退出登录
*/
export function logout(dispatch, data={nick_name, password}){
	return http({
		url:config.baseUrl + 'console/users/logout',
		type: 'get'
	}, dispatch)
}


/*
	发送忘记密码邮件
*/
export function setResetPassEmail(dispatch,data={email}){
	return http({
		url:config.baseUrl + 'console/users/send_reset_email',
		type: 'post',
		data: data
	}, dispatch)
}

/*
	忘记密码，设置新密码
*/
export function resetPassword(dispatch, data={password, password_repeat}){
	return http({
		url:config.baseUrl + 'console/users/begin_password_reset',
		type: 'post',
		data: data
	}, dispatch)
}

/*
	记得老密码，修改密码
*/
export function changepassword(dispatch, data={password, new_password, new_password_repeat}){

}

/*
	 模糊查询用户,通过用户名
*/
export function userQuery(dispatch, data={}){
	return http({
		url:config.baseUrl + 'console/users/query',
		type: 'post',
		data: data
	}, dispatch)
}


/*
	获取获取所加入的团队
*/
export function getUserTeams(dispatch){
	return http({
		url:config.baseUrl + 'console/users/teams/query',
		type: 'get'
	}, dispatch)
}

