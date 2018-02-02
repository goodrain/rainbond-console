import createPageController from '../utils/page-controller';
import {
	appBatchDiskWithTime,
	getNotInstalledPlugin
} from '../comms/app-apiCenter';
import { getCanReceiveLogApp } from '../comms/apiCenter';
import { 
	installPlugin, 
	getInstalledPluginConfig, 
	unInstallPlugin,
	disablePlugin,
	activePlugin,
	updatePluginVal,
	updatePluginToNew
} from '../comms/plugin-apiCenter';
import widget from '../ui/widget';
var artTemplate = require('art-template/lib/template-web.js');
const Msg = widget.Message;

var typeMap = {
	'downstream_port': '下游应用端口',
	'upstream_port': '应用端口',
	'un_define': '不依赖'
}

var injectTypeMap = {
	'env': '环境变量',
	'auto': '主动发现'
}

widget.define("plugin_group_item_fields", {
	_defaultOption:{
		tpl:'<form class="plugin_group_item_fields form-horizontal"></form>',
		attrs:[]
	},
	_init: function(option){
		this.callParent(option);
		if(this.ClassName === 'plugin_group_item_fields'){
			this._create();
		}
	},
	_create: function(){
		this.callParent();
		var element = this.getElement();
		var html = [];
		for(var i=0;i<this.option.attrs.length;i++){
			
			var item = this.option.attrs[i];
			html.push('<div class="form-group" overflow:hidden; style="overflow:hidden;">')
			html.push('<label title="'+item.attr_name+'" class="form-label ws-nowrap">'+item.attr_name+': </label>');
			html.push('<div class="form-input fn-tips"  data-toggle="tooltip" data-placement="top" title="'+(item.attr_info || '')+'">')
			switch(item.attr_type){
				case 'string':
				   html.push('<input name="'+item.attr_name+'" class="form-control input-sm" value="'+(item.attr_value || item.attr_default_value || '')+'"  type="text" '+(!item.is_change ? 'disabled=disabled' : "")+' />');
				   break;
				case 'radio' :
				   html.push('<select class="form-control" '+(!item.is_change ? 'disabled=disabled' : "")+' name="'+item.attr_name+'">')
				   var alt_value = item.attr_alt_value.split(',');
				   for(var j=0;j<alt_value.length;j++){
				   	    var val = alt_value[j];
				   	    var checked =  false;
				   	    if(item.attr_value){
				   	    	if(item.attr_value === val){
				   	    		checked =  true
				   	    	}
				   	    	
				   	    }else{
				   	    	if(item.attr_default_value === val){
				   	    		checked =  true
				   	    	}
				   	    }
				   	    html.push('<option value="'+val+'" '+(checked ? 'selected=selected' : '')+' >'+(val)+'</option>')
				   }
				   html.push('</select>')
				   break;
				case 'checkbox' :
				   html.push('<select multiple="multiple" class="form-control" '+(!item.is_change ? 'disabled=disabled' : "")+' name="'+item.attr_name+'">')
				   var alt_value = item.attr_alt_value.split(',');
				   for(var j=0;j<alt_value.length;j++){
				   	    var val = alt_value[j];
				   	    var checked =  false;
				   	    if(item.attr_value){
				   	    	var itemValue = item.attr_value.split(',')
				   	    	if(itemValue.indexOf(val) > -1){
				   	    		checked =  true
				   	    	}
				   	    }else if(item.attr_default_value){
				   	    	var itemValue = item.attr_value.split(',')
				   	    	if(itemValue.indexOf(val) > -1){
				   	    		checked =  true
				   	    	}
				   	    }
				   	    html.push('<option value="'+val+'" '+(checked ? 'selected=selected' : '')+' >'+(val)+'</option>')
				   }

				   html.push('</select>')
				   break;

			}
			html.push('</div>')
			html.push('</div>')

		}
		element.html(html.join(''));
		
	}
})

widget.define('plugin_group_downstream_port', {
	_defaultOption:{
		tpl:'<dl class="plugin_group_item_tpl">'+
		'<dt class="table table-bordered"><span class="item-label">下游应用: <span class="target_service"></span></span><span class="item-label">端口号: <span class="port"></span></span><span class="item-label">端口协议: <span class="protocol"></span></span><dt>'+
		'<dd class="fields"></dd>'+
		'</dl>',
		config:{}
	},
	_init:function(option){
		this.callParent(option);
		if(this.ClassName == 'plugin_group_downstream_port'){
            this._create();
            this.bind();
        }
	},
	_create:function(){
		this.callParent();
		var element = this.getElement();
		
		element.find('.type').html(typeMap[this.option.config.service_meta_type]);
		element.find('.target_service').html(this.option.config.dest_service_cname);
		element.find('.port').html(this.option.config.port);
		element.find('.protocol').html(this.option.config.protocol);
		element.find('.fields').html(
			widget.create('plugin_group_item_fields', {attrs: this.option.config.config}).getElement()
		)
	},
	bind:function(){

	}
})


widget.define('plugin_group_upstream_port', {
	_defaultOption:{
		tpl:'<dl class="plugin_group_item_tpl">'+
		'<dt><span class="item-label">端口号: <span class="port"></span></span><span class="item-label">端口协议: <span class="protocol"></span></span><dt>'+
		'<dd  class="fields"></dd>'+
		'</dl>',
		config:{}
	},
	_init:function(option){
		this.callParent(option);
		if(this.ClassName == 'plugin_group_upstream_port'){
            this._create();
            this.bind();
        }
	},
	_create:function(){
		this.callParent();
		var element = this.getElement();
		element.find('.type').html(typeMap[this.option.config.service_meta_type]);
		element.find('.port').html(this.option.config.port);
		element.find('.protocol').html(this.option.config.protocol);
		element.find('.fields').html(
			widget.create('plugin_group_item_fields', {attrs: this.option.config.config}).getElement()
		)
	},
	bind:function(){

	}
})

widget.define('plugin_group_un_define', {
	_defaultOption:{
		tpl:'<dl class="plugin_group_item_tpl">'+
		'<dt><span class="item-label">注入方式: <span class="type"></span></span><dt>'+
		'<dd class="fields"></dd>'+
		'</dl>',
		config:{}
	},
	_init:function(option){
		this.callParent(option);
		if(this.ClassName == 'plugin_group_un_define'){
            this._create();
            this.bind();
        }
	},
	_create:function(){
		this.callParent();
		var element = this.getElement();
		element.find('.type').html(injectTypeMap[this.option.config.injection]);
		element.find('.fields').html(
			widget.create('plugin_group_item_fields', {attrs: this.option.config.config}).getElement()
		)
	},
	bind:function(){

	}
})


widget.define("plugin_group",{
	_defaultOption:{
		tpl:'<div class="plugin_group_tpl"></div>',
		pluginId:'',
		config_group:[]
	},
	_init:function(option){
		this.callParent(option);
		if(this.ClassName == 'plugin_group'){
            this._create();
            this.bind();
        }
	},
	_create:function(){
		this.callParent();
		var element = this.getElement();
		for(var i=0;i<this.option.config_group.length;i++){
			var item = this.option.config_group[i];
			var ele = widget.create("plugin_group_"+item.service_meta_type, {config: item}).getElement();
			element.append(ele);
		}

	},
	bind:function(){

	}
})

/*
	从dom中获取配置值，并更新到数据
*/
function updateConfigGroup($dom, config_group=[]){
	for(var i=0;i<config_group.length;i++){
		var item = config_group[i];
		var config = item.config || [];
		var $groupItem = $dom.find('.plugin_group_item_tpl').eq(i);
		for(var j=0;j<config.length;j++){
			var currConfig = config[j];
			//如果该配置允许修改， 获取最新的值
			if(currConfig.is_change){
				var $currConfig = $groupItem.find('.form-group');
				if(currConfig.attr_type === 'string'){

					currConfig.attr_value = $currConfig.find('[name='+currConfig.attr_name+']').val();
					
				}
				if(currConfig.attr_type === 'radio'){
					currConfig.attr_value = $currConfig.find('[name='+currConfig.attr_name+']').val();
				}
				if(currConfig.attr_type === 'checkbox'){
					var val = [];

					$currConfig.find('[name='+currConfig.attr_name+'] option').each((index, item) => {
						if(item.selected){
							val.push(item.value);
						}
					});
					currConfig.attr_value  = val.join(',');

				}
			}
		}
		item.config = config;
	}
}





/* 应用插件 */
const AppPlugin = createPageController({

	property: {
		tenantName:'',
		serviceAlias:'',
		serviceId:'',
		socket: null,
		instanceId: '',
		//应用状态控制
		status: 'start',
		//应用是否已经设置了日志输出
		isAppLogOutput: false,
		renderData:{
			appInfo:{},
			pageData:{relations:[], un_relations:[]}
		}
	},
	method: {
		//获取页面初始化数据
		getInitData: function(){
			var self = this;
			return getNotInstalledPlugin(
				this.tenantName,
				this.serviceAlias
			).done((data)=> {
				self.renderData.pageData = data;
				if(!self.renderData.pageData.relations.length && 
					!self.renderData.pageData.un_relations.length
					){
					$('#plugin-list-empty').show();
				}else{
					$('#plugin-list-empty').hide();
					self.renderRelationPlugin();
				    self.renderUnrelationPlugin();
				}
				
			})
		},
		renderRelationPlugin: function(){
			$('#relation-plugin').html('');
			var relations = this.renderData.pageData.relations || [];
			var html = [];
			for(var i=0;i<relations.length;i++){
				
				html.push(artTemplate.compile($('#relation-plugin-tpl').html())(relations[i]))
			}
			$("#relation-plugin").html(html.join(''));
		},
		renderUnrelationPlugin: function(){
			$('#unrelation-plugin').html('');
			var un_relations = this.renderData.pageData.un_relations || [];
			var html = [];
			for(var i=0;i<un_relations.length;i++){
				html.push(artTemplate.compile($('#unrelation-plugin-tpl').html())(un_relations[i]))
			}
			$("#unrelation-plugin").html(html.join(''));
		},
		installPlugin: function(pluginId, version){
			installPlugin(
				this.renderData.tenantName,
				this.renderData.serviceAlias,
				pluginId,
				version
			).done((data)=>{
				this.getInitData();
				Msg.success("安装成功");
			})
		},
		getRelationPluginFromPageData:function(pluginId){
			var plugins = this.renderData.pageData.relations ||[];
			if(plugins.length){
				for(var i=0;i<plugins.length;i++){
					if(plugins[i].plugin_id === pluginId){
						return plugins[i];
					}
				}
			}
			return null;
		},
		getUnRelationPluginFromPageData:function(pluginId){
			var plugins = this.renderData.pageData.un_relations ||[];
			if(plugins.length){
				for(var i=0;i<plugins.length;i++){
					if(plugins[i].plugin_id === pluginId){
						return plugins[i];
					}
				}
			}
			return null;
		},
		getRelationPluginConfigInfo: function(pluginId, version){
		
			var plugin = this.getRelationPluginFromPageData(pluginId);
			if(plugin){

				getInstalledPluginConfig(
					this.renderData.tenantName,
					this.renderData.serviceAlias,
					pluginId,
					version
				).done((data) => {
					var $dom = $('[data-plugin-id='+pluginId+']');
					if(data.bean){
						$dom.find('.plugin_version').html(version);
						$dom.find('.plugin_version_info').html(data.bean.build_info);
						$dom.find('.plugin_version_memory').html(data.bean.memory || 0 );
						$dom.find('.plugin_create_time').html((data.bean.create_time || '').split('T').join(' '));
					}

					if(data.list && data.list.length){
						plugin.config_group = data.list;
						$dom.find('.update-config').show();
						$dom.find('.config-body').html(widget.create('plugin_group',{
							plugin_id: pluginId,
							config_group: data.list
						}).getElement())
						$('.fn-tips').tooltip();

					}else{
						$dom.find('.update-config').hide();
					}


					

				})

			}

			
		},
		uninstallPlugin: function(pluginId){
			unInstallPlugin(
				this.renderData.pageData.tenantName,
				this.renderData.pageData.serviceAlias,
				pluginId
			).done((data) => {
				this.getInitData();
				Msg.success("卸载成功");
			})
		},
		disablePlugin: function(pluginId){
			return disablePlugin(
				this.renderData.pageData.tenantName,
				this.renderData.pageData.serviceAlias,
				pluginId
			)
		},
		activePlugin: function(pluginId){
			return activePlugin(
				this.renderData.pageData.tenantName,
				this.renderData.pageData.serviceAlias,
				pluginId
			)
		},
		updatepluginVal: function(data){
			data = JSON.stringify(data);
			
			updatePluginVal(
				this.renderData.pageData.tenantName,
				this.renderData.pageData.serviceAlias,
				data
			).done((data) => {
				Msg.success("修改成功")
			})
		},
		getConfigDatafromDom: function(pluginId){
			var $dom = $('.relation-plugin[data-plugin-id='+pluginId+']');
			var pluginData = this.getRelationPluginFromPageData(pluginId);
			var data = {};
			if($dom.length && pluginData){
				data.plugin_id = pluginData.plugin_id;
				data.service_id = this.serviceId;
				data.config_group = pluginData.config_group;
				updateConfigGroup($dom, data.config_group);
			}
			return data;
		},
		handleUpdateToNew: function(pluginId){
			return updatePluginToNew(
				this.renderData.pageData.tenantName,
				this.renderData.pageData.serviceAlias,
				pluginId
			).done(() => {
				Msg.success("更新成功");
			})
		}
	},
	domEvents: {
		//安装插件
		'.install-plugin click': function(e) {
			var $target = $(e.currentTarget);
			var $parent = $target.parents('.unrelation-plugin');
			var pluginId = $parent.attr('data-plugin-id');
			var version = $parent.attr('data-plugin-version');
			this.installPlugin(pluginId, version);
		},
		//插件插件详情
		'.to-open click': function(e){
			var $target = $(e.currentTarget);
			var $parent = $target.parents('.relation-plugin');
			var pluginId = $parent.attr('data-plugin-id');
			var version = $parent.attr('data-plugin-version');
			this.getRelationPluginConfigInfo(pluginId, version);
			$parent.attr('data-status', 'opened');
			//$target.remove();
		},
		//收起插件详情
		'.to-close click': function(e){
			var $target = $(e.currentTarget);
			var $parent = $target.parents('.relation-plugin');
			$parent.attr('data-status', 'closed');
			//$target.remove();
		},
		//卸载插件
		'.uninstall click': function(e){
			var $target = $(e.currentTarget);
			var $parent = $target.parents('.relation-plugin');
			var pluginId = $parent.attr('data-plugin-id');
			this.uninstallPlugin(pluginId);
		},
		//停用插件
		'.disablePlugin click': function(e){
			var $target = $(e.currentTarget);
			var $parent = $target.parents('.relation-plugin');
			var pluginId = $parent.attr('data-plugin-id');
			this.disablePlugin(pluginId).done(() => {
				$parent.find('.activePlugin').show();
				$parent.find('.disablePlugin').hide();
			})
			
		},
		//启用插件
		'.activePlugin click': function(e){
			var $target = $(e.currentTarget);
			var $parent = $target.parents('.relation-plugin');
			var pluginId = $parent.attr('data-plugin-id');
			this.activePlugin(pluginId).done(()=> {
				$parent.find('.activePlugin').hide();
				$parent.find('.disablePlugin').show();
			})
		},
		//更新插件配置
		'.update-config click': function(e){
			var $target = $(e.currentTarget);
			var $parent = $target.parents('.relation-plugin');
			var pluginId = $parent.attr('data-plugin-id');
			var version = $parent.attr('data-plugin-version');
			var data = this.getConfigDatafromDom(pluginId);
			this.updatepluginVal(data)
		},
		//更新单个配置
		'.js-update-field click': function(e){
			var $target = $(e.currentTarget);
			var $parent = $target.parents('.relation-plugin');
			var pluginId = $parent.attr('data-plugin-id');
			var version = $parent.attr('data-plugin-version');
			var configIndex = $target.parents('.form-group').index();
			var groupIndex = $target.parents('.plugin_group_item_tpl').index();
			var data = this.getConfigDatafromDom(pluginId);
			var sendData = $.extend(true, {}, data);
			sendData.config_group = sendData.config_group[groupIndex];
			sendData.config_group.config = sendData.config_group.config[configIndex];
			this.updatepluginVal(sendData);
			
		},
		//去创建插件
		'.to-create click': function(e){
			location.href="/plugins/"+this.renderData.tenantName;
		},
		//更新到最新版本
		'.update-to-newversion click': function(e){
			var $target = $(e.currentTarget);
			var $parent = $target.parents('.relation-plugin');
			var pluginId = $parent.attr('data-plugin-id');
			this.handleUpdateToNew(pluginId).done(() => {
				$parent.find('.update-to-newversion').hide();
				this.getRelationPluginConfigInfo(pluginId, data.bean.build_version.build_version);
				$parent.attr('data-plugin-version', data.bean.build_version.build_version);
				var plugin = this.getRelationPluginFromPageData(pluginId);
				if(plugin){
					plugin.version_info.build_version = data.bean.build_version.build_version;
				}
			})
		}
	},
	onReady: function(){
		this.renderData.tenantName = this.tenantName;
		this.renderData.serviceAlias = this.serviceAlias;
		this.getInitData().done(() => {
			
		})
		
	}
})

window.AppLogController = AppPlugin;
export default AppPlugin;