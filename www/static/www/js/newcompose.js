$(function(){
	$(".fn-showlink").click(function(){
        var htmlstr = $(this).find("cite").html();
        var parents = $(this).parents(".fn-modulebox");
        if(htmlstr == "展开"){
            $(this).find("cite").html("收起");
            $(this).find("span").removeClass("glyphicon-chevron-down").addClass("glyphicon-chevron-up");
            $(parents).find(".fn-showblock").show();
        }else{
            $(this).find("cite").html("展开");
            $(this).find("span").removeClass("glyphicon-chevron-up").addClass("glyphicon-chevron-down");
            $(parents).find(".fn-showblock").hide();
        }
    })

	//打开新增端口号窗口
	$(".openAdd").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		// if( $(this).parents("tfoot").find("input.checkDetail").prop("checked") )
		// {
		// 	$(this).parents('tfoot').find("option.changeOption").remove();
		// 	$("#"+appid+" select.add_http").val("HTTP");
		// }
		// else{
		// 	var $option = $("<option class='changeOption'>请打开外部访问</option>")
		// 	$(this).parents('tfoot').find("select.add_http").prepend($option);
		// 	$("#"+appid+" select.add_http").val("请打开外部访问");
		// }
		$("#"+appid+" .checkTip").css({"display":"none"});
		$("#"+appid+" .addPort").css({"display":"table-row"});
	});
	$(".add_port").blur(function(){
		var appid = $(this).parents("section.app-box").attr("id");
		var portNum = parseInt($("#"+appid+" .add_port").val());
		if( portNum>0 && portNum<65536 )
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
		if( portNum>0 && portNum<65536 )
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
				var oTr = '<tr><td><a href="javascript:void(0);" class="portNum edit-port fn-tips" data-original-title="当前应用提供服务的端口号。">'+$("#"+appid+" .add_port").val()+'</a></td>';
				if( $("#addInner"+appid+"").prop("checked") == true )
				{
					oTr += '<td><label class="checkbox fn-tips" data-original-title="打开对外服务，其他应用即可访问当前应用。"><input type="checkbox" name="" value="" id="'+$("#"+appid+" .add_port").val()+'inner'+appid+'" checked="true" /><span class="check-bg" for="'+$("#"+appid+" .add_port").val()+'inner'+appid+'"></span></label></td>';
				}
				else{
					oTr += '<td><label class="checkbox fn-tips" data-original-title="打开对外服务，其他应用即可访问当前应用。"><input type="checkbox" name="" value="" id="'+$("#"+appid+" .add_port").val()+'inner'+appid+'" /><span class="check-bg" for="'+$("#"+appid+" .add_port").val()+'inner'+appid+'"></span></label></td>';
				}
				if( $("#addOuter"+appid+"").prop("checked") == true )
				{
					oTr += '<td><label class="checkbox fn-tips" data-original-title="打开外部访问，用户即可通过网络访问当前应用。"><input class="checkDetail" type="checkbox" name="" value="" id="'+$("#"+appid+" .add_port").val()+'outer'+appid+'" checked="true" /><span class="check-bg" for="'+$("#"+appid+" .add_port").val()+'outer'+appid+'"></span></label></td><td>';
					oTr += '<select class="fn-tips" data-original-title="请设定用户的访问协议。" data-port-http="'+$("#"+appid+" .add_port").val()+'http">';
				}
				else{
					oTr += '<td><label class="checkbox fn-tips" data-original-title="打开外部访问，用户即可通过网络访问当前应用。"><input class="checkDetail" type="checkbox" name="" value="" id="'+$("#"+appid+" .add_port").val()+'outer'+appid+'" /><span class="check-bg" for="'+$("#"+appid+" .add_port").val()+'outer'+appid+'"></span></label></td><td>';
					oTr += '<select class="fn-tips" data-original-title="请设定用户的访问协议。" data-port-http="'+$("#"+appid+" .add_port").val()+'http">';
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
				//修改端口号
			    editCom('.edit-port', function(value){
			         if( !(value>0 && value<65536) ){
			            return "端口范围为1-65535";
			         }

			         if (!$.trim(value)) {
			            return '不能为空';
			         }
			    });
				$('.fn-tips').tooltip();
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
	//checkDetail();
	function checkDetail(){
		$("input.checkDetail").off("click");
		$("input.checkDetail").on("click",function(){
			var appid = $(this).parents("section.app-box").attr("id");
			if( $(this).prop("checked") )
			{
				$(this).parents("tr").find("option.changeOption").remove();
				$(this).parents("tr").find("select").val("HTTP");
				$(this).parents("tr").find("select").css({"color":"#28cb75"}).removeAttr("disabled");
			}
			else
			{
				$option = $("<option class='changeOption'>请打开外部访问</option>")
				$(this).parents("tr").find("select").prepend($option);
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
					$(this).parents("tr").find("select").val("HTTP");
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
				if( $(this).val() == '非HTTP' )
				{
					var len = $("#"+appid+" table.tab-box tbody select").length;
					for( var i = 0; i<len; i++ )
					{
						if( $("#"+appid+" table.tab-box tbody input.checkDetail").eq(i).prop("checked") && $("#"+appid+" table.tab-box tbody select").eq(i).val() == '非HTTP' && i != $(this).attr("index") )
						{
							swal("访问方式只能有一个非HTTP");
							$(this).val("HTTP");
							break;
						}
					}
				}
			})
		}
	}
	//修改端口号
    editCom('.edit-port', function(value){
         if( !(value>0 && value<65536) ){
            return "端口范围为1-65535";
         }

         if (!$.trim(value)) {
            return '不能为空';
         }
    });
     //修改变量name
    editCom('.edit-env-name')
    //修改变量key
    editCom('.edit-env-key', function(value){
        var variableReg = /^[A-Z][A-Z0-9_]*$/;
        if( !variableReg.test(value||'') )
        {
            return '变量名由大写字母与数字组成且大写字母开头';
        }
    })
    //修改变量值
    editCom('.edit-env-val');

	function editCom(selector, validate){
        $(selector).editable({
			type: 'text',
			pk: 1,
			success: function (data) {

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
			},
			validate: function (value) {


				if (!$.trim(value)) {
                    return '不能为空';
                }
                
                if(validate){
                    return validate(value)
                }
			}
		});
	}


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
		if( $("#"+appid+" .enviroKey").val() && $("#"+appid+" .enviroValue").val() && $("#"+appid+" .enviroName").val() )
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
					var str = '<tr><td><a href="javascript:void(0);" class="enviromentName edit-env-name">'+$("#"+appid+" .enviroName").val()+'</a></td>';
					str += '<td><a href="javascript:void(0);" class="edit-env-key enviromentKey">'+$("#"+appid+" .enviroKey").val()+'</a></td>';
					str += '<td><a href="javascript:void(0);" class="edit-env-val enviromentValue">'+$("#"+appid+" .enviroValue").val()+'</a></td>';
					str += '<td><img class="rubbish" src="/static/www/images/rubbish.png"/></td></tr>';
					$(str).appendTo("#"+appid+" .enviroment");
					$("#"+appid+" .enviroName").val('');
					$("#"+appid+" .enviroKey").val('');
					$("#"+appid+" .enviroValue").val('');
					$("#"+appid+" .addContent").css({"display":"none"});
					delPort();
					 //修改变量name
				    editCom('.edit-env-name')
				    //修改变量key
				    editCom('.edit-env-key', function(value){
				        var variableReg = /^[A-Z][A-Z0-9_]*$/;
				        if( !variableReg.test(value||'') )
				        {
				            return '变量名由大写字母与数字组成且大写字母开头';
				        }
				    })
				    //修改变量值
				    editCom('.edit-env-val');
				}
				else{
					swal("变量名由大写字母开头，可以加入数字～～");
				}
			}
		}
		else{
			swal("请输入环境变量");
		}
	});
	$(".noAddEnviroment").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		$("#"+appid+" .addContent").css({"display":"none"});
		$("#"+appid+" .enviroName").val('');
		$("#"+appid+" .enviroKey").val('');
		$("#"+appid+" .enviroValue").val('');
	});
	delLi();
	//删除依赖与目录
	function delLi(){
		$("img.delLi").off("click");
		$("img.delLi").on("click",function(){
			$(this).parents("tr").remove();
		})
	}
	//新设持久化目录
	$(".addCata").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		$("#"+appid+" .catalogue").css({"display":"table-row"});
	})
	$(".catalogueContent").blur(function(){
		var appid = $(this).parents("section.app-box").attr("id");
		if( $("#"+appid+" .catalogueContent").val() )
		{
			$(this).parent().find(".checkTip").css({"display":"none"});
		}
		else{
			$(this).parent().find(".checkTip").html("请输入持久化目录");
			$(this).parent().find(".checkTip").css({"display":"inline-block"});
		}
	})
	$(".catalogueName").blur(function(){
		var appid = $(this).parents("section.app-box").attr("id");
		if( $("#"+appid+" .catalogueName").val() )
		{
			$(this).parent().find(".checkTip").css({"display":"none"});
		}
		else{
			$(this).parent().find(".checkTip").html("请输入持久化名称");
			$(this).parent().find(".checkTip").css({"display":"inline-block"});
		}
	})
	$(".addCatalogue").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		var result = true;
		if( $("#"+appid+" .catalogueContent").val() )
		{
			
			var len = $("#"+appid+" .add_pathName").length;
			for( var i = 0; i<len; i++ )
			{
				var str = '/app/'+ $("#"+appid+" .catalogueContent").val();
				if( str == $("#"+appid+" .add_pathName").eq(i).parent().find("em").html() )
				{
					result = false;
					swal("目录冲突，请重新输入");
					$("#"+appid+" .catalogueContent").val('');
					$(this).parent().find(".checkTip").css({"display":"inline-block"});
					break;
				}
			}
		}else{
			swal("请输入目录");
			$("#"+appid+" .catalogueContent").val('');
			$(this).parent().find(".checkTip").css({"display":"inline-block"});
			result = false;
		}

		if( $("#"+appid+" .catalogueName").val() )
		{
			
			var len = $("#"+appid+" .add_pathName").length;
			for( var i = 0; i<len; i++ )
			{
				var str = $("#"+appid+" .catalogueName").val();
				if( str == $("#"+appid+" .add_pathName").eq(i).html() )
				{
					result = false;
					swal("名称冲突，请重新输入");
					$("#"+appid+" .catalogueName").val('');
					$(this).parent().find(".checkTip").css({"display":"inline-block"});
					break;
				}
			}
		}else{
			swal("请输入名称");
			$("#"+appid+" .catalogueName").val("");
			$(this).parent().find(".checkTip").css({"display":"inline-block"});
			result = false;
		}
		if( result )
		{
				var str = '<tr><td><em class="fn-tips" data-original-title="当前应用所在目录为/app/，使用持久化目录请注意路径关系。">/app/'+$("#"+appid+" .catalogueContent").val()+'</em></td>';
				str += '<td><span class="path_name add_pathName">'+ $("#"+appid+" .catalogueName").val() +'</span></td>';
                str +='<td><span data-value="'+$(".catalogue").find($("#"+appid+" option:selected")).attr("value")+'" class="stateVal">'+ $(".catalogue").find('select option:selected').html() +'</span></td>'
				str += '<td><img src="/static/www/images/rubbish.png" class="delLi"/></li></td>';
				$(str).appendTo("#"+appid+" .contentBlock");
				$("#"+appid+" .catalogue").css({"display":"none"});
				$("#"+appid+" .catalogueContent").val("");
				$("#"+appid+" .catalogueName").val("");
				delLi();
				$('.fn-tips').tooltip();
		}
	});
	$(".noAddCatalogue").on("click",function(){
		var appid = $(this).parents("section.app-box").attr("id");
		$("#"+appid+" .catalogue").css({"display":"none"});
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
					var str = '<li><em class="fn-tips" data-original-title="当前应用所在目录为/app/，使用持久化目录请注意路径关系。">'+$("#"+appid+" input.addOther").eq(i).attr("data-path")+'</em>';
					str = '<span class="path_name otherAppName" data-otherName="'+$("#"+appid+" input.addOther").eq(i).attr("data-otherName")+'">挂载自'+$("#"+appid+" input.addOther").eq(i).attr("data-name")+'</span>';
					str += '<img src="/static/www/images/rubbish.png" class="delLi"/></li>';
					$(str).appendTo("#"+appid+" .contentBlock ul.clearfix");
					$("#"+appid+" .otherApp").css({"display":"none"});
					$("#"+appid+" .layer-body-bg").css({"display":"none"});
					delLi();
					$('.fn-tips').tooltip();
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


	$('.fn-tips').tooltip();


    
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
	});

	/*ww-2017-11-6*/
	$(".fn-app-box").each(function(){
        var this_id= $(this).attr("id");
		$("#"+ this_id + "_MemoryRange a").click(function(){
	        $("#"+ this_id + "_MemoryRange a").removeClass("sed");
	        $(this).addClass("sed");
	        var memoryVal = $(this).html();
	        $("#"+ this_id + "_MemoryText").html(memoryVal);
	    });
   	 	$("#"+ this_id + "_stateless").click(function(){
	        var oval= $("#"+ this_id + "_stateless").attr("checked");
	        if(oval == true){
	            var optionbox = '<option value="share-file">共享存储(文件)</option><option value="memoryfs">内存文件存储</option>';
	        }else{
	            var optionbox = '<option value="share-file">共享存储(文件)</option><option value="local">本地存储</option><option value="memoryfs">内存文件存储</option>';
	        }
	        var selectbox = $("#"+ this_id + "_statebox");
        	$(selectbox).empty();
        	$(optionbox).appendTo($(selectbox));
	    });
	    $("#"+ this_id + "_state").click(function(){
	        var oval= $("#"+ this_id + "_stateless").attr("checked");
	        if(oval == false){
	            var optionbox = '<option value="share-file">共享存储(文件)</option><option value="memoryfs">内存文件存储</option>';
	        }else{
	            var optionbox = '<option value="share-file">共享存储(文件)</option><option value="local">本地存储</option><option value="memoryfs">内存文件存储</option>';
	        }
	        var selectbox = $("#"+ this_id + "_statebox");
        	$(selectbox).empty();
        	$(optionbox).appendTo($(selectbox));
	    });
   	});

	
	/*ww-2017-11-6*/


	submitMsg();
	function submitMsg(){
		$("#build-app").on("click",function(){
			$(this).attr('disabled',true);
			var secbox= $(".app-box");
			var secdate = [];
			$(secbox).each(function(){
				var appid = $(this).attr("id");
				var service_cname = $(this).attr("service_cname")
				var service_image = $(this).attr("service_image")
				var service_id = $(this).attr("id")
				console.log(service_id+"\t"+service_cname+"\t"+service_image)

				//console.log(appid);
				//
				var port_tr = $(this).find("tbody.port").children("tr");
				var port_nums = [];
				$(port_tr).each(function(i){
					var json_port = {};
					var my_port = $(this).children("td").eq(0).find("a.portNum").html();
					var my_agreement = $(this).children("td").eq(3).find("select").val();
					if( my_agreement == 'HTTP' )
					{
						my_agreement = 'http';
					}
					else if( my_agreement = '非HTTP' )
					{
						my_agreement = 'stream';
					}
					else{
						my_agreement = 'http';
					}
					var my_inner = $(this).children("td").eq(1).find("input").prop("checked")? 1 : 0;
					var my_outer = $(this).children("td").eq(2).find("input").prop("checked")? 1 : 0;
					json_port["container_port"] = my_port;
					json_port["protocol"] = my_agreement;
					json_port["is_inner_service"] = my_inner;
					json_port["is_outer_service"] = my_outer;
					json_port["port_alias"] = ("gr"+service_id.substr(service_id.length-6)).toUpperCase()+my_port;
					port_nums[i] = json_port;
				});
				//console.log(port_nums);
				//
				var env_tr = $(this).find("tbody.enviroment").children("tr");
				var env_nums = [];
				$(env_tr).each(function(i){
					var json_environment = {};
					var my_name = $(this).children("td").eq(0).find("a.enviromentName").html();
					var my_engname = $(this).children("td").eq(1).find("a.enviromentKey").html();
					var my_value = $(this).children("td").eq(2).children("a.enviromentValue").html();
					json_environment["name"] = my_name;
					json_environment["attr_name"] = my_engname;
					json_environment["attr_value"] = my_value;
					env_nums[i] = json_environment;
				});
				//console.log(env_nums);
				//
				var dir_tr = $(this).find(".add_pathName");
				var dir_nums = [];
				$(dir_tr).each(function(i){
					var json_directory = {};
					var my_name = $(this).html();
					var my_path = $(this).parents().find('em').html();
					var my_type= $(this).parents().find("span.stateVal").attr("data-value");
					json_directory["volume_pathName"] = my_name;
					json_directory["volume_path"] = my_path;
					json_directory["volume_type"] = my_type;
					dir_nums[i] = json_directory;
				});

				var dir_other = $(this).find("a.otherAppName");
				var dir_otherArr = [];
				$(dir_other).each(function(i){
					var json_directory = {};
					var my_name = $(this).html();
					var my_path = $(this).parent().find('em').html();
					json_directory["volume_pathName"] = my_name;
					json_directory["volume_path"] = my_path;
					dir_otherArr[i] = json_directory;
					console.log(json_directory);
				});

				var deps = $(this).find(".depends_service ").find("td");
				var depends_services = []
				$(deps).each(function (i) {
					// var depends_service = {}
					var dps_service_name = $(this).html();
					// depends_service["depends_service"] = dps_service_name;
					depends_services[i] = dps_service_name;
				});
				
				//
				var resources = $(this).find(".resources option:selected").val();
				console.log(resources);
				//
				var order = $(this).find(".order").val();
				//
				var  methodval=	$('input[name="'+ appid +'_extend_method"]:checked').val();
        		var  memory_num = parseInt($("#"+ appid + "_MemoryText").html());
        		//
				var this_json={
					"service_image":service_image,
					"service_cname":service_cname,
					"service_id" : appid,
					"port_list" : port_nums,
					"env_list" : env_nums,
					"volume_list" : dir_nums,
					"depends_services":depends_services,
					"compose_service_memory" : dir_otherArr,
					"start_cmd" : order,
					"methodval": methodval,
            		"service_min_memory" : memory_num
				}
				secdate.push(this_json);
				console.log(this_json)
			});
			console.log(secdate);
			//
			var tenantName = $("#tenantNameValue").val();
			// var compose_group_name = $("#com-name").val();

			///
			$.ajax({
				type: "post",
				url: "/apps/"+tenantName+"/compose-step3/",
				dataType: "json",
				data: {
					"service_configs":JSON.stringify(secdate),
				},
				beforeSend : function(xhr, settings) {
					var csrftoken = $.cookie('csrftoken');
					xhr.setRequestHeader("X-CSRFToken", csrftoken);
					$("#build-app").off("click");
				},
				success: function (data) {
					status = data.status;
					if (status == 'success') {
						window.location.href = "/apps/" + tenantName + "/"
					} else if (status == "failure") {
						swal("数据中心初始化失败");
						submitMsg();
					} else if (status == "owed") {
						swal("余额不足请及时充值");
						submitMsg();
					} else if (status == "no_service") {
						swal("服务不存在");
						submitMsg();
					} else if (status == "over_memory") {
						swal("资源已达上限,无法创建");
						submitMsg();
					} else if (status == "over_money") {
						swal("余额不足无法创建");
						submitMsg();
					} else {
						swal("创建失败")
						submitMsg();
					}
				},
				error: function() {
					$(this).attr('disabled',false);
					submitMsg();
				},
				cache: false
				// processData: false
			});

			///
		});
	}
});




