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
        width: '900px',
        height: '500px',
        title: '挂载共享目录',
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
        var self = this;
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
                name: 'source_path',
                text: '本地持久化目录',
                width: 120
            },{
                name: 'tips',
                text: '',
                width: 80
            },{
                name: 'dep_vol_name',
                text: '目标持久化名称',
                width: 150
            },{
                name: 'dep_vol_path',
                text: '目标持久化目录',
                width: 150
            },{
                name: 'dep_vol_type',
                text: '目标持久化类型',
                width: 130
            },{
                name: 'dep_app_name',
                text: '目标所属应用',
                width: 100
            },{
                name: 'dep_app_group',
                text: '目标所属群组',
                width: 100
            }],
            event:{
                onSelectedChange: function(){
                   if(self.table){
                        var datas = self.table.getData(true);
                       for(var i=0;i<datas.length;i++){
                            var data = datas[i];
                            var uid = data.uuid;
                            var isSelect = data.selected;
                            var $tr = self.element.find('[uid='+uid+']');
                            if(isSelect){
                                $tr.find('[name=source-path]').prop('disabled', false)
                            }else{
                                $tr.find('[name=source-path]').prop('disabled', true)
                            }
                       }
                   }
                   
                }
            },
            render: {
                source_path: function(text, data){
                    return '<input disabled type="text" class="form-control" name="source-path" />'
                },
                tips: function(text, data){
                    return '<div style="text-align:center;font-size:18px"><span class="glyphicon glyphicon-resize-horizontal"></span></div>'
                },
                dep_vol_type: function(text,data){
                    return volumeUtil.getTypeCN(text);
                }
            }
    	})

    	this.setContent(this.table.getElement());
    },
    onOk: function(){
        var selecteds = this.table.getSelected(true);
        var sendData = [];
        if(!selecteds.length){
            Msg.warning("请选择要挂载的持久化目录");
            return;
        }

        var isAllSelected = true;
        for(var i=0;i<selecteds.length;i++){
            var $tr = this.element.find('[uid='+selecteds[i].uuid+']');
            var source_path = $.trim($tr.find('[name=source-path]').val());
            if(!source_path){
                Msg.warning("请填写本地持久化目录");
                $tr.find('[name=source-path]').focus();
                return;
            }

            sendData.push({
                id: selecteds[i].data.dep_vol_id, 
                path: source_path,
                app_name: selecteds[i].dep_app_name
            });
        }

        connectAppDisk(
            this.option.tenantName,
            this.option.serviceAlias,
            sendData
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




