//绑定域名事件
import widget from '../ui/widget';
import { getSertificate, addSertificate } from '../comms/apiCenter';
import { addDomain } from '../comms/app-apiCenter';
const Msg = widget.Message;

//绑定域名组件
widget.define('bindDomainForm', {
    extend: 'form',
    _defaultOption: {
        labelCol: 3,
        rowNum:1,
        items:[{
            name: 'protocol',
            label: '协议',
            type:'select',
            items:[{
                text:'HTTP',
                value:'http'
            },{
                text:'HTTPS',
                value:'https'
            },{
                text:'HTTP转HTTPS',
                value:'httptohttps'
            },{
                text:'HTTP与HTTPS共存',
                value:'httpandhttps'
            }]
            },{
                name: 'domain',
                type: 'text',
                label: '域名',
                required: true,
                requiredError: '请输入域名',
                regx: "^((www\\.)|([a-zA-Z0-9-_]+\\.)*)?([a-zA-Z0-9-_])+\\.([a-zA-Z]+)(:[0-9]+)?$",
                regxError: '域名格式不正确'
            },{
                name: 'keySelect',
                type: 'info',
                label: '选择已有证书',
                value:'<div class="keySelect-wrap text-left">'+
                            '<select name="savedKeys" class="form-control" style="display:inline-block;width:250px;margin-right: 10px;">'+
                            '</select>'+
                            '<span class="btn btn-primary btn-sm toAddZhengshu">新建证书</span>'+
                      '</div>'+
                      '<div class="keyCreate-wrap text-left" style="display:none;">'+
                        '<span class="text-danger" style="margin-right:10px;">您还没有创建证书，请先</span>'+
                        '<span class="btn btn-primary btn-sm toAddZhengshu">新建证书</span>'+
                       '</div>'
            }
        ]
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'bindDomainForm'){
            this._create();
            this.bind();
        }
    },
    _create: function(){
        this.callParent();
        this.hideInput('key');
        this.hideInput('license');
        this.hideInput('keySelect');
    },
    destroy:function(){
        this.callParent();
    }
})

//创建证书组件
widget.define('createCertificateForm', {
    extend: 'form',
    _defaultOption:{
        labelCol: 3,
        rowNum:1,
        items:[{
                name: 'alias',
                type: 'text',
                label: '证书名称',
                required: true,
                requiredError: '请输入证书名称'
            },{
                name: 'private_key',
                type: 'textarea',
                label:  'key',
                required: true,
                requiredError: '请输入key'
            },{
                name: 'certificate',
                type: 'textarea',
                label: '证书',
                required: true,
                requiredError: '请输入证书'
            }
        ]
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'createCertificateForm'){
            this._create();
            this.bind();
        }
    },
    destroy:function(){
        this.callParent();
    }
    
})



function noop(){}
widget.define('bindDomain', {
    extend: 'dialog',
    _defaultOption: {
        onSuccess: noop,
        onFail: noop,
        onCancel: noop,
        id: "createDomainDialog",
        title:'绑定域名',
        width:'600px',
        height: '400px',
        autoDestroy: true,
        //保存请求过来的证书
        savedKeys: [],
        //租户
        tenantName: '',
        //应用别名
        serviceAlias: '',
        //应用端口
        port: '',
        //应用id
        serviceId: '',
        btns:[
            {
                classes: 'btn btn-success addDomain',
                text: '确认绑定'
            },{
                classes: 'btn btn-success addzhengshu',
                text: '添加证书'
            },
            {
                classes: 'btn btn-default btn-cancel',
                text: '取消'
            },
            {
                classes: 'btn btn-default btn-back',
                text: '返回'
            }
        ]
    },
    _init:function(option){
        var self = this;
        var $element = this.element;
        option.domEvents = {
            //添加域名事件
            '.addDomain click': function(){
                self.handleAddDomain();
            },
            //添加证书事件
            '.addzhengshu click': function() {
                self.handleAddCertificate();
            },
            //去添加证书
            '.toAddZhengshu click': function() {
                self.toAddCertificate();
            },
            //添加证书返回事件
            '.btn-back click': function() {
                self.toAddDomain();
            },
            //协议切换事件
            '[name=protocol] change': function(){
                var protocol = self.bindDomainForm.getValue('protocol');
                if(protocol === 'http'){
                    self.bindDomainForm.hideInput('key');
                    self.bindDomainForm.hideInput('license');
                    self.bindDomainForm.hideInput('keySelect');
                }else{
                    self.bindDomainForm.showInput('key');
                    self.bindDomainForm.showInput('license');
                    self.bindDomainForm.showInput('keySelect');
                }
            }
        }



        this.callParent(option);
        if(this.ClassName == 'bindDomain'){
            this._create();
            this.bind();
        }
    },
    _create: function(){
        this.callParent();
        var self = this;
        this.bindDomainForm = widget.create('bindDomainForm', {
            onSubmit: function(){
                self.handleAddDomain();
            }
        })
        this.createCertificateForm = widget.create('createCertificateForm', {});
        this.setContent(this.bindDomainForm.getElement());
        this.appendContent(this.createCertificateForm.getElement());
        this.toAddDomain();
        this.getSertificate();
    },

    getSertificate: function() {
        var self = this;
        getSertificate(
            this.option.tenantName,
            this.option.serviceAlias
        ).done(function(list){
            self.option.savedKeys = list;
            self.renderSavedKeys();
        }).fail(function(){
            self.renderSavedKeys();
        })
    },
    handleAddDomain: function() {
        var form = this.bindDomainForm;
        var $element = this.element;
        if(!form.valid()) return;
        var keyId = $element.find('[name=savedKeys]').val();
        var protocol = form.getValue('protocol');
        var domain = $.trim(form.getValue('domain'));
        var self = this;
        if(!keyId && protocol !== 'http') {
            Msg.warning('请选择证书!');
            return;
        }
        addDomain(
            this.option.tenantName,
            this.option.serviceAlias,
            this.option.serviceId,
            this.option.port,
            domain,
            protocol, 
            keyId
        ).done(function(data){
            self.destroy();
            self.option.onSuccess(protocol, domain);
        })     
    },
    toAddDomain: function(){
        this.bindDomainForm.show();
        this.createCertificateForm.hide();
        this.element.find('.addDomain').show();
        this.element.find('.btn-cancel').show();
        this.element.find('.addzhengshu').hide();
        this.element.find('.btn-back').hide();
        this.createCertificateForm.reset();
    },
    handleAddCertificate: function() {
        var addLicenseForm = this.createCertificateForm;
        var $element = this.element;
        var self =this;
        if(addLicenseForm.valid()){
            var alias = addLicenseForm.getValue('alias');
            var privateKey = addLicenseForm.getValue('private_key');
            var certificate = addLicenseForm.getValue('certificate');

            addSertificate(
                this.option.tenantName,
                this.option.serviceAlias,
                privateKey,
                certificate,
                alias
            ).done(function(data){
                self.getSertificate();
                self.toAddDomain();
            })
        }
    },
    toAddCertificate:function(){
        this.bindDomainForm.hide();
        this.createCertificateForm.show();
        this.element.find('.addDomain').hide();
        this.element.find('.btn-cancel').hide();
        this.element.find('.addzhengshu').show();
        this.element.find('.btn-back').show();
    },
    renderSavedKeys: function(){
        if(this.option.savedKeys.length > 0) {
            this.element.find('.keySelect-wrap').show();
            this.element.find('.keyCreate-wrap').hide();
            this.element.find('[name=savedKeys]').html('');
            var savedKeys = this.option.savedKeys;
            for(var i=0;i<savedKeys.length;i++){
                var keysOption = $('<option value="'+savedKeys[i].id+'">'+savedKeys[i].alias+'</option>');
                this.element.find('[name=savedKeys]').append(keysOption);
            }
        }else{
             this.element.find('.keySelect-wrap').hide();
             this.element.find('.keyCreate-wrap').show();
        }
    },
    destroy:function() {
        this.bindDomainForm.destroy();
        this.createCertificateForm.destroy();
        this.bindDomainForm = this.createCertificateForm = null;
        this.callParent();
    }
})