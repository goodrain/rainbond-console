var artTemplate = require('art-template/lib/template-web.js');



var dateFormat = artTemplate.defaults.imports.dateFormat = function(date, format) {
	var date = new Date(date);
	var map = {
		yyyy: function(){
			return date.getFullYear()
		},
		MM: function(){
			var val = date.getMonth() + 1;
			return val < 10 ? '0'+val : val;
		},
		dd: function(){
			var val = date.getDate();
			return val < 10 ? '0'+val : val;
		},
		hh: function(){
			var val = date.getHours();
			return val < 10 ? '0'+val : val;
		},
		mm: function() {
			var val = date.getMinutes();
			return val < 10 ? '0'+val : val;
		},
		ss: function(){
			var val = date.getSeconds();
			return val < 10 ? '0'+val : val;
		}
	}
	for(var k in map){
		format = format.replace(k, map[k]);
	}
	return format;
}

/*
	根据日期返回今天，昨天，前天，或者日期
*/
var dateToCN =  artTemplate.defaults.imports.dateToCN = function(date, format) {
	
	
	//是否是昨天
	function isToday(str) {
	    var d = new Date(str);
	    var todaysDate = new Date();
	    if (d.setHours(0, 0, 0, 0) == todaysDate.setHours(0, 0, 0, 0)) {
	        return true;
	    } else {
	        return false;
	    }
	}


	//是否昨天
	function isYestday(date){
		var d = new Date(date);
		var date = (new Date());    //当前时间
	    var today = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime(); //今天凌晨
	    var yestday = new Date(today - 24*3600*1000).getTime();
	    return d.getTime() < today && yestday <= d.getTime();
	}
	//是否是前天
	function isBeforeYestday(date){
		var d = new Date(date);
		var date = (new Date());    //当前时间
	    var today = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime(); //今天凌晨
	    var yestday = new Date(today - 24*3600*1000).getTime();
	    var beforeYestday = new Date(today - 48*3600*1000).getTime();
	    return d.getTime() < yestday && beforeYestday <= d.getTime();
	}


	function getShowData(date){
		if(isToday(date)){
			return '今天';
		}else if(isYestday(date)){
			return '昨天';
		}else if(isBeforeYestday(date)){
			return '前天';
		}
		return dateFormat(date, format);
	}
	return getShowData(date)
}

function noop (){};
/*
	定制页面控制器的方法
*/

var privates = {
	_init: 1,
	_initProperty: 1,
	_initMethod: 1,
	ready: 1,
	_bindEvent: 1,
	_initOwn: 1
}

function createPageController(option = {}){

	function PageController(ownOption = {}){
		option = option || {};
		//控制器的dom作用域范围
		this.$wrap = ownOption.$wrap || option.$wrap || $(document.body);
		//绑定事件配置对象
		this.domEvents = option.domEvents || {};
		//绑定
		this.onReady = option.onReady || noop;
		this.property = option.property || {};
		this.method = option.method || {};
		this.ownOption = ownOption;
		this.renderData = option.renderData || {};
		this.template = ownOption.template || option.template || '';
		this._init();
	}

	PageController.prototype = {
		constructor: PageController,
		_init:function(){
			this._initProperty();
			this._initMethod();
			this._initOwn();
		},
		onReady:noop,
		_initProperty:function(){
			for(var key in this.property){
				if(!privates[key]){
					this[key] = this.property[key];
				}
				
			}
			delete this.property;
		},
		_initMethod:function(){
			for(var key in this.method){
				if(!privates[key]){
					this[key] = this.method[key];
				}
			}
			delete this.method;
		},
		_initOwn:function(){
			for(var key in this.ownOption){
				if(!privates[key]){
					this[key] = this.ownOption[key];
				}
			}
			delete this.ownOption;
		},
		ready:function(){
			var self = this;
			$(function(){
				self.onReady.call(self);
			})
			this._bindEvent();
		},
		render:function(template){
			var tmp = template || this.template;
			if(tmp){
				this.$wrap.html(artTemplate.compile(tmp)(this.renderData))
			}
		},
		complileTpl: function(template, data){
			if(template && data){
				return artTemplate.compile(template)(data);
			}
			return '';
		},
		_bindEvent:function(){
			var self = this;
			for(var key in this.domEvents){
				if(this.domEvents.hasOwnProperty(key)){
					var selector = key.split(' ')[0];
					var type = key.split(' ')[1];
					var handle = this.domEvents[key];
					(function(selector, type, handle){
						self.$wrap.delegate(selector, type, function(e){
							handle.call(self, e);
						});
					})(selector, type, handle)
					
				}
			}
			delete this.domEvents;
		}
	}
	return PageController;
}


export default createPageController;
