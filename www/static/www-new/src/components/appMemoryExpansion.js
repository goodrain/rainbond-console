/*
	单个应用内存扩容
*/
import widget from '../ui/widget';
import { 
    appMemoryMonthlyExpansionInfo,
    postMemoryMonthlyExpansion
} from '../comms/app-apiCenter';
function noop(){}

widget.define('appMemoryExpansion', {
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
        if(this.ClassName == 'appMemoryExpansion'){
            this._create();
            this.bind();
        }
    },
    _create: function(){
    	this.callParent();
    	var self = this;
       appMemoryMonthlyExpansionInfo(
            self.option.tenantName,
            self.option.serviceAlias
        ).done(function(data){
            self.showMemoryExpansionDialog(data);
        })
    },
    showMemoryExpansionDialog: function(data){

        var $showNodeNum = null;
        //节点数input
        var $nodeNumInput = null;

        //显示内存数
        var $showMemory = null;
        var $memoryInput = null;
        var $showMoney = null;

        //根据选择的内存数 计算要提交的内存数， 如果大于1024M 则取1024的整数倍， 即向上取正到GB
        function computedMemory(memory) {
            if(memory < 1024 ){
                return memory;
            }else{
                return Math.floor(memory/1024) * 1024;
            }
        }

        //计算要显示的内存数,  带单位
        function computedShowMemory(memory){
            if(memory < 1024 ){
                return memory +' M';
            }else{
                return Math.floor(memory/1024) + ' G';
            }
        }

        //计算要显示的金额
        function computedMoney() {
            var memory = computedMemory($memoryInput.val());
            var nodeNum = data.canSetNodeNums ? $nodeNumInput.val() : 1;
            var money = ( nodeNum * memory - data.minMemory ) * data.unitMoney;
            $showMoney.html(money.toFixed(2));
            return money;
        }

        var self = this;
        var form = widget.create('form', {
            rowNum: 1,
            items:[{
                label: '节点数',
                name: 'nodeNum',
                type:'info',
                value: '<input style="display:inline-block;width:60%" type="range" min="'+data.minNode+'" max="20" step="1" id="NodeNum" value="'+data.minNode+'" /><span><cite id="NodeText" class="text-success">'+data.minNode+'</cite>个</span>'
            },{
                label: '单节点内存',
                type:'info',
                value: '<input style="display:inline-block;width:60%" type="range" min="'+data.minMemory+'" max="'+data.maxMemory+'" step="128" id="OneMemory" value="'+data.minMemory+'" ／><span><cite id="OneMemoryText" class="text-success"></cite></span>'
            },{
                label: '新增费用',
                type:'info',
                name: 'money',
                value: '<span id="deployMoney" class="text-success">'+(data.payMoney || 0)+'</span><span>元（按当前包月时长计算）</span>'
            }]
        })

        var dialog = widget.create('dialog', {
            title: '增加内存包月额度',
            content: form.getElement(),
            height:'300px',
            btns:[{
                classes: 'btn btn-success',
                text: '确认付款'
            },{
                classes: 'btn btn-default btn-cancel',
                text: '取消'
            }],
            domEvents:{
                '.btn-success click': function(){
                    var payMoney = computedMoney();
                    if(payMoney <= 0) {
                        form.destroy();
                        dialog.destroy();
                        form = dialog = null;
                    }else{
                        postMemoryMonthlyExpansion(
                            self.option.tenantName,
                            self.option.serviceAlias,
                            computedMemory($memoryInput.val()),
                            $('#NodeNum').val()
                        ).done(function(){
                            form.destroy();
                            dialog.destroy();
                            form = dialog = null;
                            self.option.onSuccess();
                        })
                    }
                    
                },
                '#NodeNum input': function(){
                    if(!data.canSetNodeNums){ return };
                    $('#NodeText').html($('#NodeNum').val());
                    computedMoney();
                },
                '#OneMemory input': function(){
                    $('#OneMemoryText').html(
                        computedShowMemory(
                            computedMemory($('#OneMemory').val())
                        )
                    )
                    computedMoney();

                }
            }
        })

        var $dialog = dialog.getElement();
        $showMoney = $dialog.find('#deployMoney');
        //显示节点数
        $showNodeNum = $dialog.find('#NodeText');
        //节点数input
        $nodeNumInput = $dialog.find('#NodeNum');

        //显示内存数
        $showMemory = $dialog.find('#OneMemoryText');
        $memoryInput = $dialog.find('#OneMemory');
        //初始化显示内存数
        $showMemory.html(computedShowMemory(data.minMemory));

        //如果不能设置节点数量
        if(!data.canSetNodeNums){
            form.hideInput('nodeNum');
        }

        if(!data.showMoney){
            form.hideInput('money');
        }
    }
})




