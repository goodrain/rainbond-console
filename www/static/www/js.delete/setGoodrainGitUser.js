gWidget.define('setGoodrainGitUser', {
	extend:'dialog',
    _defaultOption : {
    	_tpl:'<form class="form-horizontal" style="padding:40px 20px;margin-left:auto;margin-right:auto;color:#303030">'+
              '<div class="form-group">'+
                '<label class="col-sm-3 control-label">好雨Git账号</label>'+
                '<div class="col-sm-8">'+
                 '<p class="form-control-static gitName"></p>'+
                '</div>'+
              '</div>'+
			  '<div class="form-group">'+
			    '<label class="col-sm-3 control-label">好雨Git密码</label>'+
			    '<div class="col-sm-8">'+
			     '<input type="password" maxlength="16" class="password form-control" placeholder="请输入您的云帮登录密码">'+
			    '</div>'+
			  '</div>'+
              '<div class="form-group">'+
                '<label class="col-sm-3 control-label">邮箱地址</label>'+
                '<div class="col-sm-8">'+
                 '<input type="text" class="email form-control" placeholder="邮箱地址">'+
                '</div>'+
              '</div>'+
			'</form>'+
            
			'<div class="row" style="text-align:left;border-top: 1px dashed #dcdcdc;padding-left:70px;padding-top:20px;font-size:12px;">'+
					'<p>* 好雨Git的密码为您的好雨账号登录密码， 此处输入仅做验证之用</p>'+
			'</div>',
        resize : false,
        expandable : false,
        showFooter : true,
        autoShow : true,
        drag:true,
        autoCenter : true,
        width:'650px',
        height:'200px',
        minHeight:'200px',
        modal : true,
        title: '设置好雨Git账号',
        gitName: '',
        btns:[{
        	classes: 'btn btn-success',
        	text: '确定'
        },{
        	classes: 'btn btn-default btn-cancel',
        	text: '取消'
        }]
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'setGoodrainGitUser'){
            this._create();
            this.bind();
        }
    },
    _create: function(){
    	this.callParent();
    	this.setContent(this.option._tpl);
        this.element.find('.gitName').html(this.option.gitName);

    },
    getData: function(){
    	var data = {
    		email: $.trim(this.element.find('.email').val()),
    		password: $.trim(this.element.find('.password').val())
    	}
    	return data;
    },
    check: function(){
    	var data = this.getData();

    	if(!data.email){
    		gWidget.Message.warning("请输入邮箱地址");
    		return false;
    	}

    	if(!/^(.+)@([a-zA-Z0-9]+)((\.)([a-zA-Z]+)){1,2}$/i.test(data.email)){
    		gWidget.Message.warning("邮箱格式不正确");
    		return false;
    	}

    	if(!data.password){
    		gWidget.Message.warning("请输入密码");
    		return false;
    	}

    	if(!/^.{8,16}$/.test(data.password)){
    		gWidget.Message.warning("密码长度为8-16位");
    		return false;
    	}

    	return true;
    },
    onSubmit: function(){
    	var tenantName = this.option.tenantName;
    	var data = this.getData();
    	var self  = this;
    	if(this.check()){
    		var loading = gWidget.create('loadingbar');
        	loading.addRequest();
    		$.ajax({
    			headers:{
    				"X-CSRFToken": $.cookie('csrftoken')
    			},
    			url:'/ajax/'+tenantName+'/git-register',
    			type:'post',
    			data:data,
    			success:function(data){
    				if(data.ok === true){
    					gWidget.Message.warning("好雨Git账号设置成功");
    					setTimeout(function(){
    						self.option.onSuccess && self.option.onSuccess(data)
    					}, 2000)
    					
    				}else{
    					gWidget.Message.warning(data.msg || '服务器异常');
    				}
    			},
    			error: function(data){

    			}
    		}).always(function(){
    			try{
    				loading.removeRequest();
    				loading.destroy();
    				loading = null;
    			}catch(e){

    			}
    			
    		})
    	}
    },
    bind: function(){
    	var self =this;
    	this.callParent();
    	this.element.delegate('.btn-success', 'click', function(e){
    		self.onSubmit();
    	})
    }
})