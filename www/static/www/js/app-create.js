var BranchLocalData = {};
//创建应用
$(function(){
    $('#create_app_name').blur(function(){
        var appName = $(this).val(),
            checkReg = /^[a-z][a-z0-9-]*[a-z0-9]$/,
            result = true;
            
        if(!checkReg.test(appName)){
        	$("#create_app_name").focus()
        	scrollOffset($("#create_app_name").offset()); 
            $('#create_appname_notice').slideDown();
            return;
        }else{
            $('#create_appname_notice').slideUp();
        }
    });
    //第一步
    $('#first_step').click(function(){
        var appName = $('#create_app_name').val(),
            checkReg = /^[a-z][a-z0-9-]*[a-z0-9]$/,
            result = true;
            
        if(!checkReg.test(appName)){
        	$("#create_app_name").focus()
        	scrollOffset($("#create_app_name").offset()); 
            $('#create_appname_notice').slideDown();
            return;
        }else{
            $('#create_appname_notice').slideUp();
        }
        var codeStoreSel = $(':radio:checked', $('#sel_code_store')).val();
        if((codeStoreSel == 'option2' || codeStoreSel == 'option3') && !$('.duigou_icon', $('#code_store_list')).length){
            // $('#create_codestore_notice').removeClass('alert-info').addClass('alert-danger').slideDown();
            $('#create_codestore_notice').slideDown();
            return;
        }
        var service_code_id = $("#service_code_id").val()
        var gitValue = $("#git_version_"+service_code_id).val();
        $("#service_code_version").val(gitValue);        
        $("#first_step").attr('disabled', true);
    	var _data = $("form").serialize();
        var tenantName= $('#currentTeantName').val();
    	$.ajax({
    		type : "post",
    		url : "/apps/" + tenantName + "/app-create/",
    		data : _data,
    		cache : false,
    		beforeSend : function(xhr, settings) {
    			var csrftoken = $.cookie('csrftoken');
    			xhr.setRequestHeader("X-CSRFToken", csrftoken);
    		},
    		success : function(msg) {
    			var dataObj = msg;
    			if (dataObj["status"] == "exist") {
    				swal("服务名已存在");
    			} else if (dataObj["status"] == "owed"){
    				swal("余额不足请及时充值")
    			} else if (dataObj["status"] == "over_memory") {
    				swal("免费资源已达上限，不能创建");
    			} else if (dataObj["status"] == "over_money") {
    				swal("余额不足，不能创建");
    			} else if (dataObj["status"] == "empty") {
    				swal("应用名称不能为空");
    			}else if (dataObj["status"] == "code_from") {
    				swal("应用资源库未选择");
    			}else if (dataObj["status"] == "code_repos") {
    				swal("代码仓库异常");
    			}else if (dataObj["status"] == "success") {
    				service_alias = dataObj["service_alias"]
    				window.location.href = "/apps/" + tenantName + "/" + service_alias + "/app-dependency/";
    			} else {
    				swal("创建失败");
                }
    		    $("#first_step").attr('disabled', false);
    		},
    		error : function() {
    			swal("系统异常,请重试");
    			$("#first_step").attr('disabled', false);
    		}
    	})
    });
    //代码仓库选择
    $(':radio', $('#sel_code_store')).click(function(){
        var selOption = $(this).val();
        if(selOption == 'option1'){
        	$('#service_code_from').val("gitlab_new");
            $('#code_store_list').slideUp();
            $('#wait_loading').hide();
        }else if(selOption == 'option2'){
            BranchLocalData = {};
        	$('#service_code_from').val("gitlab_exit");
            $('#code_store_list').hide();
            $('#create_codestore_notice').hide();
            $('#wait_loading').slideDown();
            var tenantName= $('#currentTeantName').val();
            _url = "/ajax/"+tenantName+"/code_repos?action=gitlab";
            loadRepos(_url);
        }else if(selOption == 'option3'){
            BranchLocalData = {};
        	$('#service_code_from').val("github");
            $('#code_store_list').hide();
            $('#create_codestore_notice').hide();
            $('#wait_loading').slideDown();
            var tenantName= $('#currentTeantName').val();
            _url = "/ajax/"+tenantName+"/code_repos?action=github";
            loadRepos(_url);
        }
    });
});

function loadRepos(_url){
    listWrap = $('#code_store_list');
	$.ajax({
	     type: "GET",
	     url: _url,
	     cache: false,
         success: function(msg){
             var dataObj = msg;
             if(dataObj["status"] == "unauthorized"){
                window.open(dataObj["url"], "_parent");
             }else if(dataObj["status"]=="success"){
               var dataList=dataObj["data"];
               var htmlmsg="";
               for(var i=0;i<dataList.length;i++){
                 data = dataList[i];
                 htmlmsg +='<tr idx="'+ i +'" data="'+data["code_id"]+'">';
                 htmlmsg +='<input type="hidden" id="repos_'+data["code_id"]+'" name="repos_'+data["code_id"]+'" value='+data["code_repos"]+' />';
                 htmlmsg +='<td class="text-center"><i></i></td>';
                 htmlmsg +='<td><div class="lh34">'+data["code_user"]+'/'+data["code_project_name"]+'</div></td>';
                 htmlmsg +='<td><select class="form-control" style="width: 150px; display: none;" id="git_version_'+data['code_id']+'"> </select><div class="lh34" id="git_version_notice_'+ data['code_id'] +'" style="color: #31708f; display: none;">正在读取项目分支信息</div></td>';
                 htmlmsg +='</tr>';
               }
               $('tbody', listWrap).html(htmlmsg);
               $('#wait_loading').hide();
               listWrap.slideDown();
               
               $('select', listWrap).click(function(e){
                   event = e || window.event;
                   event.stopPropagation();
               });
               
               $('tr', listWrap).click(function(){
                   var iObj = $('i', $(this));
                   if(iObj.hasClass('duigou_icon')){
                       iObj.removeClass('duigou_icon');
                       $(this).removeClass('create_codestore_trsed');
                       var service_code_id=$(this).attr("data");
                       $("#service_code_id").val("");
                       $("#service_code_clone_url").val("")
                       if(!$('.duigou_icon', $('#code_store_list')).length){
                            $('#create_codestore_notice').slideDown();
                       }
                       // $('#create_codestore_notice').removeClass('alert-info').addClass('alert-danger').html('请选择相应的代码仓库和分支');
                   }else{
                       $('.duigou_icon', listWrap).removeClass('duigou_icon');
                       $('.create_codestore_trsed', listWrap).removeClass('create_codestore_trsed');
                       iObj.addClass('duigou_icon');
                       $(this).addClass('create_codestore_trsed');
                       var service_code_id=$(this).attr("data");                       
                       $("#service_code_id").val(service_code_id);
                       var clone_url = $('#repos_'+service_code_id).val();
                       $("#service_code_clone_url").val(clone_url);
                       var gitValue = $("#git_version_"+service_code_id).val();
                       if(gitValue == null || gitValue == ""){
                           var service_code_from = $('#service_code_from').val();
                           var isLoad = $('#git_version_notice_' + service_code_id).attr('load');
                           if(typeof BranchLocalData[service_code_id] == 'undefined'){
                                $('#git_version_notice_' + service_code_id).show();
                                projectVersion(service_code_from,service_code_id,clone_url);
                           }
                           // $('#create_codestore_notice').removeClass('alert-danger').addClass('alert-info').html("正在读取项目分支信息");
                            // $('#create_codestore_notice').slideUp(); 
                       }else{
                    	   $('#create_codestore_notice').slideUp(); 
                       }
                   }
               });           
             }else{
               $('#wait_loading').html("无可用仓库")
             }
       },
       error: function(){
       //swal("系统异常");
       }
	})
}

function projectVersion(code_from,code_id,clone_url){
	var action="";
	var user ="";
	var repos ="";
	if(code_from=="gitlab_exit"){
		action="gitlab";
	}else if(code_from=="github"){
		action="github";
		user =  clone_url.split("/")[3];
		repos = clone_url.split("/")[4].split(".")[0];
	}
	var tenantName= $('#currentTeantName').val();
	if(action != ""){
	 $.ajax({
	       type : "POST",
	       url : "/ajax/"+tenantName+"/code_repos",
	       data : "action=" + action + "&code_id="+code_id+"&user="+user+"&repos="+repos,
	       cache : false,
	       beforeSend : function(xhr, settings) {
	         var csrftoken = $.cookie('csrftoken');
	         xhr.setRequestHeader("X-CSRFToken", csrftoken);
	       },
	       success : function(msg) {
	         var dataObj = msg;
	         if(dataObj["status"] == "unauthorized") {
	           window.open(dataObj["url"],"_parent");
	         }else if(dataObj["status"] == "success"){
                var dataList=dataObj["data"];
                var htmlmsg="";
                var codeId = dataObj['code_id'];
                //htmlmsg +='<select name="code_version_'+code_id+'" id="code_version_'+code_id+'" class="form-control" style="width: 150px;">'
                if(typeof BranchLocalData[codeId] == 'undefined'){
                    BranchLocalData[codeId] = dataList;
                }
                for(var i=0;i<dataList.length;i++){
                     data = dataList[i];
                     htmlmsg +='<option value="'+data["version"]+'">'+data["version"]+'</option>';
                }
                //htmlmsg +='</select>'
                if(htmlmsg){
                    $('#create_codestore_notice').slideUp();
                    $("#git_version_"+codeId).html(htmlmsg).show();
                    $("#git_version_notice_" + codeId).hide();
                }else{
                    $("#git_version_notice_" + codeId).text('暂无可选分支');
                }
	         }else {
	           swal("操作失败");
	         }
	       },
	       error : function() {
	         // swal("系统异常");
	       }
	     })
	}
}

function scrollOffset(scroll_offset) { 
	$("body,html").animate({scrollTop: scroll_offset.top - 70}, 0); 
} 

