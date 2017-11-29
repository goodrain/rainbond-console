/*
	单个应用包月
*/
import widget from '../ui/widget';
import { 
    getMemoryMonthlyInfo,
    appMemoryMonthly
} from '../comms/app-apiCenter';

function noop(){}

widget.define('appMemoryMonthly', {
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
        if(this.ClassName == 'appMemoryMonthly'){
            this._create();
            this.bind();
        }
    },
    _create: function(){
    	this.callParent();
    	var self = this;
        getMemoryMonthlyInfo(
            this.option.tenantName,
            this.option.serviceAlias
        ).done(function(data){
            //硬盘还没有选择包月时长， 内存可以选择的情况
            if(data.choosable){
                self.handleMemorySelectTimePay(data)
            }else{
                self.handleMemoryDirectPay(data);
            }
        })
    },
    //内存包月选择时长付款
    handleMemorySelectTimePay: function(data) {
        var self = this;
        //内存包月一个月多少钱
        var oneMonthMoney = data.oneMonthMoney;
        //最后需要付款的钱
        var needPay = oneMonthMoney;
        var form = widget.create('form', {
            rowNum: 1,
            items:[{
                label: '包月时长',
                type: 'info',
                value: '<input style="display:inline-block;width:60%" type="range" min="1" max="24" step="1" id="TimeLong" value="1"><span><cite id="TimeLongText" class="text-success">1</cite>个月</span>'
            },{
                label: '费用总计',
                type: 'info',
                value: '<span id="TimeLongMoney" class="text-success">'+oneMonthMoney+'</span>元'
            }]
        })
        var dialog = widget.create('dialog', {
            title: '购买内存包月',
            content: form.getElement(),
            height:'250px',
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
                    var monthNum = dialog.getElement().find('#TimeLong').val();
                    appMemoryMonthly(
                        self.option.tenantName,
                        self.option.serviceAlias,
                        monthNum,
                        needPay
                    ).done(function(data){
                        form.destroy();
                        dialog.destroy();
                        form = dialog = null;
                        self.option.onSuccess();
                    })
                },
                //当包月条长度变化时
                '#TimeLong input': function() {
                    needPay = (dialog.getElement().find('#TimeLong').val() * oneMonthMoney).toFixed(2);
                    $("#TimeLongMoney").html(needPay);
                    $('#TimeLongText').html($('#TimeLong').val())
                }
            }
        })
    },
    //内存包月不选择时长， 直接付款
    handleMemoryDirectPay: function(data) {
        var self = this;
        var form = widget.create('form', {
            rowNum: 1,
            items:[{
                label: '包月时长',
                type: 'info',
                value: '<p class="the_same text-danger">内存与磁盘包月时长应保持一致，剩余时间<span class="text-success day">'+data.remainDay+'</span>天<span  class="text-success hour">'+data.remainHour+'</span>小时</p>'
            },{
                label: '费用总计',
                type: 'info',
                value: '<span id="TimeLongMoney" class="text-success">'+data.toPayMoney+'</span>元'
            }]
        })
        var dialog = widget.create('dialog', {
            title: '购买内存包月',
            content: form.getElement(),
            height:'250px',
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
                    appMemoryMonthly(
                        self.option.tenantName,
                        self.option.serviceAlias,
                    ).done(function(data){
                        form.destroy();
                        dialog.destroy();
                        form = dialog = null;
                        self.option.onSuccess();
                    })
                }
            }
        })
    }
})




