/*
	单个应用包月
*/
import widget from '../ui/widget';
import { 
    getDiskMonthlyInfo,
    appDiskMonthly
} from '../comms/app-apiCenter';

function noop(){}

widget.define('appDiskMonthly', {
	_defaultOption: {
        tpl:'<div></div>',
		onSuccess: noop,
		onFail: noop,
		onCancel: noop,
		tenantName:'',
        serviceAlias:''
	},
	_init:function(option){
		var self = this;
        this.callParent(option);
        if(this.ClassName == 'appDiskMonthly'){
            this._create();
            this.bind();
        }
    },
    _create: function(){
    	this.callParent();
    	var self = this;
        getDiskMonthlyInfo(
            self.option.tenantName,
            self.option.serviceAlias
        ).done(function(data){
            self.showDiskMonthlyDialog(data, data.choosable);

        })
    },
    //显示硬盘包月弹框
    showDiskMonthlyDialog: function(data, choosable){
        var self = this;
        var unitMoney = choosable ? data.oneMonthOneGmoney : data.oneGmoney;
        var needPay = unitMoney;

        //创建表单
        var form = widget.create('form', {
            rowNum: 1,
            items:[{
                label: '包月时长',
                type: 'info',
                name: 'monthInfo',
                value: '<p class="the_same text-danger">磁盘与内存包月时长应保持一致，剩余时间<span  class="text-success">'+data.remainDay+'</span>天<span  class="text-success">'+data.remainHour+'</span>小时</p>'
            },{
                label: '包月时长',
                type: 'info',
                name: 'monthInput',
                value: '<input style="display:inline-block;width:60%" type="range" min="1" max="24" step="1" id="LongDisk" value="1"><span><cite id="LongDiskText" class="text-success">1</cite>个月</span>'
            },{
                label: '包月额度',
                type: 'info',
                value: '<input style="display:inline-block;width:60%" type="range" min="1" max="200" step="1" id="LongDiskSize" value="1"><span><span><cite id="DiskSizeText" class="text-success">1</cite>G</span>'
            },{
                label: '费用总计',
                type: 'info',
                value: '<span id="LongDiskMoney" class="text-success">'+ needPay +'</span>元'
            }]
        })
        //创建弹框
        var dialog = widget.create('dialog', {
            title: '购买磁盘包月',
            content: form.getElement(),
            height:'300px',
            btns:[{
                classes: 'btn btn-success',
                text: '确认付款'
            },{
                classes: 'btn btn-default btn-cancel',
                text: '取消'
            }],
            domEvents: {
                //点击确认付款按钮
                '.btn-success click': function() {
                    
                    var $wrap = dialog.getElement();
                        var monthNum = $wrap.find('#LongDisk').val();
                        var diskSize = $wrap.find('#LongDiskSize').val();
                        appDiskMonthly(
                            self.option.tenantName,
                            self.option.serviceAlias,
                            diskSize,
                            monthNum
                        ).done(function(data){
                            form.destroy();
                            dialog.destroy();
                            form = dialog = null;
                            self.option.onSuccess();
                        })
                },
                //当包月条长度变化时
                '#LongDisk input': function() {
                    if(!choosable){
                        return;
                    }
                    var $wrap = dialog.getElement();
                    needPay = (unitMoney * $wrap.find('#LongDisk').val() * $wrap.find('#LongDiskSize').val()).toFixed(2);
                    $('#LongDiskText').html($wrap.find('#LongDisk').val())
                    $("#LongDiskMoney").html(needPay);
                },
                //硬盘大小变化时
                '#LongDiskSize input': function() {
                    var $wrap = dialog.getElement();
                    if(!choosable){
                        needPay = (unitMoney * $wrap.find('#LongDiskSize').val()).toFixed(2);
                    }else{
                        needPay = (unitMoney * $wrap.find('#LongDiskSize').val() * $wrap.find('#LongDisk').val()).toFixed(2);
                    }
                    

                    $("#LongDiskMoney").html(needPay);
                    $('#DiskSizeText').html($wrap.find('#LongDiskSize').val())
                }
            }
        })

        //按是否可以选择时长来隐藏显示form表单的某项
        if(choosable) {
            form.hideInput('monthInfo');
        }else{
            form.hideInput('monthInput');
        }
    }

})




