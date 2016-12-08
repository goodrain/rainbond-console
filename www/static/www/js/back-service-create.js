//服务创建
function service_create(tenantName, service_key, app_version) {
	window.location.href = "/apps/" + tenantName
			+ "/service-deploy/?service_key=" + service_key + "&app_version=" + app_version
}

function service_update(tenantName, service_key, app_version, update_version) {
    window.location.href = '/ajax/'+tenantName+'/remote/market?service_key='
            + service_key + '&app_version=' + app_version+'&update_version='+update_version+'&action=update';
}


//创建应用
$(function(){
    $('#create_service_name').blur(function(){
        var appName = $(this).val(),
            checkReg = /^[a-z][a-z0-9-]*[a-z0-9]$/,
            result = true;
            
        if(appName == ""){
            $('#create_service_notice').slideDown();
            return;
        }else{
            $('#create_service_notice').slideUp();
        }
    });
    //第一步
    $('#back_service_step1').click(function(){
        var appName = $('#create_service_name').val(),
            checkReg = /^[a-z][a-z0-9-]*[a-z0-9]$/,
            result = true;
            
        if(appName == ""){
            $('#create_service_notice').slideDown();
            return;
        }else{
            $('#create_service_notice').slideUp();
        }
		var tenantName = $("#tenantName").val()
		$("#back_service_step1").prop('disabled', true)
		var _data = $("form").serialize();
    	$.ajax({
    		type : "post",
    		url : "/apps/" + tenantName + "/service-deploy/",
    		data : _data,
    		cache : false,
    		beforeSend : function(xhr, settings) {
    			var csrftoken = $.cookie('csrftoken');
    			xhr.setRequestHeader("X-CSRFToken", csrftoken);
    		},
    		success : function(msg) {
    			var dataObj = msg;
                $("#back_service_finished").prop('disabled', false);
    			if (dataObj["status"] == "notexist"){
    				swal("所选的服务类型不存在");
    			} else if (dataObj["status"] == "depend_service_notexit"){
    			    swal("依赖的服务类型不存在，请先下载到服务市场");
    			} else if (dataObj["status"] == "owed"){
    				swal("余额不足请及时充值")
    			} else if (dataObj["status"] == "expired"){
                    swal("试用已到期")
                } else if (dataObj["status"] == "exist") {
    				swal("服务名已存在");
    			} else if (dataObj["status"] == "over_memory") {
    				swal("资源已达上限，不能创建");
    			} else if (dataObj["status"] == "over_money") {
    				swal("余额不足，不能创建");
    			} else if (dataObj["status"] == "empty") {
    				swal("服务名称不能为空");    				
    			}else if (dataObj["status"] == "success") {
    				service_alias = dataObj["service_alias"]
    				window.location.href = "/apps/" + tenantName + "/" + service_alias + "/setup/extra/";
    			} else {
    				swal("创建失败");
                }
    		},
    		error : function() {
    			swal("系统异常,请重试");
    			$("#back_service_finished").prop('disabled', false)
    		}
    	})
    });

    $('#back_service_finished').click(function() {
        envs = []
        var flag = false
        $('tbody tr').each(function() {
            env = {};
            $(this).find('[name^=attr]').each(function(event) {
                i = $(this);
                name = $(this).attr('name');
                value = $(this).val() || i.html();
                if (value) {
                    env[name] = value;
                } else {
                    showMessage("有未填写的内容");
                    flag = true
                }
            });
            envs.push(env);
        });
        if (flag) {
            return false;
        }
        var csrftoken = $.cookie('csrftoken');
        data = {"envs": envs};
        $.ajax({
          url: window.location.pathname,
          method: "POST",
          data: $.stringify(data),
          beforeSend: function(xhr) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
          },
          success :function (event) {
            if (event.success) {
              window.location.href = event.next_url;
            } else {
              showMessage(event.info);
            }
          },
          contentType: 'application/json; charset=utf-8',

          statusCode: {
            403: function(event) {
              alert("你没有此权限");
            }
          },
        });
    });

    //// ww-2016-12-6 选择 groupname start
    //弹出层
    function FnLayer(textTit){
        var oDiv = '<div class="layerbg"><div class="layermain"></div></div>';
        var oCloseBtn = '<a href="javascript:;" class="closebtn fn-close">X</a>';
        var oTit = '<p class="layer-tit">'+ textTit +'</p>';
        var oInput ='<p class="input-css"><input name="" type="text" value="" /></p>';
        var oLink = '<p class="layerlink"><a href="javascript:;" class="fn-sure">确定</a><a href="javascript:;" class="fn-close">取消</a></p>';
        $("body").append(oDiv);
        $("div.layermain").append(oCloseBtn,oTit);
        $("div.layermain").append(oInput);
        $("div.layermain").append(oLink);
        $(".fn-close").click(function(){
             $("div.layerbg").remove();
             $(".input-css input").prop("value","");
             $("#group-name").find("option[value='-1']").prop("selected",true);
        });
        $(".fn-sure").click(function(){
            if(inputText == ""){
                swal("您还没有输入组名！")
                return false;
            }else{
                var inputText = $(".input-css input").val();
                var tenant_name = $("#currentTeantName").val();
                ///ajax start

                $.ajax({
                    type : "post",
                    url : "/ajax/" + tenant_name  + "/group/add",
                    data : {
                        group_name : inputText
                    },
                    cache : false,
                    beforeSend : function(xhr, settings) {
                        var csrftoken = $.cookie('csrftoken');
                        xhr.setRequestHeader("X-CSRFToken", csrftoken);
                    },
                    success : function(msg) {
                        if(msg.ok){
                            var  group_id = msg.group_id;
                            var  group_name = msg.group_name;
                            var  Option = "<option value=" +  group_id + ">" + group_name + "</option>";
                            $("div.layerbg").remove();
                            $(".input-css input").prop("value","");
                            $("#group-name option").eq(0).after(Option);
                            $("#group-name option").each(function(){
                                var oVal = $(this).prop("value");
                                if(oVal == group_id){
                                    $(this).prop("selected",true);
                                }
                            });
                        }else{
                            swal(msg.info);
                        }
                    },
                    error : function() {
                        swal("系统异常,请重试");
                    }
                });
                
                ///ajax end
            }
              
        });   
    }
    //  弹出层
    $("#group-name").change(function(){
     var groupName=$("#group-name option:selected").val();
        //console.log(groupName);
        if(groupName == -2) {
            FnLayer("请输入新增组名");  
        }
    });
    //// ww-2016-12-6 选择 groupname end 
});