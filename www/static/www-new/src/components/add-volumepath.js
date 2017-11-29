/*
	应用添加存储
*/
import widget from '../ui/widget';
import { changeGroup } from '../comms/app-apiCenter';
var tmp = require('./add-volumepath-tpl.html');
const Msg = widget.Message;
function noop(){}


widget.define('addVolumepath', {
	extend: 'dialog',
	_defaultOption: {
        width: '600px',
        height: '350px',
        title: '添加持久化目录',
        onOk: noop,
        serviceInfo: {}
	},
	_init:function(option){
		var self = this;
        this.callParent(option);
        if(this.ClassName == 'addVolumepath'){
            this._create();
            this.bind();
        }
    },
    _create: function(){
    	this.callParent();
    	this.setContent(tmp);
        this.getElement().find('.fn-tips').tooltip();

        //无状态服务
        if(this.option.serviceInfo.extend_method === 'stateless'){
            this.element.find('.local-radio').hide();
        }
    },
    onOk: function(volume_name, volume_path, volume_type){
        this.option.onOk && this.option.onOk(volume_name, volume_path, volume_type)
    },
    destroy:function() {
    	this.unbind();
    	this.callParent();
    },
    bind: function(){
        this.callParent();
        var self = this;
        var element = this.getElement();
        element.delegate('.btn-success', 'click', function(e){
            //提交持久化目录
            var volume_name = element.find("#volume_name").val();
            if (volume_name == "") {
                Msg.warning("持久化名称不能为空!");
                return false;
            }

            var volume_path = element.find("#volume_path").val();
            if (volume_path == "") {
                Msg.warning("持久化路径不能为空!");
                return false;
            }

            var volume_type = element.find("[name=volume_type]:checked").val();
            self.onOk(volume_name, volume_path, volume_type);
        })


    },
    unbind: function(){
        this.getElement().undelegate();
    }
})




