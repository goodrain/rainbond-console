
function noop (){};
/*
	定制页面控制器的方法
*/

function createPageController(option){

	function PageController(ownOption){
		option = option || {};
		ownOption = ownOption || {};
		option = $.extend(true, {}, option, ownOption);
		//控制器的dom作用域范围
		this.$wrap = option.$wrap || $(document);
		//绑定事件配置对象
		this.domEvents = option.domEvents || {};
		//绑定
		this.onReady = option.onReady || noop;
		this.property = option.property || {};
		this.method = option.method || {};
		this._init();
	}

	PageController.prototype = {
		constructor: PageController,
		_init:function(){
			this._initProperty();
			this._initMethod();
		},
		onReady:noop,
		_initProperty:function(){
			for(var key in this.property){
				this[key] = this.property[key];
			}
			delete this.property;
		},
		_initMethod:function(){
			for(var key in this.method){
				this[key] = this.method[key];
			}
			delete this.method;
		},
		ready:function(){
			var self = this;
			$(function(){
				self.onReady.call(self);
			})
			this._bindEvent();
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
