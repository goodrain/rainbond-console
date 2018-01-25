
import widget from '../ui/widget';
var Msg = widget.Message;
var loading = widget.create('loadingbar');


function showLoading() {
	 loading.addRequest();
}

function hideLoading(){
	loading.removeRequest();
}


/*
 * 通用ajax服务
 * */

var filters = [];

String.prototype.format = function(){
	var args = arguments;
	return this.replace(/{{(\d)}}/g, function(e,c){
		return args[+c] === undefined ? '':args[+c];
	})
}
//用于配置
var config = window.httpConfig = {
		beforeLoad:function(msg){
			showLoading(msg);
		},
		afterLoad:function(msg){
			hideLoading();
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



function http(option){
	 option = option || {};
	 option.type = option.type || option.method || 'get';
	 var isTipError = option.isTipError == (void 0) ? true : option.isTipError;
	 option.timeout = option.timeout || 1000 * 20; //20秒超时
	 option.multiple = option.multiple || true;//已url为标示， 是否可以同一个请求没返回之前再次发起
	 if(option.multiple === false){
		 if(!ajaxIngCache.get(option.url)){
			 ajaxIngCache.add(option.url)
		 }else{
			 return {
				 done:function(){},
				 fail:function(){}
			 }
		 }
	 }
	 //promise对象
	 var dfd = $.Deferred();
	 option.success=function(data = {}){
		 ajaxIngCache.remove(option.url);
		 if(option.showLoading !== false){
			 config.afterLoad();
		 }


		 if(data.code  === void 0){
		 	dfd.resolve(data);
		 }else{
		 	
		 	if(data.code>=200 && data.code<300){
				 dfd.resolve(data.body || data.data || data);
			 }else{
				 if(isTipError === true){
					 Msg.warning(data.msgcn || data.msg_show || data.msg || '操作异常');
				 }
				 dfd.reject(data);   
			 }
		 }
		 
	 }
	 
	 option.error=function(xmlHttpRequest){
		 ajaxIngCache.remove(option.url);
		 if(option.showLoading !== false){
			 config.afterLoad();
		 }
		 if( isTipError ){
		 	var info = '';
		 	if(xmlHttpRequest.status == '403'){
		 		info = '您没有权限执行此操作!';
		 	}

		 	if(xmlHttpRequest.responseJSON) {
		 		info = xmlHttpRequest.responseJSON.info || xmlHttpRequest.responseJSON.desc;
		 	}
		 	Msg.danger(info || '网络异常， 请稍后重试!')
		 }
		 dfd.reject(xmlHttpRequest);
		 
	 }
	 if(option.showLoading !== false){
		 config.beforeLoad(config.waitMsg);
	 }
	 
	 if(option.cache === undefined){
		//不缓存
		 option.cache = false;
	 }

	 option.beforeSend = function (xhr, settings) {
          var csrftoken = $.cookie('csrftoken');
          xhr.setRequestHeader("X-CSRFToken", csrftoken);
     }

     option.data = option.data || {};
     var type = (option.type || '').toLowerCase();
     if (type != 'get'){
     	//option.data.csrfmiddlewaretoken = $.cookie('csrftoken');
     }
     
	 
	 $.ajax(option);
	 return dfd;
 }

 export default http;