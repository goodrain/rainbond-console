/*
	包月日期选择组件, 根据业务封装
*/

import widget from '../ui/widget';
require('./monthly-time-select.css')

function noop(){}
widget.define('monthly-time-select', {
	_defaultOption: {
		tpl:'<div class="monthly-time-select"><span data-value="1">1</span><span data-value="2">2</span><span data-value="3">3</span><span data-value="4">4</span><span data-value="5">5</span><span data-value="6">6</span><span data-value="7">7</span><span data-value="8">8</span><span data-value="9">9</span><span data-value="10">10</span><span data-value="11">11个月</span><span data-value="12">1年</span><span data-value="24">2年</span></div>',
		value:1,
		onChange: noop,
		disabled: false
	},
	_init:function(option){
		this.callParent(option);
		if(this.ClassName == 'monthly-time-select'){
            this._create();
            this.bind();
        }
	},
	_create:function(){
		this.callParent();
		this.setValue(this.option.value || 1);
		if(this.option.disabled) {
			this.disable();
		}
	},
	disable:function(){
		this.disabled = true;
		this.element.addClass('disabled');
	},
	active:function(){
		this.disabled = false;
		this.element.removeClass('disabled');
	},
	getValue:function(){
		return this.value;
	},
	setValue:function(value){
		if(value <= 0){
			value = 1;
		}
		if(value > 12 && value < 24){
			value = 24;
		}
		if(value > 24){
			value = 24;
		}

		this.value = value;
		this.updateDom();
		this.option.onChange(this.value);
	},
	updateDom:function(){
		var $span = this.element.find('span'), value = this.value;
		$span.removeClass('active');
		$span.each(function(){
			var thisVal = Number($(this).attr('data-value'));
			if(thisVal <= value){
				$(this).addClass('active');
			}
		})
	},
	bind:function(){
		var self = this;
		this.element.delegate('span', 'click', function(){
			if(!self.disabled) {
				var val = Number($(this).attr('data-value'));
				if(self.value !== val){
					self.setValue(val);
				}
			}
		})
	}
})