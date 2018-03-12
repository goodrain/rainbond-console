var $ =  require('../libs/jquery.min');
import { message } from 'antd';
import cookie from './cookie-util';


/*
 * 通用ajax服务
 * */

//瞬间请求的次数
let total_loading = 0;
function showLoading(dispatch){
	if(!dispatch) return;

	if(total_loading  === 0){

		dispatch && dispatch({
			type:'SHOW_LOADING'
		})
	}
	total_loading ++;
}
function hiddenLoading(dispatch){
	if(!dispatch) return;
	total_loading --;

	if(total_loading <= 0){
		dispatch && dispatch({
			type:'HIDDEN_LOADING'
		})
	}
}


var filters = [];
//用于配置
var config = window.httpConfig = {
		beforeLoad:function(dispatch){
			showLoading(dispatch);
		},
		afterLoad:function(dispatch){
			
			hiddenLoading(dispatch);
		},
		addFilters:function(handle){
			if(handle){
				filters.push(handle);
			}
		}
		
};

//当前正在请求的ajax的记录对象， 以url为标示
var ajaxIngCache = {
		cache:{},
		handleUrl:function(url){
			url = (url||'').replace(/\?.*/, "");
			return url;
		},
		get:function(url){
			var url = this.handleUrl(url);
			return this.cache[url];
		},
		add:function(url){
			if(!url)return;
			var url = this.handleUrl(url);
			this.cache[url] = true;
			
		},
		remove:function(url){
			var url = this.handleUrl(url);
			delete this.cache[url];
		}
}



//身份凭证
var userToken = '';
function http(option={}, dispatch){
	 option = option || {};
	 option.type = option.type || option.method || 'get';
	 var isTipError = option.isTipError == (void 0) ? true : option.isTipError;
	 option.timeout = option.timeout || 1000 * 20; //20秒超时
	 option.multiple = option.multiple || false;//已url为标示， 是否可以同一个请求没返回之前再次发起
	 var data = option.data || {};
	 var ajaxToken='';
	 try{
 	 	ajaxToken = JSON.stringify(option);
 	 }catch(e){
 		ajaxToken = '';
 	 }

	 if(option.multiple === false){

		 if(!ajaxIngCache.get(ajaxToken)){
			 ajaxIngCache.add(ajaxToken)
		 }else{
			 return {
				 done:function(){},
				 fail:function(){},
				 always:function(){}
			 }
		 }
	 }
	 //promise对象
	 var dfd = $.Deferred();
	 option.success=function(data = {}){
		 ajaxIngCache.remove(ajaxToken);
		 if(option.showLoading !== false){
			 config.afterLoad(dispatch);
		 }

		 dfd.resolve(data.data ? data.data : data);
	 }
	 
	 option.error=function(xmlHttpRequest, code, th){
		 ajaxIngCache.remove(ajaxToken);
		 if(option.showLoading !== false){
			 config.afterLoad(dispatch);
		 }
		 var responseJSON = {};
		 if(xmlHttpRequest.responseJSON){
		 	responseJSON = xmlHttpRequest.responseJSON;
		 }else{
		 	 try{
		 	 	responseJSON = JSON.parse(xmlHttpRequest.responseText)
		 	 }catch(e){
		 	 	
		 	 }
		 	 
		 }
		 isTipError && message.error(responseJSON.msg_show || '操作异常');
		 dfd.reject(responseJSON, xmlHttpRequest.status);
		 
	}
	if(option.showLoading !== false){
		 config.beforeLoad(dispatch);
	}

	
	if(process.env.NODE_ENV == 'test'){
		option.headers = {
			"Authorization": 'GRJWT eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImxpY2hhbyIsInVzZXJfaWQiOjYsImVtYWlsIjoibGljQGdvb2RyYWluLmNvbSIsImV4cCI6MTUxNzQ2NDY3M30.frHCOEpR9B-hwWcrcwMwBPNl9VAS9LH2XtKRHehai2A',
			"X-CSRFToken": cookie.get('csrftoken')
		};
	}else if(process.env.NODE_ENV == 'production'){
		option.headers = {
			"Authorization": userToken,
			"X-CSRFToken": cookie.get('csrftoken')
		};
	}

	if(option.cache === undefined){
		//不缓存
		option.cache = false;
	}
     
	 
	$.ajax(option);
	return dfd;
 }




 http.setToken = (token) => {
 	userToken = 'GRJWT ' +token;
 }
 http.removeToken = () => {
 	userToken = '';
 }

 http.getToken = () => {
 	return userToken;
 }

 export default http;