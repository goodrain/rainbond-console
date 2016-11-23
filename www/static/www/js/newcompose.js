$(function(){
	////// 端口
	//正则表达式
	var regNumber = /^[0-9]*$/; //验证数字
	// 新增端口 start 
	$(".fn-newapp").on("click",function(){
		var this_btn = $(this);
		this_btn.hide();
		this_btn.next("a.fn-newapp-sure").show();
		this_btn.next().next("a.fn-newapp-cancel").show();
		this_btn.parent().prev("div.addport-box").show();
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
		var appid = $(this).parent().parent().parent().parent().attr("id");
		//console.log(appid);
		var val_port = $(this).parent().prev("div.addport-box").find(".add-port input").val();
		//console.log($(this).parent().prev("div.addport-box").children(".add-port").children("input").val());
		//console.log($(this).parent().prev("div.addport-box").find(".add-port input").val());
		var val_agreement =$(this).parent().prev("div.addport-box").find(".add-agreement option:selected").val();
		var val_inner = $(this).parent().prev("div.addport-box").find(".add-inner").children("input").prop("checked");
		var val_outer = $(this).parent().prev("div.addport-box").find(".add-outer").children("input").prop("checked");
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
			new_tab = new_tab + '<td><a href="javascript:;" class="fn-revise">修改</a><a href="javascript:;" class="fn-delete">删除</a></td>';
			new_tab = new_tab + "</tr>";
			$("#" + appid + " table.new-port tbody").append(new_tab);
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
		var a_sure = '<a class="fn-sure" href="javascript:;">确定</a>';
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
			if(val_input != ""){
				this_box.find("span").eq(1).html(val_input);
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
		$(this).parent().prev(".environment-box").show();
		$(this).next(".fn-environment-sure").show();
		$(this).next().next(".fn-environment-cancel").show();
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
		var appid = $(this).parent().parent().parent().parent().attr("id");
		console.log(appid);
		var env_name = $(this).parent().prev("div.environment-box").find(".environment-name input").val();
		var env_english = $(this).parent().prev("div.environment-box").find(".environment-english input").val();
		var env_value = $(this).parent().prev("div.environment-box").find(".environment-value input").val();
		console.log(env_name,env_english,env_value);
		if(env_name == ""){
			alert("请输入名称！")
		}else if(env_english == ""){
			alert("请输入变量名！")
		}else if(env_value == ""){
			alert("请输入值！")
		}else{
			var new_tab = "<tr>";
			new_tab = new_tab + "<td><span>"+ env_name +"</span></td>";
			new_tab = new_tab + "<td><span>"+ env_english +"</span></td>";
			new_tab = new_tab + "<td><span>"+ env_value +"</span></td>";
			new_tab = new_tab + '<td><a href="javascript:;" class="fn-env-revise">修改</a><a href="javascript:;" class="fn-env-delete">删除</a></td>';
			new_tab = new_tab + "</tr>";
			$("#" + appid + " table.new-environment tbody").append(new_tab);
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
		var a_env_sure = '<a class="fn-env-sure" href="javascript:;">确定</a>';
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
			if(val_env_eng != ""){
				this_box.find("span").eq(1).html(val_env_eng);
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
		$(this).parent().prev(".directory-box").show();
		$(this).next(".fn-directory-sure").show();
		$(this).next().next(".fn-directory-cancel").show();
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
		var appid = $(this).parent().parent().parent().parent().attr("id");
		var dir_name = $(this).parent().prev("div.directory-box").find(".directory-name input").val();
		if(dir_name == ""){
			alert("请输入名称！")
		}else{
			var new_tab = "<tr>";
			new_tab = new_tab + "<td><span>"+ dir_name +"</span></td>";
			new_tab = new_tab + '<td><a href="javascript:;" class="fn-dir-revise">修改</a><a href="javascript:;" class="fn-dir-delete">删除</a></td>';
			new_tab = new_tab + "</tr>";
			$("#" + appid + " table.new-directory").append(new_tab);
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
		var dir_name = '<input type="text" class="fn-dir-name" value=' + previous_dir+'/>';
		var a_dir_sure = '<a class="fn-dir-sure" href="javascript:;">确定</a>';
		var a_dir_cancel = '<a class="fn-dir-cancel" href="javascript:;">取消</a>';
		this_box.children("td").eq(0).append(dir_name);
		this_box.children("td").eq(1).append(a_dir_sure,a_dir_cancel);
		// 确定
		$("body").on("click",".fn-dir-sure",function(){
			var val_dir_name = this_box.find("input.fn-dir-name").val();
			if(val_dir_name !=""){
				this_box.find("span").eq(0).html(val_dir_name);
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

	///// 提交
    $("#build-app").click(function(){
		$(this).attr('disabled',true);
    	var secbox= $(".app-box");
    	var secdate = [];
    	$(secbox).each(function(){
    		var appid = $(this).attr("id");
			var service_cname = $(this).attr("service_cname")
			var service_image = $(this).attr("service_image")
			
    		//console.log(appid);
    		//
    		var port_tr = $(this).find(".new-port tbody").children("tr");
    		var port_nums = [];
	        $(port_tr).each(function(i){
		    	var json_port = {};
			    var my_name = $(this).children("td").eq(0).children("span").html();
			    var my_port = $(this).children("td").eq(1).children("span").html();
			    var my_agreement = $(this).children("td").eq(2).children("span").html();
			    var my_inner = $(this).children("td").eq(3).children("input").prop("checked")? 1 : 0;
			    var my_outer = $(this).children("td").eq(4).children("input").prop("checked")? 1 : 0;
			    json_port["port_alias"] = my_name;
			    json_port["container_port"] = my_port;
			    json_port["protocol"] = my_agreement;
			    json_port["is_inner_service"] = my_inner;
			    json_port["is_outer_service"] = my_outer;
			    port_nums[i] = json_port;
			});
	        //console.log(port_nums);  
	        //
	        var env_tr = $(this).find(".new-environment tbody").children("tr");
    		var env_nums = [];
	    	$(env_tr).each(function(i){
	    		var json_environment = {};
	    		var my_name = $(this).children("td").eq(0).children("span").html();
	    		var my_engname = $(this).children("td").eq(1).children("span").html();
	    		var my_value = $(this).children("td").eq(2).children("span").html();
	    		json_environment["name"] = my_name;
	    		json_environment["attr_name"] = my_engname;
	    		json_environment["attr_value"] = my_value;
	    		env_nums[i] = json_environment;
	    	});
	    	//console.log(env_nums);
	    	//
	    	var dir_tr = $(this).find(".new-directory tbody").children("tr");
	    	var dir_nums = [];
		    $(dir_tr).each(function(i){
		    	var json_directory = {};
		    	var my_name = $(this).children("td").eq(0).children("span").html();
		    	json_directory["volume_path"] = my_name;
		    	dir_nums[i] = json_directory;
		    });

			var deps = $(this).find("#depends_service ").children("span");
			var depends_services = []
			$(deps).each(function (i) {
				var depends_service = {}
				var dps_service_name = $(this).html()
				depends_service["depends_service"] = dps_service_name
				depends_services[i]=dps_service_name
			});
		    //console.log(dir_nums);
	    	//
	    	var resources = $(this).find(".resources option:selected").val();  
	    	//console.log(resources);
	    	//
	    	var order = $(this).find(".order").val();
	    	var this_json={
				"service_image":service_image,
				"service_cname":service_cname,
	    		"service_id" : appid,
	    		"port_list" : port_nums,
	    		"env_list" : env_nums,
	    		"volume_list" : dir_nums,
				"depends_services":depends_services,
	    		"compose_service_memory" : resources,
	    		"start_cmd" : order
	    	}
	    	//console.log(this_json);
	    	secdate.push(this_json);
    	});
    	console.log(secdate);
    	//
		var tenantName = $("#tenantNameValue").val();
    	///
    	$.ajax({
            type: "post",
            url: "/apps/"+tenantName+"/compose-params/",
            dataType: "json",
			data: {"service_configs":JSON.stringify(secdate)},
			beforeSend : function(xhr, settings) {
				var csrftoken = $.cookie('csrftoken');
				xhr.setRequestHeader("X-CSRFToken", csrftoken);
			},
			success:function(data){
				if (data.status == 'success'){
					alert("success");
				}
			},
			error: function() {
				$(this).attr('disabled',false);
            },
            cache: false
            // processData: false
		});
		
    	///
    });
	///////

	/////切换
	$(".tablink a").click(function(){
		var num = $(this).index();
		$(".tablink a").removeClass("sed");
		$(this).addClass("sed");
		$("section.app-box").hide();
		$("section.app-box").eq(num).show();
	});


	$("#pre_page").click(function () {
		var compose_file_id = $("#compose_file_id").val();
		var tenantName = $("#tenantNameValue").val();
		url = "/apps/"+tenantName+"/compose-create?id="+compose_file_id;
		window.location.href = url
	})
});










