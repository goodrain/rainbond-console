/*
	应用添加共享存储
*/
import widget from '../ui/widget';
import { connectAppDisk } from '../comms/app-apiCenter';
import volumeUtil from '../utils/volume-util';
const Msg = widget.Message;

function noop(){}

widget.define('addSharedVolumepath', {
	extend: 'dialog',
	_defaultOption: {
		onSuccess: noop,
		onFail: noop,
		onCancel: noop,
        width: '650px',
        height: '400px',
        title: '请选择要挂载的目录',
        tenantName:'',
        serviceAlias:'',
        //应用列表
        serviceList:[],
        //已经挂载的serviceIds
        mntServiceIds:[],
        //要添加到的应用别名
        serviceAlias:''
	},
	_init:function(option){
		var self = this;
		option.domEvents = {
			'.btn-success click': function() {
				self.onOk();
			}
		}

        this.callParent(option);
        if(this.ClassName == 'addSharedVolumepath'){
            this._create();
            this.bind();
        }
    },
    _create: function(){
    	this.callParent();
        var datas = [];
        for(var i=0;i<this.option.serviceList.length;i++){
            if(this.option.serviceList[i].service_alias != this.otpion.serviceAlias &&
                 this.option.mntServiceIds.indexOf(this.option.serviceList[i].service_id) < 0){
                datas.push(this.option.serviceList[i]);
            }
        }

    	this.table = widget.create('tableList', {
            showPage: true,
            pageSize:8,
            url:'/ajax/'+this.option.tenantName + '/' +this.option.serviceAlias  +'/dep-mnts',
            columns:[{
                name: 'dep_vol_name',
                text: '持久化名称',
                width: 150
            },{
                name: 'dep_vol_path',
                text: '持久化目录'
            },{
                name: 'dep_vol_type',
                text: '持久化类型'
            },{
                name: 'dep_app_name',
                text: '所属应用'
            },{
                name: 'dep_app_group',
                text: '所属群组'
            }],
            render: {
                dep_vol_type: function(text,data){
                    return volumeUtil.getTypeCN(text);
                }
            }
    	})

    	this.setContent(this.table.getElement());
    },
    onOk: function(){
        var volumeIds = this.table.getSelectedArrayByKey('dep_vol_id');
        if(!volumeIds.length){
            Msg.warning("请选择要挂载的持久化目录");
            return;
        }
        connectAppDisk(
            this.option.tenantName,
            this.option.serviceAlias,
            volumeIds
        ).done((data) => {
            this.option.onOk && this.option.onOk();
            this.destroy();
        }).fail((data) => {
            this.option.onFail && this.option.onFail();
            this.destroy();
        })
    },
    destroy:function() {
    	this.table.destroy();
        this.table = null;
    	this.callParent();
    }
})




