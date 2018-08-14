$(function(){
	////// 端口
	//正则表达式
	var regNumber = /^[0-9]*$/; //验证数字
	var variableReg = /^[A-Z][A-Z0-9_]*$/ //验证变量名
	var linuxPathReg = /^([\/] [\w-]+)*$/;  //验证linux文件
	// 新增端口 start
	$(".fn-newapp").on("click",function(){
		$(this).hide();
		$(".fn-newapp-sure").show();
		$(".fn-newapp-cancel").show();
		$(".addport-box").show();
	});
	// 新增端口 end 
	// 取消新增 start
	$(".fn-newapp-cancel").on("click",function(){
		$(".fn-newapp-sure").hide();
		$(".fn-newapp-cancel").hide();
		$(".fn-newapp").show();	
		$(".addport-box").hide();
		$(".add-port").children("input").prop("value","");
	}); 
	// 取消新增 end 
	//确认新增端口
	$(".fn-newapp-sure").on("click",function(){
		var val_port = $(".add-port").children("input").val();
		var val_agreement = $(".add-agreement option:selected").val();
		var val_inner = $(".add-inner").children("input").prop("checked");
		var val_outer = $(".add-outer").children("input").prop("checked");
		if(val_port == ""){
			alert("端口号不能为空");
		}else if(!regNumber.test(val_port)){
			alert("端口号必须为数字");
		}else{
			var new_tab = "<tr>";
			new_tab = new_tab + "<td><span>S"+ val_port +"</span></td>";
			new_tab = new_tab + "<td><span>"+ val_port +"</span></td>";
			new_tab = new_tab + "<td><span>"+ val_agreement +"</span></td>";
			if(val_inner == true){
				new_tab = new_tab + '<td><input class="fn-input-inner" name="inner" type="checkbox"  disabled="true" checked="checked"></td>';
			}else{
				new_tab = new_tab + '<td><input class="fn-input-inner" name="inner" type="checkbox"  disabled="true"></td>';
			}
			if(val_outer == true){
				new_tab = new_tab + '<td><input class="fn-input-outer" name="outer" type="checkbox"  disabled="true" checked="checked"></td>';
			}else{
				new_tab = new_tab + '<td><input class="fn-input-outer" name="outer" type="checkbox"  disabled="true"></td>';
			}
			new_tab = new_tab + '<td><a href="javascript:;" class="fn-revise">修改</a>&nbsp;&nbsp;&nbsp;<a href="javascript:;" class="fn-delete">删除</a></td>';
			new_tab = new_tab + "</tr>";
			$("#new-port tbody").append(new_tab);
			$(".fn-newapp-sure").hide();
			$(".fn-newapp-cancel").hide();
			$(".fn-newapp").show();	
			$(".addport-box").hide();
			$(".add-port input").prop("value","");
		}
	});
	//确认新增端口

	// 修改端口 start 
	$("body").on("click",".fn-revise",function(){
		$(this).hide();
		$(this).next("a").hide();
		var this_box = $(this).parent().parent();
		var previous_port_alias = this_box.find("span").eq(0).html();
		var previous_port = this_box.find("span").eq(1).html();
		//console.log(this_box);
		var input_onoff_inner = this_box.find("input").eq(0).attr("checked");
		var input_onoff_outer = this_box.find("input").eq(1).attr("checked");
		console.log(input_onoff_inner,input_onoff_outer);
		this_box.find("span").css({"display":"none"});
		this_box.find("input").removeAttr("disabled");
		var addto_name = '<input type="text" class="fn-addto-name" value='+previous_port_alias+' />';
		var addto_input = '<input type="text" class="fn-addto-input" value='+previous_port+' />';
		var addto_select = '<select class="fn-addto-select"><option value="http">http</option><option value="stream">stream</option></select>';
		var a_sure = '<a class="fn-sure" href="javascript:;">确定</a>&nbsp;&nbsp;';
		var a_cancel = '<a class="fn-cancel" href="javascript:;">取消</a>';
		this_box.children("td").eq(0).append(addto_name);
		this_box.children("td").eq(1).append(addto_input);
		this_box.children("td").eq(2).append(addto_select);
		this_box.children("td").eq(5).append(a_sure,a_cancel);

		////确定
		$("body").on("click",".fn-sure",function(){
			var val_name = this_box.find("input.fn-addto-name").val();
			var val_input = this_box.find("input.fn-addto-input").val();
			var val_select = this_box.find("select.fn-addto-select option:selected").val();
			if(val_name !=""){
				this_box.find("span").eq(0).html(val_name);
			}
			if(val_input != "" && regNumber.test(val_input)){
				this_box.find("span").eq(1).html(val_input);
			}else{
				alert("端口值不合法")
			}
			this_box.find("span").eq(2).html(val_select);
			this_box.find("span").css({"display":"inline-block"});
			this_box.find("a").css({"display":"inline-block"});
			this_box.find("input").attr("disabled","true");
			this_box.find("input.fn-addto-name").remove();
			this_box.find("input.fn-addto-input").remove();
			this_box.find("select.fn-addto-select").remove();
			this_box.find("a.fn-sure").remove();
			this_box.find("a.fn-cancel").remove();
		});
		////取消
		$("body").on("click",".fn-cancel",function(){
			this_box.find("span").css({"display":"inline-block"});
			this_box.find("a").css({"display":"inline-block"});
			this_box.find("input").attr("disabled","true");
			this_box.find("input.fn-addto-name").remove();
			this_box.find("input.fn-addto-input").remove();
			this_box.find("select.fn-addto-select").remove();
			this_box.find("a.fn-sure").remove();
			this_box.find("a.fn-cancel").remove();
			if(input_onoff_inner == "checked"){
				this_box.find("input.fn-input-inner").attr("checked",true);
			}else{
				this_box.find("input.fn-input-inner").removeAttr("checked");
			}
			if(input_onoff_outer == "checked"){
				this_box.find("input.fn-input-outer").attr("checked",true);
			}else{
				this_box.find("input.fn-input-outer").removeAttr("checked");
			}
		});
	});
	// 修改端口 end 

	// 删除端口 start
	$("body").on("click",".fn-delete",function(){
		$(this).parent().parent().remove();
	});
	// 删除端口 end 

	////// 环境变量
	// 新增环境变量 start 
	$(".fn-environment").click(function(){
		$(this).hide();
		$(".environment-box").show();
		$(".fn-environment-sure").show();
		$(".fn-environment-cancel").show();
	});
	// 新增环境变量 end 
	// 取消新增环境变量 start 
	$(".fn-environment-cancel").click(function(){
		$(this).hide();
		$(".environment-box").hide();
		$(".fn-environment-sure").hide();
		$(".fn-environment").show();
		$(".environment-name input").prop("value","");
		$(".environment-english input").prop("value","");
		$(".environment-value input").prop("value","");
	});
	// 取消新增环境变量 end 
	// 确认新增环境变量 start 
	
	$(".fn-environment-sure").click(function(){
		var env_name = $(".environment-name input").val();
		var env_english =  $(".environment-english input").val();
		var env_value = $(".environment-value input").val();
		if(env_name == ""){
			alert("请输入名称！")
		}else if(env_english == "" || !variableReg.test(env_english)) {
			alert("请输入合法变量名！")
		}else if(env_value == ""){
			alert("请输入属性值！")
		}else{
			var new_tab = "<tr>";
			new_tab = new_tab + "<td><span>"+ env_name +"</span></td>";
			new_tab = new_tab + "<td><span>"+ env_english +"</span></td>";
			new_tab = new_tab + "<td><span>"+ env_value +"</span></td>";
			new_tab = new_tab + '<td><a href="javascript:;" class="fn-env-revise">修改</a> &nbsp;&nbsp;<a href="javascript:;" class="fn-env-delete">删除</a></td>';
			new_tab = new_tab + "</tr>";
			$("#new-environment tbody").append(new_tab);
			$(".environment-box").hide();
			$(".fn-environment-sure").hide();
			$(".fn-environment-cancel").hide();
			$(".fn-environment").show();
			$(".environment-name input").prop("value","");
			$(".environment-english input").prop("value","");
			$(".environment-value input").prop("value","");
		}
	});
   
	// 确认新增环境变量 end 
	//修改环境变量
	$("body").on("click",".fn-env-revise",function(){
		$(this).hide();
		$(this).next("a").hide();
		var this_box = $(this).parent().parent();
		var previous_env_name = this_box.find("span").eq(0).html();
		var previous_attr_name = this_box.find("span").eq(1).html();
		var privious_attr_value = this_box.find("span").eq(2).html();
		this_box.find("span").css({"display":"none"});
		var env_name = '<input type="text" class="fn-env-name" value='+previous_env_name+' /> ';
		var env_engname = '<input type="text" class="fn-env-engname" value='+previous_attr_name+' /> ';
		var env_val = '<input type="text" class="fn-env-val" value='+privious_attr_value+' /> ';
		var a_env_sure = '<a class="fn-env-sure" href="javascript:;">确定</a>&nbsp;&nbsp;';
		var a_env_cancel = '<a class="fn-env-cancel" href="javascript:;">取消</a>';
		this_box.children("td").eq(0).append(env_name);
		this_box.children("td").eq(1).append(env_engname);
		this_box.children("td").eq(2).append(env_val);
		this_box.children("td").eq(3).append(a_env_sure,a_env_cancel);
		// 确定
		$("body").on("click",".fn-env-sure",function(){
			var val_env_name = this_box.find("input.fn-env-name").val();
			var val_env_eng = this_box.find("input.fn-env-engname").val();
			var val_env_val = this_box.find("input.fn-env-val").val();
			if(val_env_name !=""){
				this_box.find("span").eq(0).html(val_env_name);
			}
			if(val_env_eng != "" && variableReg.test(val_env_eng)){
				this_box.find("span").eq(1).html(val_env_eng);
			}else{
				alert("请输入合法变量值")
			}
			if(val_env_val != ""){
				this_box.find("span").eq(2).html(val_env_val);
			}
			this_box.find("span").css({"display":"inline-block"});
			this_box.find("a").css({"display":"inline-block"});
			this_box.find("input.fn-env-name").remove();
			this_box.find("input.fn-env-engname").remove();
			this_box.find("input.fn-env-val").remove();
			this_box.find("a.fn-env-sure").remove();
			this_box.find("a.fn-env-cancel").remove();
		});
		//取消
		$("body").on("click",".fn-env-cancel",function(){
			this_box.find("span").css({"display":"inline-block"});
			this_box.find("a").css({"display":"inline-block"});
			this_box.find("input.fn-env-name").remove();
			this_box.find("input.fn-env-engname").remove();
			this_box.find("input.fn-env-val").remove();
			this_box.find("a.fn-env-sure").remove();
			this_box.find("a.fn-env-cancel").remove();
		});
	});
	//删除环境变量
	$("body").on("click",".fn-env-delete",function(){
		$(this).parent().parent().remove();
	});

	////// 持久化目录
	$(".fn-directory").click(function(){
		$(this).hide();
		$(".directory-box").show();
		$(".fn-directory-sure").show();
		$(".fn-directory-cancel").show();
	});
	//
	$(".fn-directory-cancel").click(function(){
		$(this).hide();
		$(".directory-box").hide();
		$(".fn-directory-sure").hide();
		$(".fn-directory").show();
		$(".directory-name input").prop("value","");
	});
	//

	$(".fn-directory-sure").click(function(){
		var dir_name = $(".directory-name input").val();
		if(dir_name == "" ){
			alert("请输入正确的linux文件路径！")
		}else{
			var new_tab = "<tr>";
			new_tab = new_tab + "<td><span>"+ dir_name +"</span></td>";
			new_tab = new_tab + '<td><a href="javascript:;" class="fn-dir-revise">修改</a>&nbsp;&nbsp;<a href="javascript:;" class="fn-dir-delete">删除</a></td>';
			new_tab = new_tab + "</tr>";
			$("#new-directory").append(new_tab);
			$(".directory-box").hide();
			$(".fn-directory-sure").hide();
			$(".fn-directory-cancel").hide();
			$(".fn-directory").show();
			$(".directory-name input").prop("value","");
		}
	});
	//
	$("body").on("click",".fn-dir-revise",function(){
		$(this).hide();
		$(this).next("a").hide();
		var this_box = $(this).parent().parent();
		var previous_dir = this_box.find("span").eq(0).html();
		this_box.find("span").css({"display":"none"});
		var dir_name = '<input type="text" class="fn-dir-name" value='+previous_dir+' />';
		var a_dir_sure = '<a class="fn-dir-sure" href="javascript:;">确定</a>&nbsp;&nbsp;';
		var a_dir_cancel = '<a class="fn-dir-cancel" href="javascript:;">取消</a>';
		this_box.children("td").eq(0).append(dir_name);
		this_box.children("td").eq(1).append(a_dir_sure,a_dir_cancel);
		// 确定
		$("body").on("click",".fn-dir-sure",function(){
			var val_dir_name = this_box.find("input.fn-dir-name").val();
			if(val_dir_name !=""){
				this_box.find("span").eq(0).html(val_dir_name);
			}else{
				alert("请输入正确的linux文件路径!")
			}
			this_box.find("span").css({"display":"inline-block"});
			this_box.find("a").css({"display":"inline-block"});
			this_box.find("input.fn-dir-name").remove();
			this_box.find("a.fn-dir-sure").remove();
			this_box.find("a.fn-dir-cancel").remove();
		});
		//取消
		$("body").on("click",".fn-dir-cancel",function(){
			this_box.find("span").css({"display":"inline-block"});
			this_box.find("a").css({"display":"inline-block"});
			this_box.find("input.fn-dir-name").remove();
			this_box.find("a.fn-dir-sure").remove();
			this_box.find("a.fn-dir-cancel").remove();
		});
	});
	//
	$("body").on("click",".fn-dir-delete",function(){
		$(this).parent().parent().remove();
	});

	$("#pre_step").click(function(){
		var tenantName = $("#tenantNameValue").val();
		var service_id = $("#service_id").val();
		window.location.href ="/apps/"+tenantName+"/image-create/?id="+service_id
	})

	///// 提交
    $("#build-app").click(function(){
		$(this).attr('disabled',true);
    	console.log(1);
    	var port_tr = $("#new-port tbody tr");
    	var environment = $("#new-environment tbody tr");
    	var directory = $("#new-directory tr");
    	var resources = $("#resources option:selected").val();
    	var order = $("#order").val();
    	var port_nums = [];
    	var env_nums = [];
    	var dir_nums = [];
    	$(port_tr).each(function(i){
    		var json_port = {};
    		var my_name = $(this).children("td").eq(0).children("span").html();
    		var my_port = $(this).children("td").eq(1).children("span").html();
    		var my_agreement = $(this).children("td").eq(2).children("span").html();
    		var my_inner = $(this).children("td").eq(3).children("input").prop("checked") ? 1 : 0;
    		var my_outer = $(this).children("td").eq(4).children("input").prop("checked") ? 1 : 0;
    		json_port["port_alias"] = my_name;
    		json_port["container_port"] = my_port;
    		json_port["protocol"] = my_agreement;
    		json_port["is_inner_service"] = my_inner;
    		json_port["is_outer_service"] = my_outer;
    		port_nums[i] = json_port;
    	});
    	$(environment).each(function(i){
    		var json_environment = {};
    		var my_name = $(this).children("td").eq(0).children("span").html();
    		var my_engname = $(this).children("td").eq(1).children("span").html();
    		var my_value = $(this).children("td").eq(2).children("span").html();
    		json_environment["name"] = my_name;
    		json_environment["attr_name"] = my_engname;
    		json_environment["attr_value"] = my_value;
    		env_nums[i] = json_environment;
    	});
    	$(directory).each(function(i){
    		var json_directory = {};
    		var my_name = $(this).children("td").eq(0).children("span").html();
    		json_directory["volume_path"] = my_name;
    		dir_nums[i] = json_directory;
    	});
		var image_url = $("#image_url").val()
		var service_id = $("#service_id").val()
		service_config = {
			"image_url":image_url,
			"port_list" : JSON.stringify(port_nums),
			"env_list" : JSON.stringify(env_nums),
			"volume_list" : JSON.stringify(dir_nums),
			"image_service_memory" : resources,
			"start_cmd" : order,
			"service_id":service_id
		};
		var tenantName = $("#tenantNameValue").val();
    	///
    	$.ajax({
            type: "post",
            url: "/apps/"+tenantName+"/image-params/",
            dataType: "json",
			data: service_config,
			beforeSend : function(xhr, settings) {
				var csrftoken = $.cookie('csrftoken');
				xhr.setRequestHeader("X-CSRFToken", csrftoken);
			},
			success:function(data){
				status = data.status;
				if(status == "notfound"){
					swal("服务不存在");
				}else if (status == "failure"){
					swal("数据中心初始化失败");
				}else if (status == "owed"){
					swal("余额不足请及时充值");
				}else if (status =="expired"){
					swal("试用期已过");
				}else if(status =="over_memory"){
					swal("资源已达上限,无法创建");
				}else if(status == "over_money"){
					swal("余额不足无法创建");
				}else if (status == "success"){
					service_alias = data.service_alias
					window.location.href = "/apps/" + tenantName + "/" + service_alias + "/detail/";
				}else{
					swal("创建失败");
				}
				$("#build-app").attr('disabled',false);
				
			},
			error: function() {
				$("#build-app").attr('disabled',false);
            },
            cache: false
            // processData: false
		});
    	///
    });
	///////
    //提交信息
    $("#nextstep").click(function(){

        var oVal = $("#mirror-address").val();
		if(oVal== ""){
			swal("镜像不能为空");
			return false;
		}
		$(this).attr('disabled',true);
		var tenantName = $("#tenantNameValue").val();
		var service_id = $("#service_id").val();
        ///
        $.ajax({
            type: "post",
            url: "/apps/"+tenantName+"/image-create/",
            data: {
				"image_url":oVal,
				"service_id":service_id
            },
            catch: false,
            beforeSend: function (xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function (data) {
				if(data.ok){
					window.location.href = "/apps/"+tenantName+"/image-params?id="+data.id;
				}
                
            },
            error: function () {
                console.log("提交失败！");
            }
        })
        ///
    });

	function progressHandling(e) {
		var percentComplete = Math.round(e.loaded * 100 / e.total);
		console.log(percentComplete)
	}
	
	$("#create_name").blur(function(){
		var g_name = $("#create_name").val();
		if(g_name == ""){
			$("#create_name_notice").slideDown();
		}else{
			$("#create_name_notice").slideUp();
		}
	});
    //上传compose文件
    $("#nextcomposestep").click(function(){
        var formData = new FormData($("#myForm")[0]);
		var tenantName = $("#tenantNameValue").val();
		var group_name = $("#create_name").val();
		if(group_name == ""){
			$("#create_name_notice").slideDown();
			return;
		}else{
			$("#create_name_notice").slideUp();
		}
		formData.append("group_name",group_name);

		upload_url = "/apps/"+tenantName+"/compose-create/";
        $.ajax({  
                url : upload_url,  
                type : 'POST',  
                data : formData,  
                processData : false,  
                contentType : false,
				xhr: function() {
					myXhr = $.ajaxSettings.xhr();
					if(myXhr.upload){
						myXhr.upload.addEventListener('progress', progressHandling, false);
					}
					return myXhr;
				},
                beforeSend: function (xhr, settings) {
                    var csrftoken = $.cookie('csrftoken');
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                },
                success : function(responseStr) { 
					if(responseStr.success){
						window.location.href = "/apps/" + tenantName + "/compose-step2?id=" + responseStr.compose_file_id + "&group_id=" + responseStr.group_id;

					}else{
						if (responseStr.info == "group_exist"){
							swal("组名已存在");
						}
					}
                },  
                error : function(responseStr) {  
                   
                }  
            });  
    });


    //
    // $("#tab-tit a").click(function(){
    // 	var indexnum = $(this).index();
    // 	$("#tab-tit a").removeClass("sed");
    // 	$(this).addClass("sed");
    // 	$("#app-market li").hide();
    // 	$("#app-market li").eq(indexnum).show();
    // });

    //
    $("#compose_file").on("change",function(){
        var filePath=$(this).val();
        if(filePath.indexOf("yml")!=-1){
            var arr=filePath.split('\\');
            var fileName=arr[arr.length-1];
            console.log(fileName)
            $(this).next("span").html(fileName);
        }else{
            $(this).next("span").html("请重新上传！");
            return false;
        }
    });
    //
});
function service_create(tenantName, service_key, app_version) {
	window.location.href = "/apps/" + tenantName
		+ "/service-deploy/?service_key=" + service_key + "&app_version=" + app_version
}

function group_create(tenantName, group_key, group_version) {
    window.location.href = "/apps/" + tenantName
        + "/group-deploy/?group_key=" + group_key + "&group_version="+group_version

}