import http from './http';
import { message } from 'antd';
import config from '../config/config';
import cookie from './cookie-util';
var $ =  require('../libs/jquery.min');

/*
	绑定手机号
*/

export function bindPhone(dispatch, mobile, uid, captcha) {
	return http({
		url:config.baseUrl + 'api/accounts/bind-mobile',
		type: 'get',
		headers:{
			"Authorization": "Bearer "+cookie.get("token")
		},
		data: {
			mobile: mobile,
			uid: uid,
			captcha: captcha
		}
	}, dispatch)
}



/*
	 获取token
*/

export function getToken(dispatch, headers, data){
	var dfd = $.Deferred();
	return $.ajax({
		url:config.baseUrl + 'api/access_token',
		type: 'post',
		headers: headers,
		data: data
	}).done((data) => {
		dfd.resolve(data);
	}).fail((data) => {
		message.error(data.error || '操作异常');
		dfd.reject(data);
	})
	return dfd;
}


/*
	注册

	@user {
		company:'企业名称'
		password:'密码'
		name: '用户姓名'
		phone_no:'手机号',
		captcha: '手机验证码'

	}
*/
export function register(dispatch, user,remember=true){
	var dfd = $.Deferred();
	http({
		url:config.baseUrl + 'api/accounts/register/',
		type: 'post',
		data: user
	}, dispatch).done((data) => {
		var days = remember ? 30 : 0;
		var domain = ".goodrain.com";
		console.log(data);
		console.log(data.token);
		var namecode = escape(data.bean.username);
		cookie.set("username", namecode, days, domain);
		cookie.set("token", data.token, days, domain);
		cookie.set("uid", data.bean.uid, days, domain);
		cookie.set("sid", data.bean.id, days, domain);
		dfd.resolve(data);
	}).fail((data) => {
		message.error(data.msg_show || '操作异常');
		dfd.reject(data);
	})
	return dfd;
}


/*
	登录
*/
export function login(dispatch, data={}, remember=true) {

	var dfd = $.Deferred();
	http({
		url:config.baseUrl + 'api/accounts/login/',
		type:'post',
		data:data
	}, dispatch).done((data) => {
		var days = remember ? 30 : 0;
		var domain = ".goodrain.com";
		var namecode = escape(data.bean.username);
		cookie.set("username", namecode, days, domain);
		cookie.set("token", data.token, days, domain);
		cookie.set("uid", data.bean.uid, days, domain);
		cookie.set("sid", data.bean.id, days, domain);
		dfd.resolve(data);
	}).fail(() => {
		dfd.reject()
	})
	return dfd;
}

/*
	检测手机号是否可用
*/
export function checkMobile(dispatch, mobile, async=true, isTipError=false){
	return http({
		url:config.baseUrl + 'api/check-mobile?mobile='+mobile,
		type:'get',
		async: async,
		isTipError: isTipError
	}, dispatch)
}



/*
	获取短信验证码
*/
export function getPhoneCode(dispatch, mobile, forgot=false){
	return http({
		url:config.baseUrl + 'api/cpatcha',
		type:'post',
		data:{
			mobile: mobile,
			forgot: forgot
		}
	}, dispatch)
}

/*
	验证短信验证码
*/
export function checkPhoneCode(dispatch, mobile, phoneCode){
	return http({
		url:config.baseUrl + 'api/check-captcha',
		type:'get',
		data:{
			mobile: mobile,
			captcha: phoneCode
		}
	}, dispatch)
}

/*
	验证token
*/
export function checkToken(dispatch, token){
	return http({
		url:config.baseUrl + 'api/validate_token',
		type:'get',
		data:{
			token: token
		}
	}, dispatch)
}

/*
	忘记密码
*/
export function forgetPassword(dispatch, mobile,password, newpassword){
	return http({
		url:config.baseUrl + 'api/accounts/forget-password',
		type:'post',
		data:{
			mobile: mobile,
			password: password,
			repassword: newpassword
		}
	}, dispatch)
}


/*
	退出登录
*/
export function logout(dispatch) {
	return http({
		url:config.baseUrl + 'api/accounts/logout',
		type:'get'
	}, dispatch).done((data) => {
		http.removeToken();
		cookie.remove('token');
		cookie.remove('user');
		dispatch({
        	type:'LOGOUT'
        })
	}).fail(() => {

	})
}