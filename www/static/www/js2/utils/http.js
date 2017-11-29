(function(){

	var loadingTmp = '<div id="loadding" style="background:#000 url(/static/www/images/loadding.gif) center center no-repeat;opacity:0.6;position:fixed;left:0;top:0;right:0;bottom:0;z-index:999999999;"></div>'
	var $loadding = null;
	var Message = gWidget.Message;


	function showLoading() {
		 if(!$loadding){
		   $loadding = $(loadingTmp);
		   $('body').append($loadding);
		  }else{
		      $loadding.show();
		  }
	}

	function hideLoading(){
		 setTimeout(function(){
		    $loadding && $loadding.hide();
		 })
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
		 var isTipError = option.isTipError;
		 delete option.isTipError;
		 if(isTipError === undefined){
			 isTipError = true;
		 }
		 option = option || {};
		 option.type = option.type || 'get';
		 //option.dataType = option.type || 'json';
		 option.timeout = option.timeout || 180000;
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
		 var dtd = $.Deferred();
		 option.success=function(data){
			 ajaxIngCache.remove(option.url);
			 if(option.showLoading !== false){
				 config.afterLoad();
			 }
			 if(data){
				 for(var i=0;i<filters.length;i++){
					 var handle = filters[i];
					 if(handle(data) === false){
						 return;
					 }
				 }
				 if(data.code>=200 && data.code<300){
					 if(option.filter && $.isFunction(option.filter)){
						 data = option.filter(data);
					 }
					 dtd.resolve(data.body);
				 }else{
					 if(isTipError === true){
						 Message.danger(data.msgcn);
					 }
					 dtd.reject(data);   
				 }
			 }
		 }
		 
		 option.error=function(e){
			 ajaxIngCache.remove(option.url);
			 try{
				 dtd.reject(null, e);
				 config.afterLoad();
				 Message.danger("操作异常，请稍后重试！");
			 }catch(e){
				 
			 }finally{
				 
			 }
			 
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
		 
		 $.ajax(option);
		 return dtd;
	 }
	
	 window.http = http;
})();