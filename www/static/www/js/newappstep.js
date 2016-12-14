$(function(){
	// 滑块 开始 
	function FnRange(inputid,textid,widid,num,maxnum){
		var range= document.getElementById(inputid);
		var result = document.getElementById(textid);
		var wid = document.getElementById(widid);
		cachedRangeValue = /*localStorage.rangeValue ? localStorage.rangeValue :*/ num; 
		// 检测浏览器
		var o = document.createElement('input');
	    o.type = 'range';
	    if ( o.type === 'text' ) alert('不好意思，你的浏览器还不够酷，试试最新的浏览器吧。');
	    range.value = cachedRangeValue;
	    result.innerHTML = cachedRangeValue;
	    wid.style.width = range.value/maxnum*100 + "%";
	    range.addEventListener("mouseup", function() {
	    	result.innerHTML = range.value;
	        wid.style.width = range.value/maxnum*100 + "%";
	        //alert("你选择的值是：" + range.value + ". 我现在正在用本地存储保存此值。在现代浏览器上刷新并检测。");
	        //localStorage ? (localStorage.rangeValue = range.value) : alert("数据保存到了数据库或是其他什么地方。");
	        //result.innerHTML = range.value;
	    }, false);

	    // 滑动时显示选择的值
	    range.addEventListener("change", function() {
	        result.innerHTML = range.value;
	        wid.style.width = range.value/maxnum*100 + "%";
	    }, false);
	}
    
    FnRange("OneMemory","OneMemoryText","OneMemoryWid",256,2048);
    FnRange("NodeNum","NodeText","NodeWid",1,10);
    FnRange("TimeLong","TimeLongText","TimeLongWid",9,12);

    // 滑动框 结束

    // 输入框输入样式

    // 01 输入用户名
    $('#create_name').blur(function(){
        var appName = $(this).val();
        //var checkReg = /^[a-z][a-z0-9-]*[a-z0-9]$/;
        //var result = true;
        if(appName == ""){
            $('#create_name_notice').slideDown();
            return;
        }else{
            $('#create_name_notice').slideUp();
        }
    });
    // 01 end 

    //03 公开项目
    $('#service_code_url').blur(function(){
        var appurl= $(this).val();
        if(appurl == ""){
            $('#service_code_url_tips').slideDown();
            return;
        }else{
            $('#service_code_url_tips').slideUp();
        }
    });
    //03 公开项目
    //04 自建Git
    $('#my_git_url').blur(function(){
        var myurl= $(this).val();
        if(myurl == ""){
            $('#my_git_url_tips').slideDown();
            return;
        }else{
            $('#my_git_url_tips').slideUp();
        }
    });
    //04 自建Git
    // github 

    var way_value = $(".fn-way").attr("data-action");
    if(way_value == "gitlab_exit"){
        console.log(1);
        $('#service_code_from').val("gitlab_exit");
        var tenantName= $('#currentTeantName').val();
        _url = "/ajax/"+tenantName+"/code_repos?action=gitlab";
        loadObj(_url);
    }else if(way_value == "github"){
        console.log(1);
        $('#service_code_from').val("github");
        var tenantName= $('#currentTeantName').val();
        _url = "/ajax/"+tenantName+"/code_repos?action=github";
        loadRepos(_url);
    }else{
        return;
    }

    //项目 地址
    function loadObj(_url){
        var listWrap;
        var service_code_from = $('#service_code_from').val();
        
        $.ajax({
            type: "GET",
            url: _url,
            cache: false,
            success: function(msg){
                var dataObj = msg;
                if(dataObj["status"] == "unauthorized"){
                    window.open(dataObj["url"], "_parent");
                    $("#code_github_list").hide();
                    $("#gh_branch").hide();
                }else if(dataObj["status"]=="success"){
                    var dataList=dataObj["data"];
                    var htmlmsg="";
                    for(var i=0;i<dataList.length;i++){
                        data = dataList[i];
                        htmlmsg +='<option idx="'+ i +'" data="'+data["code_id"]+ '" id="repos_'+data["code_id"] + '" name="repos_'+data["code_id"]+'" value='+data["code_repos"] +'">';
                        htmlmsg += data["code_user"]+'/'+data["code_project_name"] + '</option>';
                    }
                    if(service_code_from == "github"){
                        listWrap = $("#code_github_list");
                        if(htmlmsg){
                            $(listWrap).html(htmlmsg);
                            $("#waiting").hide();
                        }
                    }else{
                        listWrap = $("#code_gr_list");
                        if(htmlmsg){
                            htmlmsg += '<option value="newobj">新建项目</option>';
                            $(listWrap).html(htmlmsg);
                        }else{
                           $(listWrap).html('<option value="newobj">新建项目</option>'); 
                        }
                    }                    

                    $(listWrap).change(function(){
                         var sedoption = $(listWrap).find('option:selectd');
                         console.log(sedoption);
                         var service_code_id=$(sedoption).attr("data");
                         var clone_url = $('#repos_'+service_code_id).val();
                         Fnbranch(service_code_from,service_code_id,clone_url);  
                    });
                }else{
                    $('#waiting').html("无可用仓库");
                }
            },
            error: function(){
                console.log("系统异常");
            }
        });
    }

    // 项目分支 
    function  Fnbranch(code_from,code_id,clone_url){
        var action="";
        var user ="";
        var repos ="";
        var branch_box;
        if(code_from=="gitlab_exit"){
            action="gitlab";
            branch_box = $("#gr_branch");
        }else if(code_from=="github"){
            action="github";
            user =  clone_url.split("/")[3];
            repos = clone_url.split("/")[4].split(".")[0];
            branch_box = $("#gh_branch");
        }
        var tenantName= $('#currentTeantName').val();
        //
        if(action != ""){
            ///
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
                        if(typeof BranchLocalData[codeId] == 'undefined'){
                            BranchLocalData[codeId] = dataList;
                        }
                        for(var i=0;i<dataList.length;i++){
                            data = dataList[i];
                            htmlmsg +='<option value="'+data["version"]+'">'+data["version"]+'</option>';
                        }
                        var htmlno = '<option value="0">暂无可选分支</option>';
                        if(htmlmsg){
                            $(branch_box).html(htmlmsg);
                        }else{
                            $(branch_box).html(htmlno);
                        }  
                    }else {
                       swal("操作失败");
                    }
                },
                error : function() {
                    console.log("系统异常");
                }
            });
            ///
        }
        //
    }
    //
});










