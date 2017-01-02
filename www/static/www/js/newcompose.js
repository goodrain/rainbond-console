$(function(){
	////// 端口
	//正则表达式
	//var regNumber = /^[0-9]*$/; //验证数字
	// 新增端口 start 
	//$(".fn-newapp").on("click",function(){
	//	var this_btn = $(this);
	//	this_btn.hide();
	//	this_btn.next("a.fn-newapp-sure").show();
	//	this_btn.next().next("a.fn-newapp-cancel").show();
	//	this_btn.parent().prev("div.addport-box").show();
	//});
	// 新增端口 end 
	// 取消新增 start
	//$(".fn-newapp-cancel").on("click",function(){
	//	$(".fn-newapp-sure").hide();
	//	$(".fn-newapp-cancel").hide();
	//	$(".fn-newapp").show();
	//	$(".addport-box").hide();
	//	$(".add-port").children("input").prop("value","");
	//});
	// 取消新增 end 
	//确认新增端口
	//$(".fn-newapp-sure").on("click",function(){
	//	var appid = $(this).parent().parent().parent().parent().attr("id");
	//	//console.log(appid);
	//	var val_port = $(this).parent().prev("div.addport-box").find(".add-port input").val();
	//	//console.log($(this).parent().prev("div.addport-box").children(".add-port").children("input").val());
	//	//console.log($(this).parent().prev("div.addport-box").find(".add-port input").val());
	//	var val_agreement =$(this).parent().prev("div.addport-box").find(".add-agreement option:selected").val();
	//	var val_inner = $(this).parent().prev("div.addport-box").find(".add-inner").children("input").prop("checked");
	//	var val_outer = $(this).parent().prev("div.addport-box").find(".add-outer").children("input").prop("checked");
	//	if(val_port == ""){
	//		alert("端口号不能为空");
	//	}else if(!regNumber.test(val_port)){
	//		alert("端口号必须为数字");
	//	}else{
	//		var new_tab = "<tr>";
	//		new_tab = new_tab + "<td><span>S"+ val_port +"</span></td>";
	//		new_tab = new_tab + "<td><span>"+ val_port +"</span></td>";
	//		new_tab = new_tab + "<td><span>"+ val_agreement +"</span></td>";
	//		if(val_inner == true){
	//			new_tab = new_tab + '<td><input class="fn-input-inner" name="inner" type="checkbox"  disabled="true" checked="checked"></td>';
	//		}else{
	//			new_tab = new_tab + '<td><input class="fn-input-inner" name="inner" type="checkbox"  disabled="true"></td>';
	//		}
	//		if(val_outer == true){
	//			new_tab = new_tab + '<td><input class="fn-input-outer" name="outer" type="checkbox"  disabled="true" checked="checked"></td>';
	//		}else{
	//			new_tab = new_tab + '<td><input class="fn-input-outer" name="outer" type="checkbox"  disabled="true"></td>';
	//		}
	//		new_tab = new_tab + '<td><a href="javascript:;" class="fn-revise">修改</a><a href="javascript:;" class="fn-delete">删除</a></td>';
	//		new_tab = new_tab + "</tr>";
	//		$("#" + appid + " table.new-port tbody").append(new_tab);
	//		$(".fn-newapp-sure").hide();
	//		$(".fn-newapp-cancel").hide();
	//		$(".fn-newapp").show();
	//		$(".addport-box").hide();
	//		$(".add-port input").prop("value","");
	//	}
	//});
	//确认新增端口

	//打开新增端口号窗口
	$(".openAdd").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		$("#"+appid+" select.add_http").val("请选择");
		var appid = $(this).parents("section.app-box").attr("id");
		$("#"+appid+" .addPort").css({"display":"table-row"});
	});
	$(".add_port").blur(function(){
		var appid = $(this).parents("section.app-box").attr("id");
		var portNum = parseInt($("#"+appid+" .add_port").val());
		if( portNum>1024 && portNum<65536 )
		{
			$(this).parents('tr').find('p.checkTip').css({"display":"none"});
		}
		else{
			$(this).parents('tr').find('p.checkTip').css({"display":"block"});
		}
	})
	//确定添加端口号
	$(".add").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		var portNum = parseInt($("#"+appid+" .add_port").val());
		if( portNum>1024 && portNum<65536 )
		{
			var addOnoff = true;
			var portLen = $("#"+appid+" .portNum").length;
			for( var i = 0; i<portLen; i++ )
			{
				if( portNum == $("#"+appid+" .portNum").eq(i).html() )
				{
					addOnoff = false;
					break;
				}
			}
			if( addOnoff )
			{
				var arr = ['HTTP','非HTTP'];
				var oTr = '<tr><td><a href="javascript:void(0);" class="portNum edit-port fn-tips" data-tips="源码中无 Dockerfile 文件时，默认开启服务端口为5000，请勿随意更改。如果当前应用为多端口应用，请根据您编码中定义的端口自行添加。">'+$("#"+appid+" .add_port").val()+'</a></td>';
				if( $("#addInner"+appid+"").prop("checked") == true )
				{
					oTr += '<td><div class="checkbox fn-tips" data-tips="打开对外服务，其他应用即可访问当前应用。"><input type="checkbox" name="" value="" id="'+$("#"+appid+" .add_port").val()+'inner'+appid+'" checked="true" /><label class="check-bg" for="'+$("#"+appid+" .add_port").val()+'inner'+appid+'"></label></div></td>';
				}
				else{
					oTr += '<td><div class="checkbox fn-tips" data-tips="打开对外服务，其他应用即可访问当前应用。"><input type="checkbox" name="" value="" id="'+$("#"+appid+" .add_port").val()+'inner'+appid+'" /><label class="check-bg" for="'+$("#"+appid+" .add_port").val()+'inner'+appid+'"></label></div></td>';
				}
				if( $("#addOuter"+appid+"").prop("checked") == true )
				{
					oTr += '<td><div class="checkbox fn-tips" data-tips="打开外部访问，用户即可通过互联网访问当前应用。"><input class="checkDetail" type="checkbox" name="" value="" id="'+$("#"+appid+" .add_port").val()+'outer'+appid+'" checked="true" /><label class="check-bg" for="'+$("#"+appid+" .add_port").val()+'outer'+appid+'"></label></div></td><td>';
					oTr += '<select style="" class="fn-tips" data-tips="如果允许用户通过互联网采用HTTP协议访问当前应用，请选择HTTP。" data-port-http="'+$("#"+appid+" .add_port").val()+'http"><option class="changeOption">请选择</option>';
				}
				else{
					oTr += '<td><div class="checkbox fn-tips" data-tips="打开外部访问，用户即可通过互联网访问当前应用。"><input class="checkDetail" type="checkbox" name="" value="" id="'+$("#"+appid+" .add_port").val()+'outer'+appid+'" /><label class="check-bg" for="'+$("#"+appid+" .add_port").val()+'outer'+appid+'"></label></div></td><td>';
					oTr += '<select disabled="disabled" style="color: #838383;" class="fn-tips" data-tips="如果允许用户通过互联网采用HTTP协议访问当前应用，请选择HTTP。" data-port-http="'+$("#"+appid+" .add_port").val()+'http"><option class="changeOption">请打开外部访问</option>';
				}
				for( var i = 0; i < 2; i++ )
				{
					if( $('#'+appid+' .add_http').val() == arr[i] )
					{
						oTr += '<option selected="selected">'+arr[i]+'</option>';
					}
					else{
						oTr += '<option>'+arr[i]+'</option>';
					}
				}
				oTr += '</select></td><td><img class="rubbish" src="/static/www/images/rubbish.png"/></td></tr>';
				$(oTr).appendTo("#"+appid+" .port");
				$("#"+appid+" .addPort").css({"display":"none"});
				delPort();
				editPort();
				tip();
				checkDetail();
				selectChange();
			}
			else{
				swal("端口号冲突～～");
			}
		}
		else{
			$(this).parents('tr').find('p.checkTip').css({"display":"block"});
		}
		$("#"+appid+" .add_port").val("");
	});
	//取消端口号的添加
	$(".noAdd").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		$("#"+appid+" .addPort").css({"display":"none"});
	});
	delPort();
	//删除端口号与环境变量
	function delPort(){
		$("img.rubbish").off("click");
		$("img.rubbish").on("click",function(){
			$(this).parents("tr").remove();
		})
	}
	//外部访问开关
	checkDetail();
	function checkDetail(){
		$("input.checkDetail").off("click");
		$("input.checkDetail").on("click",function(){
			var appid = $(this).parents("section.app-box").attr("id");
			if( $(this).prop("checked") )
			{
				$(this).parents("tr").find("option.changeOption").html("请选择");
				$(this).parents("tr").find("select").val("请选择");
				$(this).parents("tr").find("select").css({"color":"#28cb75"}).removeAttr("disabled");
			}
			else
			{
				$(this).parents("tr").find("option.changeOption").html("请打开外部访问");
				$(this).parents("tr").find("select").val("请打开外部访问");
				$(this).parents("tr").find("select").css({"color":"#838383"}).attr("disabled",true);
			}
			if( $(this).parents("tr").find("select").val() == '非HTTP' )
			{
				var len = $("#"+appid+" table.tab-box tbody select").length;
				var num = 0;
				for( var i = 0; i<len; i++ )
				{
					if( $("#"+appid+" table.tab-box tbody input.checkDetail").eq(i).prop("checked") && $("#"+appid+" table.tab-box tbody select").eq(i).val() == '非HTTP' )
					{
						num++;
					}
				}
				if( num >= 2 )
				{
					swal("访问方式只能有一个非HTTP");
					$(this).parents("tr").find("select").val("请选择");
				}
			}
		});
	}
	//访问方式切换
	selectChange();
	function selectChange(){
		var selectLen = $("table.tab-box select").length;
		for( var j = 0; j<selectLen; j++ )
		{
			$("table.tab-box select").eq(j).attr("index",j);
			$("table.tab-box select").eq(j).change(function(){
				var appid = $(this).parents("section.app-box").attr("id");
				console.log(appid);
				if( $(this).val() == '非HTTP' )
				{
					var len = $("#"+appid+" table.tab-box tbody select").length;
					for( var i = 0; i<len; i++ )
					{
						if( $("#"+appid+" table.tab-box tbody input.checkDetail").eq(i).prop("checked") && $("#"+appid+" table.tab-box tbody select").eq(i).val() == '非HTTP' && i != $(this).attr("index") )
						{
							console.log(i);
							swal("访问方式只能有一个非HTTP");
							$(this).val("请选择");
							break;
						}
					}
				}
			})
		}
	}
	//修改端口号
	editPort();
	function editPort(){
		$('.edit-port').editable({
			type: 'text',
			pk: 1,
			success: function (data) {
				//window.location.reload();
			},
			error: function (data) {
				msg = data.responseText;
				res = $.parseJSON(msg);
				showMessage(res.info);
			},
			ajaxOptions: {
				beforeSend: function(xhr, settings) {
					xhr.setRequestHeader("X-CSRFToken", $.cookie('csrftoken'));
					settings.data += '&action=change_port';
				},
			}
		});
	}

	//// 修改端口 start
	//$("body").on("click",".fn-revise",function(){
	//	$(this).hide();
	//	$(this).next("a").hide();
	//	var this_box = $(this).parent().parent();
	//	var previous_port_alias = this_box.find("span").eq(0).html();
	//	var previous_port = this_box.find("span").eq(1).html();
	//	//console.log(this_box);
	//	var input_onoff_inner = this_box.find("input").eq(0).attr("checked");
	//	var input_onoff_outer = this_box.find("input").eq(1).attr("checked");
	//	console.log(input_onoff_inner,input_onoff_outer);
	//	this_box.find("span").css({"display":"none"});
	//	this_box.find("input").removeAttr("disabled");
	//	var addto_name = '<input type="text" class="fn-addto-name" value='+previous_port_alias+' />';
	//	var addto_input = '<input type="text" class="fn-addto-input" value='+previous_port+' />';
	//	var addto_select = '<select class="fn-addto-select"><option value="http">http</option><option value="stream">stream</option></select>';
	//	var a_sure = '<a class="fn-sure" href="javascript:;">确定</a>';
	//	var a_cancel = '<a class="fn-cancel" href="javascript:;">取消</a>';
	//	this_box.children("td").eq(0).append(addto_name);
	//	this_box.children("td").eq(1).append(addto_input);
	//	this_box.children("td").eq(2).append(addto_select);
	//	this_box.children("td").eq(5).append(a_sure,a_cancel);
	//
	//	////确定
	//	$("body").on("click",".fn-sure",function(){
	//		var val_name = this_box.find("input.fn-addto-name").val();
	//		var val_input = this_box.find("input.fn-addto-input").val();
	//		var val_select = this_box.find("select.fn-addto-select option:selected").val();
	//		if(val_name !=""){
	//			this_box.find("span").eq(0).html(val_name);
	//		}
	//		if(val_input != ""){
	//			this_box.find("span").eq(1).html(val_input);
	//		}
	//		this_box.find("span").eq(2).html(val_select);
	//		this_box.find("span").css({"display":"inline-block"});
	//		this_box.find("a").css({"display":"inline-block"});
	//		this_box.find("input").attr("disabled","true");
	//		this_box.find("input.fn-addto-name").remove();
	//		this_box.find("input.fn-addto-input").remove();
	//		this_box.find("select.fn-addto-select").remove();
	//		this_box.find("a.fn-sure").remove();
	//		this_box.find("a.fn-cancel").remove();
	//	});
	//	////取消
	//	$("body").on("click",".fn-cancel",function(){
	//		this_box.find("span").css({"display":"inline-block"});
	//		this_box.find("a").css({"display":"inline-block"});
	//		this_box.find("input").attr("disabled","true");
	//		this_box.find("input.fn-addto-name").remove();
	//		this_box.find("input.fn-addto-input").remove();
	//		this_box.find("select.fn-addto-select").remove();
	//		this_box.find("a.fn-sure").remove();
	//		this_box.find("a.fn-cancel").remove();
	//		if(input_onoff_inner == "checked"){
	//			this_box.find("input.fn-input-inner").attr("checked",true);
	//		}else{
	//			this_box.find("input.fn-input-inner").removeAttr("checked");
	//		}
	//		if(input_onoff_outer == "checked"){
	//			this_box.find("input.fn-input-outer").attr("checked",true);
	//		}else{
	//			this_box.find("input.fn-input-outer").removeAttr("checked");
	//		}
	//	});
	//});
	//// 修改端口 end
    //
	//// 删除端口 start
	//$("body").on("click",".fn-delete",function(){
	//	$(this).parent().parent().remove();
	//});
	//// 删除端口 end


	//显示添加环境变量内容
	$(".openAddEnviroment").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		$("#"+appid+" .addContent").css({"display":"table-row"});
	});
	$(".enviroKey").blur(function(){
		var appid = $(this).parents("section.app-box").attr("id");
		var variableReg = /^[A-Z][A-Z0-9_]*$/;
		if( variableReg.test($("#"+appid+" .enviroKey").val()) )
		{
			$(this).parent().find("p.checkTip").css({"display":"none"});
		}
		else{
			$(this).parent().find("p.checkTip").css({"display":"block"});
		}
	});
	$(".addEnviroment").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		if( $("#"+appid+" .enviroKey").val() && $("#"+appid+" .enviroValue").val() )
		{
			var len = $("#"+appid+" .enviromentKey").length;
			var onOff = true;
			for( var i = 0; i<len; i++ )
			{
				if( $("#"+appid+" .enviroKey").val() == $("#"+appid+" .enviromentKey")[i].innerHTML ){
					swal("变量名冲突～～");
					onOff = false;
					break;
				}
			}
			if( onOff )
			{
				var variableReg = /^[A-Z][A-Z0-9_]*$/;
				if( variableReg.test($("#"+appid+" .enviroKey").val()) )
				{
					var str = '<tr><td><a href="javascript:void(0);" class="enviromentName edit-port enviromentKey key'+(len+1)+'">'+$("#"+appid+" .enviroName").val()+'</a></td>';
					str += '<td><a href="javascript:void(0);" class="edit-port enviromentKey key'+(len+1)+'">'+$("#"+appid+" .enviroKey").val()+'</a></td>';
					str += '<td><a href="javascript:void(0);" class="edit-port enviromentValue value'+(len+1)+'">'+$("#"+appid+" .enviroValue").val()+'</a></td>';
					str += '<td><img class="rubbish" src="/static/www/images/rubbish.png"/></td></tr>';
					$(str).appendTo("#"+appid+" .enviroment");
					$("#"+appid+" .enviroName").val('');
					$("#"+appid+" .enviroKey").val('');
					$("#"+appid+" .addContent").css({"display":"none"});
					delPort();
					editPort();
				}
				else{
					swal("变量名由大写字母开头，可以加入数字～～");
				}
			}
		}
		else{
			console.log(2);
		}
	});
	$(".noAddEnviroment").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		$("#"+appid+" .addContent").css({"display":"none"});
		$("#"+appid+" .enviroKey").val('');
		$("#"+appid+" .enviroValue").val('');
	});

	////// 环境变量
	// 新增环境变量 start 
	//$(".fn-environment").click(function(){
	//	$(this).hide();
	//	$(this).parent().prev(".environment-box").show();
	//	$(this).next(".fn-environment-sure").show();
	//	$(this).next().next(".fn-environment-cancel").show();
	//});
	//// 新增环境变量 end
	//// 取消新增环境变量 start
	//$(".fn-environment-cancel").click(function(){
	//	$(this).hide();
	//	$(".environment-box").hide();
	//	$(".fn-environment-sure").hide();
	//	$(".fn-environment").show();
	//	$(".environment-name input").prop("value","");
	//	$(".environment-english input").prop("value","");
	//	$(".environment-value input").prop("value","");
	//});
	// 取消新增环境变量 end 
	// 确认新增环境变量 start 
	
	//$(".fn-environment-sure").click(function(){
	//	var appid = $(this).parent().parent().parent().parent().attr("id");
	//	console.log(appid);
	//	var env_name = $(this).parent().prev("div.environment-box").find(".environment-name input").val();
	//	var env_english = $(this).parent().prev("div.environment-box").find(".environment-english input").val();
	//	var env_value = $(this).parent().prev("div.environment-box").find(".environment-value input").val();
	//	console.log(env_name,env_english,env_value);
	//	if(env_name == ""){
	//		alert("请输入名称！")
	//	}else if(env_english == ""){
	//		alert("请输入变量名！")
	//	}else if(env_value == ""){
	//		alert("请输入值！")
	//	}else{
	//		var new_tab = "<tr>";
	//		new_tab = new_tab + "<td><span>"+ env_name +"</span></td>";
	//		new_tab = new_tab + "<td><span>"+ env_english +"</span></td>";
	//		new_tab = new_tab + "<td><span>"+ env_value +"</span></td>";
	//		new_tab = new_tab + '<td><a href="javascript:;" class="fn-env-revise">修改</a><a href="javascript:;" class="fn-env-delete">删除</a></td>';
	//		new_tab = new_tab + "</tr>";
	//		$("#" + appid + " table.new-environment tbody").append(new_tab);
	//		$(".environment-box").hide();
	//		$(".fn-environment-sure").hide();
	//		$(".fn-environment-cancel").hide();
	//		$(".fn-environment").show();
	//		$(".environment-name input").prop("value","");
	//		$(".environment-english input").prop("value","");
	//		$(".environment-value input").prop("value","");
	//	}
	//});
    //
	//// 确认新增环境变量 end
	////修改环境变量
	//$("body").on("click",".fn-env-revise",function(){
	//	$(this).hide();
	//	$(this).next("a").hide();
	//	var this_box = $(this).parent().parent();
	//	var previous_env_name = this_box.find("span").eq(0).html();
	//	var previous_attr_name = this_box.find("span").eq(1).html();
	//	var privious_attr_value = this_box.find("span").eq(2).html();
	//	this_box.find("span").css({"display":"none"});
	//	var env_name = '<input type="text" class="fn-env-name" value='+previous_env_name+' /> ';
	//	var env_engname = '<input type="text" class="fn-env-engname" value='+previous_attr_name+' /> ';
	//	var env_val = '<input type="text" class="fn-env-val" value='+privious_attr_value+' /> ';
	//	var a_env_sure = '<a class="fn-env-sure" href="javascript:;">确定</a>';
	//	var a_env_cancel = '<a class="fn-env-cancel" href="javascript:;">取消</a>';
	//	this_box.children("td").eq(0).append(env_name);
	//	this_box.children("td").eq(1).append(env_engname);
	//	this_box.children("td").eq(2).append(env_val);
	//	this_box.children("td").eq(3).append(a_env_sure,a_env_cancel);
	//	// 确定
	//	$("body").on("click",".fn-env-sure",function(){
	//		var val_env_name = this_box.find("input.fn-env-name").val();
	//		var val_env_eng = this_box.find("input.fn-env-engname").val();
	//		var val_env_val = this_box.find("input.fn-env-val").val();
	//		if(val_env_name !=""){
	//			this_box.find("span").eq(0).html(val_env_name);
	//		}
	//		if(val_env_eng != ""){
	//			this_box.find("span").eq(1).html(val_env_eng);
	//		}
	//		if(val_env_val != ""){
	//			this_box.find("span").eq(2).html(val_env_val);
	//		}
	//		this_box.find("span").css({"display":"inline-block"});
	//		this_box.find("a").css({"display":"inline-block"});
	//		this_box.find("input.fn-env-name").remove();
	//		this_box.find("input.fn-env-engname").remove();
	//		this_box.find("input.fn-env-val").remove();
	//		this_box.find("a.fn-env-sure").remove();
	//		this_box.find("a.fn-env-cancel").remove();
	//	});
	//	//取消
	//	$("body").on("click",".fn-env-cancel",function(){
	//		this_box.find("span").css({"display":"inline-block"});
	//		this_box.find("a").css({"display":"inline-block"});
	//		this_box.find("input.fn-env-name").remove();
	//		this_box.find("input.fn-env-engname").remove();
	//		this_box.find("input.fn-env-val").remove();
	//		this_box.find("a.fn-env-sure").remove();
	//		this_box.find("a.fn-env-cancel").remove();
	//	});
	//});
	////删除环境变量
	//$("body").on("click",".fn-env-delete",function(){
	//	$(this).parent().parent().remove();
	//});

	//显示添加环境变量内容
	//$(".openAddEnviroment").on("click",function(){
	//	var appid = $(this).parents("section.app-box").attr("id");
	//	$("#"+appid+" .addContent").css({"display":"table-row"});
	//});
	//$(".enviroKey").blur(function(){
	//	var appid = $(this).parents("section.app-box").attr("id");
	//	var variableReg = /^[A-Z][A-Z0-9_]*$/;
	//	if( variableReg.test($("#"+appid+" .enviroKey").val()) )
	//	{
	//		$(this).parent().find("p.checkTip").css({"display":"none"});
	//	}
	//	else{
	//		$(this).parent().find("p.checkTip").css({"display":"block"});
	//	}
	//});
	//$(".addEnviroment").on("click",function(){
	//	var appid = $(this).parents("section.app-box").attr("id");
	//	if( $("#"+appid+" .enviroKey").val() && $("#"+appid+" .enviroValue").val() )
	//	{
	//		var len = $("#"+appid+" .enviromentKey").length;
	//		var onOff = true;
	//		for( var i = 0; i<len; i++ )
	//		{
	//			if( $("#"+appid+" .enviroKey").val() == $("#"+appid+" .enviromentKey")[i].innerHTML ){
	//				swal("变量名冲突～～");
	//				onOff = false;
	//				break;
	//			}
	//		}
	//		if( onOff )
	//		{
	//			var variableReg = /^[A-Z][A-Z0-9_]*$/;
	//			if( variableReg.test($("#"+appid+" .enviroKey").val()) )
	//			{
	//				var str = '<tr><td><a href="javascript:void(0);" class="enviromentName edit-port enviromentKey key'+(len+1)+'">'+$("#"+appid+" .enviroName").val()+'</a></td>';
	//				str += '<td><a href="javascript:void(0);" class="edit-port enviromentKey key'+(len+1)+'">'+$("#"+appid+" .enviroKey").val()+'</a></td>';
	//				str += '<td><a href="javascript:void(0);" class="edit-port enviromentValue value'+(len+1)+'">'+$("#"+appid+" .enviroValue").val()+'</a></td>';
	//				str += '<td><img class="rubbish" src="/static/www/images/rubbish.png"/></td></tr>';
	//				$(str).appendTo(".enviroment");
	//				$("#"+appid+" .enviroName").val('');
	//				$("#"+appid+" .enviroKey").val('');
	//				$("#"+appid+" .enviroValue").val('');
	//				$("#"+appid+" .addContent").css({"display":"none"});
	//				delPort();
	//				editPort();
	//			}
	//			else{
	//				swal("变量名由大写字母开头，可以加入数字～～");
	//			}
	//		}
	//	}
	//	else{
	//		console.log(2);
	//	}
	//});
	//$(".noAddEnviroment").on("click",function(){
	//	var appid = $(this).parents("section.app-box").attr("id");
	//	$("#"+appid+" .addContent").css({"display":"none"});
	//	$("#"+appid+" .enviroKey").val('');
	//	$("#"+appid+" .enviroValue").val('');
	//});


	////// 持久化目录
	//$(".fn-directory").click(function(){
	//	$(this).hide();
	//	$(this).parent().prev(".directory-box").show();
	//	$(this).next(".fn-directory-sure").show();
	//	$(this).next().next(".fn-directory-cancel").show();
	//});
	////
	//$(".fn-directory-cancel").click(function(){
	//	$(this).hide();
	//	$(".directory-box").hide();
	//	$(".fn-directory-sure").hide();
	//	$(".fn-directory").show();
	//	$(".directory-name input").prop("value","");
	//});
	////
	//$(".fn-directory-sure").click(function(){
	//	var appid = $(this).parent().parent().parent().parent().attr("id");
	//	var dir_name = $(this).parent().prev("div.directory-box").find(".directory-name input").val();
	//	if(dir_name == ""){
	//		alert("请输入名称！")
	//	}else{
	//		var new_tab = "<tr>";
	//		new_tab = new_tab + "<td><span>"+ dir_name +"</span></td>";
	//		new_tab = new_tab + '<td><a href="javascript:;" class="fn-dir-revise">修改</a><a href="javascript:;" class="fn-dir-delete">删除</a></td>';
	//		new_tab = new_tab + "</tr>";
	//		$("#" + appid + " table.new-directory").append(new_tab);
	//		$(".directory-box").hide();
	//		$(".fn-directory-sure").hide();
	//		$(".fn-directory-cancel").hide();
	//		$(".fn-directory").show();
	//		$(".directory-name input").prop("value","");
	//	}
	//});
	//
	//$("body").on("click",".fn-dir-revise",function(){
	//	$(this).hide();
	//	$(this).next("a").hide();
	//	var this_box = $(this).parent().parent();
	//	var previous_dir = this_box.find("span").eq(0).html();
	//	this_box.find("span").css({"display":"none"});
	//	var dir_name = '<input type="text" class="fn-dir-name" value=' + previous_dir+'/>';
	//	var a_dir_sure = '<a class="fn-dir-sure" href="javascript:;">确定</a>';
	//	var a_dir_cancel = '<a class="fn-dir-cancel" href="javascript:;">取消</a>';
	//	this_box.children("td").eq(0).append(dir_name);
	//	this_box.children("td").eq(1).append(a_dir_sure,a_dir_cancel);
	//	// 确定
	//	$("body").on("click",".fn-dir-sure",function(){
	//		var val_dir_name = this_box.find("input.fn-dir-name").val();
	//		if(val_dir_name !=""){
	//			this_box.find("span").eq(0).html(val_dir_name);
	//		}
	//		this_box.find("span").css({"display":"inline-block"});
	//		this_box.find("a").css({"display":"inline-block"});
	//		this_box.find("input.fn-dir-name").remove();
	//		this_box.find("a.fn-dir-sure").remove();
	//		this_box.find("a.fn-dir-cancel").remove();
	//	});
	//	//取消
	//	$("body").on("click",".fn-dir-cancel",function(){
	//		this_box.find("span").css({"display":"inline-block"});
	//		this_box.find("a").css({"display":"inline-block"});
	//		this_box.find("input.fn-dir-name").remove();
	//		this_box.find("a.fn-dir-sure").remove();
	//		this_box.find("a.fn-dir-cancel").remove();
	//	});
	//});
	////
	//$("body").on("click",".fn-dir-delete",function(){
	//	$(this).parent().parent().remove();
	//});
	delLi();
	//删除依赖与目录
	function delLi(){
		$("img.delLi").off("click");
		$("img.delLi").on("click",function(){
			$(this).parents("li").remove();
		})
	}
	//新设持久化目录
	$(".addCata").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		$("#"+appid+" p.catalogue").css({"display":"block"});
	})
	$(".catalogueContent").blur(function(){
		var appid = $(this).parents("section.app-box").attr("id");
		if( $("#"+appid+" .catalogueContent").val() )
		{
			$(this).parent().find(".checkTip").css({"display":"none"});
		}
		else{
			$(this).parent().find(".checkTip").css({"display":"block"});
		}
	})
	$(".addCatalogue").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		if( $("#"+appid+" .catalogueContent").val() )
		{
			var service_name = $("#service_name").val();
			var str = '<li><a href="javascript:void(0);"  class="path_name add_pathName">'+service_name+'</a>';
			str += '<em>/app/'+$("#"+appid+" .catalogueContent").val()+'</em>';
			str += '<img src="/static/www/images/rubbish.png" class="delLi"/></li>';
			$(str).appendTo("#"+appid+" .contentBlock ul.clearfix");
			$("#"+appid+" p.catalogue").css({"display":"none"});
			$("#"+appid+" .catalogueContent").val("");
			delLi();
		}
		else{
			swal("请输入目录～～");
		}
	});
	$(".noAddCatalogue").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		$("#"+appid+" p.catalogue").css({"display":"none"});
	});

	//挂载其他应用持久化目录
	$(".addOtherApp").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		var marleft = $("#main-content").attr("style");
		if(marleft){
			var arrleft = marleft.split(":");
			if(arrleft[1] == " 210px;"){
				$("#"+appid+" .layer-body-bg").css({"left":"-210px;"});
			}else{
				$("#"+appid+" .layer-body-bg").css({"left":"0px;"});
			}
		}else{
			$("#"+appid+" .layer-body-bg").css({"left":"-210px;"});
		}
		$("#"+appid+" .otherApp").css({"display":"block"});
		$("#"+appid+" .layer-body-bg").css({"display":"block"});
	});

	//挂载其他应用服务
	$(".sureAddOther").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		var len = $("#"+appid+" input.addOther").length;
		for( var i = 0; i<len; i++ )
		{
			if( $("#"+appid+" input.addOther").eq(i).is(":checked") )
			{
				var length = $("#"+appid+" .otherAppName").length;
				var onOff = true;
				for( var j = 0; j<length; j++ )
				{
					if( $("#"+appid+" input.addOther").eq(i).attr("data-otherName") == $("#"+appid+" .otherAppName").eq(j).attr("data-otherName") )
					{
						onOff = false;
						break;
					}
				}
				if( onOff )
				{
					var str = '<li><a href="javascript:void(0);"  class="path_name otherAppName" data-otherName="'+$("#"+appid+" input.addOther").eq(i).attr("data-otherName")+'">'+$("#"+appid+" input.addOther").eq(i).attr("data-name")+'</a>';
					str += '<em>'+$("#"+appid+" input.addOther").eq(i).attr("data-path")+'</em>';
					str += '<img src="/static/www/images/rubbish.png" class="delLi"/></li>';
					$(str).appendTo("#"+appid+" .contentBlock ul.clearfix");
					$("#"+appid+" .otherApp").css({"display":"none"});
					$("#"+appid+" .layer-body-bg").css({"display":"none"});
					delLi();
				}
			}
		}
		$("#"+appid+" .otherApp").css({"display":"none"});
		$("#"+appid+" .layer-body-bg").css({"display":"none"});
	});
	//关闭弹窗
	$("button.cancel").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		$("#"+appid+" .layer-body-bg").css({"display":"none"});
	});
	$(".del").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		$("#"+appid+" .layer-body-bg").css({"display":"none"});
	});


	tip();
	function tip(){
		$(".fn-tips").mouseover(function(){
			var tips = $(this).attr("data-tips");
			var pos = $(this).attr("data-position");
			var x = $(this).offset().left;
			var y = $(this).offset().top;
			var oDiv='<div class="tips-box"><p><span>'+ tips +'</span><cite></cite></p></div>';
			$("body").append(oDiv);
			var oDivheight = $(".tips-box").height();
			var oDivwidth = $(".tips-box").width();
			var othiswid = $(this).width();
			var othisheight = $(this).height();
			if(pos){
				if(pos == "top"){
					//
					$(".tips-box").css({"top":y-oDivheight -25});
					if(oDivwidth > othiswid){
						$(".tips-box").css({"left":x-(oDivwidth-othiswid)/2});
					}else if(oDivwidth < othiswid){
						$(".tips-box").css({"left":x + (othiswid - oDivwidth)/2});
					}else{
						$(".tips-box").css({"left":x});
					}
					$(".tips-box").find("cite").addClass("top");
					//
				}else if(pos == "bottom"){
					//
					$(".tips-box").css({"top":y + othisheight + 25});
					if(oDivwidth > othiswid){
						$(".tips-box").css({"left":x-(oDivwidth-othiswid)/2});
					}else if(oDivwidth < othiswid){
						$(".tips-box").css({"left":x + (othiswid - oDivwidth)/2});
					}else{
						$(".tips-box").css({"left":x});
					}
					$(".tips-box").find("cite").addClass("bottom");
					//
				}else if(pos == "left"){
					$(".tips-box").css({"top":y+5,"left":x-othiswid-5});
					$(".tips-box").find("cite").addClass("left");
				}else if(pos == "right"){
					$(".tips-box").css({"top":y+5,"left":x+othiswid+5});
					$(".tips-box").find("cite").addClass("right");
				}else{
					//
					$(".tips-box").css({"top":y-oDivheight -25});
					if(oDivwidth > othiswid){
						$(".tips-box").css({"left":x-(oDivwidth-othiswid)/2});
					}else if(oDivwidth < othiswid){
						$(".tips-box").css({"left":x + (othiswid - oDivwidth)/2});
					}else{
						$(".tips-box").css({"left":x});
					}
					$(".tips-box").find("cite").addClass("top");
					//
				}
			}else{
				//
				$(".tips-box").css({"top":y-oDivheight -25});
				if(oDivwidth > othiswid){
					$(".tips-box").css({"left":x-(oDivwidth-othiswid)/2});
				}else if(oDivwidth < othiswid){
					$(".tips-box").css({"left":x + (othiswid - oDivwidth)/2});
				}else{
					$(".tips-box").css({"left":x});
				}
				$(".tips-box").find("cite").addClass("top");
				//
			}

		});
		$(".fn-tips").mouseout(function(){
			$(".tips-box").remove();
		});
		////tips end
	}


	// 名称 compose 
	//var oldname = $("#com-name").val();
	/*$("#com-name").focus(function(){
	  	$(this).attr("value","");
	});
	$("#com-name").change(function(){
		if($(this).val()== ""){
			$(this).attr("value",oldname);
		}
	});
	$("#com-name").blur(function(){
		if($(this).val()== ""){
			$(this).attr("value",oldname);
		}
	});*/
	// 图
	var json_svg_ = $("#compose_relations").attr("value");
	var json_svg = JSON.parse(json_svg_);
	//console.log(json_svg_);
	//console.log(json_svg);
	

	/// svg
	var AppBot =[];        // 下部
    var AppTop = [];      //   上部
    var AppMid = [];     // 中部，即依赖别的
    var key_svg = [];    // key
    var val_svg_arr =[]; // 数组
    var val_svg = [];    //值
    var my_svg =[];      // 依赖自己
    var val_svg_single =[]; // 值数组去重

    Array.prototype.indexOf = function(val) {
        for (var i = 0; i < this.length; i++) {
            if (this[i] == val) return i;
        }
        return -1;
    };
    Array.prototype.remove = function(val) {
        var index = this.indexOf(val);
        if (index > -1) {
            this.splice(index, 1);
        }
    };
    
   for(var key in json_svg){
        key_svg.push(key);
        val_svg_arr.push(json_svg[key]);
        val_svg = val_svg.concat(json_svg[key]);
   }
   //console.log(key_svg.length);
   //console.log(key_svg); 
   //console.log(val_svg);
   //console.log(val_svg_arr);

   //
   if(key_svg.length == 0){
        console.log("没有依赖关系");
        $("#imgbtn").hide().removeClass("sed");
        $("#imgBox").hide();
        $("#tabBox").show();
        $("#tabbtn").addClass("sed");
   }else{
        for(var key in json_svg){
            if(json_svg[key].length == 0){
                AppBot.push(key);
                key_svg.remove(key);
                val_svg.remove(key);
            }else{
                for(var i=0;i<json_svg[key].length; i++){
                   if(json_svg[key][i] == key){
                        my_svg.push(key);
                        val_svg.remove(key);
                   } 
                }
            }
        }
    }
    //console.log(key_svg); 
    //console.log(val_svg);
   
    //数组去重
    for(i=0;i<val_svg.length;i++){
        if(val_svg_single.indexOf(val_svg[i])<0){
            val_svg_single.push(val_svg[i])
        }
    }    
    //console.log(val_svg_single);

    for(var i=0;i<val_svg_single.length;i++){
        if(key_svg.indexOf(val_svg_single[i]) == -1){
            AppBot.push(val_svg_single[i]);
        }else{
            AppMid.push(val_svg_single[i]);
        }
    }
    for(var i=0;i<key_svg.length;i++){
        if(val_svg_single.indexOf(key_svg[i]) == -1){
            AppTop.push(key_svg[i]);
        }
    }
    //console.log(my_svg);
    //console.log(AppTop);
    //console.log(AppMid);
    //console.log(AppBot);

    var AppBot_B = [];
    for(i=0;i<AppBot.length;i++){
        if(AppBot_B.indexOf(AppBot[i])<0){
            AppBot_B.push(AppBot[i])
        }
    }   
    
    //绘图
    var svgNS = 'http://www.w3.org/2000/svg';
    var svgLink="http://www.w3.org/1999/xlink";
    var oSvgDiv = document.getElementById("view-svg");
    var divWidth = oSvgDiv.offsetWidth;
    var axisXY  = {};  //坐标
    // 创建函数
    function createTag(tag,objAttr){
        var oTag = document.createElementNS(svgNS , tag);
        for(var attr in objAttr){
            oTag.setAttribute(attr,objAttr[attr]);
        }
        return oTag;
    }
    var oSvg = createTag('svg',{'xmlns':svgNS,'xmlns:xlink':svgLink,'width':'100%','height':'600'});
    var oDefs = createTag('defs',{});
    var oMarker = createTag('marker',{'id':'markerArrow','markerWidth':'13','markerHeight':'13','refX':'35','refY':'6','orient':'auto'});
    var oPath = createTag('path',{'d':'M2,2 L2,11 L10,6 L2,2 z','fill':'#ccc'});
    oSvg.appendChild(oDefs);
    oDefs.appendChild(oMarker);
    oMarker.appendChild(oPath);


    // 添加图片
    function FnSvgIcon(wid,hei,num,txt,txtWid){
        var oImg = createTag('image',{'width':'60px','height':'60px','x':(wid*num+wid/2-30),'y':hei});
        var oText = createTag('text',{'x':(wid*num+wid/2),'y':hei+70,'font-size':'12','text-anchor':'middle','fill':'#999','lengthAdjust':'spacing'});
        oText.innerHTML = txt;
        oImg.setAttributeNS(svgLink,'xlink:href','/static/www/images/app1.png');
        var oA= createTag('a',{'href':"javascript:;"});
        var oG = createTag('g',{'style':'cursor:pointer'});
        oA.appendChild(oText);
        oA.appendChild(oImg);
        oG.appendChild(oA);
        oSvg.appendChild(oG);
    }
    if(AppTop.length != 0){
        for(var i=0; i<AppTop.length;i++){
            var top_width = divWidth/AppTop.length;
            var top_w = top_width - 20;
            //FnSvgIcon(top_width,30,i,AppTop[i],top_w); 
            axisXY[AppTop[i]] = [(top_width*i+top_width/2),50];
        }
    }
    if(AppMid.length != 0){
        for(var i=0; i<AppMid.length;i++){
            var mid_width = divWidth/AppMid.length;
            var mid_w = mid_width - 20;
            //FnSvgIcon(mid_width,170,i,AppMid[i],mid_w);
            axisXY[AppMid[i]] = [(mid_width*i+mid_width/2),200];
        }
    }
    if(AppBot_B.length != 0){
        for(var i=0; i<AppBot_B.length;i++){
            var bot_width = divWidth/AppBot_B.length;
            var bot_w = bot_width - 20;
            //FnSvgIcon(bot_width,320,i,AppBot_B[i],bot_w);
            axisXY[AppBot_B[i]] = [(bot_width*i+bot_width/2),350];
        }
    }
    //
    for(var key in json_svg){
        if(json_svg[key].length != 0){
            //console.log(key);
            //console.log(axisXY[key]);
            //console.log(json_svg[key]);
            for(var i=0; i<json_svg[key].length; i++){
                //console.log(axisXY[json_svg[key][i]]);
                var startX = axisXY[key][0];
                //console.log(startX);
                var startY = axisXY[key][1];
                //console.log(startY);
                var endX = axisXY[json_svg[key][i]][0];
                //console.log(endX);
                var endY = axisXY[json_svg[key][i]][1];
                //console.log(endY);
                var oLine = createTag('line',{'x1':startX,'y1':startY,'x2':endX,'y2':endY,'stroke':'#ccc','marker-end':'url(#markerArrow)'});
                //console.log(oLine);
                oSvg.appendChild(oLine);
            }
        }
    }
    //
    if(AppTop.length != 0){
        for(var i=0; i<AppTop.length;i++){
            var top_width = divWidth/AppTop.length;
            var top_w = top_width - 20;
            FnSvgIcon(top_width,30,i,AppTop[i],top_w); 
            //axisXY[AppTop[i]] = [(top_width*i+top_width/2),50];
        }
    }
    if(AppMid.length != 0){
        for(var i=0; i<AppMid.length;i++){
            var mid_width = divWidth/AppMid.length;
            var mid_w = mid_width - 20;
            FnSvgIcon(mid_width,170,i,AppMid[i],mid_w);
            //axisXY[AppMid[i]] = [(mid_width*i+mid_width/2),200];
        }
    }
    if(AppBot_B.length != 0){
        for(var i=0; i<AppBot_B.length;i++){
            var bot_width = divWidth/AppBot_B.length;
            var bot_w = bot_width - 20;
            FnSvgIcon(bot_width,320,i,AppBot_B[i],bot_w);
            //axisXY[AppBot_B[i]] = [(bot_width*i+bot_width/2),350];
        }
    }
    //

    oSvgDiv.appendChild(oSvg);
	/// svg
	//图

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
	    	console.log(this_json);
	    	secdate.push(this_json);
    	});
    	console.log(secdate);
    	//
		var tenantName = $("#tenantNameValue").val();
		var compose_group_name = $("#com-name").val();
		
    	///
    	//$.ajax({
         //   type: "post",
         //   url: "/apps/"+tenantName+"/compose-params/",
         //   dataType: "json",
			//data: {
			//		"service_configs":JSON.stringify(secdate),
			//		"compose_group_name":compose_group_name
			//		},
			//beforeSend : function(xhr, settings) {
			//	var csrftoken = $.cookie('csrftoken');
			//	xhr.setRequestHeader("X-CSRFToken", csrftoken);
			//},
			//success:function(data){
			//	status = data.status;
			//	if (status == 'success'){
			//		window.location.href="/apps/"+tenantName +"/"
			//	}else if (status == "failure"){
			//		swal("数据中心初始化失败");
			//	}else if (status == "owed"){
			//		swal("余额不足请及时充值");
			//	}else if (status =="expired"){
			//		swal("试用期已过");
			//	}else if(status =="over_memory"){
			//		swal("资源已达上限,无法创建");
			//	}else if(status == "over_money"){
			//		swal("余额不足无法创建");
			//	}else{
			//		swal("创建失败")
			//	}
			//},
			//error: function() {
			//	$(this).attr('disabled',false);
         //   },
         //   cache: false
         //   // processData: false
        //});
		
    	///
    });
	///////

	/////切换
	$(".tablink a").click(function(){
		var num = $(this).index();
		$(".tablink a").removeClass("sed");
		$(this).addClass("sed");
		$("section.fn-app-box").hide();
		$("section.fn-app-box").eq(num).show();
	});

	$("#view-svg g").click(function(){
		var oHtml = $(this).find("text").html();
		console.log(oHtml);
		var num;
		$(".tablink a").each(function(){
			var oText = $(this).html();
			if(oText == oHtml){
				num = $(this).index();
				//console.log(num);
			}
		});
		$(".tablink a").removeClass("sed");
		$(".tablink a").eq(num).addClass("sed");
		$("section.fn-app-box").hide();
		$("section.fn-app-box").eq(num).show();
	});
	$("#pre_page").click(function () {
		var compose_file_id = $("#compose_file_id").val();
		var tenantName = $("#tenantNameValue").val();
		url = "/apps/"+tenantName+"/compose-create?id="+compose_file_id;
		window.location.href = url
	})
});




