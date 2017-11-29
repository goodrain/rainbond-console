/*
	修改应用分组组件
*/
import widget from '../ui/widget';
import { changeGroup } from '../comms/app-apiCenter';
function noop(){}

const editGroup = widget.define('editGroup', {
	extend: 'dialog',
	_defaultOption: {
		onSuccess: noop,
		onFail: noop,
		onCancel: noop,
		groupId:'',
		groupName:'',
		tenantName:'',
        width: '400px',
        height: '200px',
		serviceName: '',
		serviceId:'',
		groupList:[]
	},
	_init:function(option){
		var self = this;
		option.domEvents = {
			'.btn-success click': function() {
				self.onOk();
			}
		}

        this.callParent(option);
        if(this.ClassName == 'editGroup'){
            this._create();
            this.bind();
        }
    },
    _create: function(){
    	this.callParent();
    	this.form = widget.create('form', {
            hideLabel: true,
    		items:[{
    			type: 'select',
    			name: 'group',
    			items: this.option.groupList,
    			value: this.groupId
    			
    		}]
    	})
    	this.setTitle("修改群组 "+ this.option.serviceName);
    	this.setContent(this.form.getElement());
    },
    onOk: function(){
    	var self = this, newGroupId = this.form.getValue('group');
    	if(newGroupId) {
    		changeGroup(
    			this.option.tenantName,
    			this.option.serviceId,
    			newGroupId
    		).done(function(){
    			self.option.onSuccess();
    			self.destroy();
    		})
    	}
    },
    destroy:function() {
    	this.form.destroy();
    	this.callParent();
    }
})

export default editGroup;



