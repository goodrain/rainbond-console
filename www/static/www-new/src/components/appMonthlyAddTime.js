/*
	单个应用增加时长
*/
import widget from '../ui/widget';
import { 
    getAppMonthlyInfo,
    appMonthlyAddTime
} from '../comms/app-apiCenter';

function noop(){}

widget.define('appMonthlyAddTime', {
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
        if(this.ClassName == 'appMonthlyAddTime'){
            this._create();
            this.bind();
        }
    },
    _create: function(){
    	this.callParent();
    	var self = this;
        getAppMonthlyInfo(
            self.option.tenantName,
            self.option.serviceAlias
        ).done(function(data){
            self.showMonthlyAddTimeDialog(data);
        })
    },
    //显示增加包月时长弹框
    showMonthlyAddTimeDialog: function(data) {
        var self = this;
        //包月一个月多少钱
        var oneMonthMoney = data.oneMonthMoney;
        //最后需要付款的钱
        var needPay = oneMonthMoney;
        var form = widget.create('form', {
            rowNum: 1,
            labelCol: 3,
            items:[{
                label: '包月时长',
                type: 'info',
                value: '<input type="range" min="1" max="24" step="1" id="TimeLong" value="1" style="display:inline-block;width:60%"><span><cite id="TimeLongText" class="text-success">1</cite>个月</span>'
            },{
                label: '费用总计',
                type: 'info',
                value: '<div><span id="TimeLongMoney" class="text-success">'+oneMonthMoney+'</span>元（按所有包月项目同步增加时长计算）</div>'
            }]
        })
        var dialog = widget.create('dialog', {
            title: '增加包月时长',
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
                    var monthNum = dialog.getElement().find('#TimeLong').val();
                    appMonthlyAddTime(
                        self.option.tenantName,
                        self.option.serviceAlias,
                        monthNum
                    ).done(function(data){
                        form.destroy();
                        dialog.destroy();
                        form = dialog = null;
                        self.option.onSuccess();
                    })
                },
                //当包月条长度变化时
                '#TimeLong input': function (){
                    needPay = (dialog.getElement().find('#TimeLong').val() * oneMonthMoney).toFixed(2);
                    $("#TimeLongMoney").html(needPay);
                    $('#TimeLongText').html(dialog.getElement().find('#TimeLong').val());
                }
            }
        })
    }
})




