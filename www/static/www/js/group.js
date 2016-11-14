$(function(){
    // var ser_alias = $("#app-group").attr("data-serviceAlias");
    var tenant_Name = $("#app-group").attr("data-tenantName");
	// 复选框开始
	var chackboxnums;
	$(".fn-SelectItem input").click(function(){
    	chackboxnums = $(".fn-SelectItem input:checked").length;
    	$("#nums-app p").children("span").html(chackboxnums);
        if(chackboxnums < $(".fn-SelectItem input").length){
            $(".fn-SelectAll input").removeAttr("checked");
        }else{
            $(".fn-SelectAll input").prop("checked",true);
        }
    });
    $(".fn-SelectAll input").on("click",function(){
    	if($(".fn-SelectAll input:checked").length == 1){
			$(".fn-SelectItem input").prop("checked",true);
			chackboxnums = $(".fn-SelectItem input:checked").length;
    		$("#nums-app p").children("span").html(chackboxnums);
		}else{
			$(".fn-SelectItem input").removeAttr("checked");
    		$("#nums-app p").children("span").html("0");
		}
    });
    // 复选框结束
    
    //批量重新部署
    $("#newStart").click(function(){
        var Arraycheck = [];
        $(".fn-SelectItem input:checked").each(function(){
            Arraycheck.push($(this).val());
        })
        var app_id = Arraycheck;
        console.log(app_id);
        $("#newStart").attr('disabled', "true");
        _url = "/ajax/" + tenant_Name + '/' + ser_alias + "/app-deploy/";
        ///
        $.ajax({
            type : "POST",
            url : _url,
            data:{
                ser_Id : app_id
            },
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {
                var dataObj = msg;
                if (dataObj["status"] == "success") {
                    swal("操作成功")
                } else if (dataObj["status"] == "owed") {
                    swal("余额不足请及时充值")
                } else if (dataObj["status"] == "expired") {
                    swal("试用已到期")
                } else if (dataObj["status"] == "language") {
                    swal("应用语言监测未通过")
                    forurl = "/apps/" + tenantName + "/" + serviceAlias
                            + "/detail/"
                    window.open(forurl, target = "_parent")
                } else if (dataObj["status"] == "often") {
                    swal("部署正在进行中，请稍后")
                } else if (dataObj["status"] == "over_memory") {
                    swal("资源已达上限，不能升级")
                } else if (dataObj["status"] == "over_money") {
                    swal("余额不足，不能升级")
                } else {
                    swal("操作失败")
                    $("#onekey_deploy").removeAttr("disabled")
                }
                $("#newStart").removeAttr("disabled")
            },
            error : function() {
                $("#newStart").removeAttr("disabled")
                swal("系统异常");
            }
        })
        ///
    });
    //批量重新部署

    //批量停止
    $("#batchEnd").click(function(){
        var Arraycheck = [];
        $(".fn-SelectItem input:checked").each(function(){
            Arraycheck.push($(this).val());
        })
        var app_id = Arraycheck;
        $("#batchEnd").attr('disabled', "true")
        ///
        $.ajax({
            type : "POST",
            url : "/ajax/" + tenantName + "/" + service_alias + "/manage",
            data : {

            },
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {
                var dataObj = msg
                if (dataObj["status"] == "success") {
                    swal("操作成功")
                } else if (dataObj["status"] == "often") {
                    swal("操作正在进行中，请稍后")
                } else if (dataObj["status"] == "owed") {
                    swal("余额不足请及时充值")
                } else if (dataObj["status"] == "expired") {
                    swal("试用已到期")
                } else if (dataObj["status"] == "over_memory") {
                    swal("资源已达上限，不能升级")
                } else if (dataObj["status"] == "over_money") {
                    swal("余额不足，不能升级")
                } else {
                    swal("操作失败")
                }
                $("#batchEnd").removeAttr("disabled");
            },
            error : function() {
                swal("系统异常");
                $("#batchEnd").removeAttr("disabled");
            }
        })
        ///
    });
    //批量停止

    //批量启动
    $("#batchStart").click(function(){
        var Arraycheck = [];
        $(".fn-SelectItem input:checked").each(function(){
            Arraycheck.push($(this).val());
        })
        var app_id = Arraycheck;
        $("#batchStart").attr('disabled', "true")
        ///
        $.ajax({
            type : "POST",
            url : "/ajax/" + tenantName + "/" + service_alias + "/manage",
            data : {

            },
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {
                var dataObj = msg
                if (dataObj["status"] == "success") {
                    swal("操作成功")
                } else if (dataObj["status"] == "often") {
                    swal("操作正在进行中，请稍后")
                } else if (dataObj["status"] == "owed") {
                    swal("余额不足请及时充值")
                } else if (dataObj["status"] == "expired") {
                    swal("试用已到期")
                } else if (dataObj["status"] == "over_memory") {
                    swal("资源已达上限，不能升级")
                } else if (dataObj["status"] == "over_money") {
                    swal("余额不足，不能升级")
                } else {
                    swal("操作失败")
                }
                $("#batchStart").removeAttr("disabled");
            },
            error : function() {
                swal("系统异常");
                $("#batchStart").removeAttr("disabled");
            }
        })
        ///
    });
    //批量启动
     


    
    ////////////////
    //选择分组
    $("#app-group").change(function(){
        var main_sed_val = $("#app-group option").eq(0).val();
        var sed_val = $("#app-group option:selected").val();
        $("#tab-box tr").show();
        if(main_sed_val == sed_val){
            return false;
        }else{
            $("#tab-box tr").each(function(){
                if($(this).attr("data-group") != sed_val){
                    $(this).hide();
                }
            })
        }
    });
    //选择分组

    //修改组名
    $("#revise-groupname").click(function(){
        FnLayer("请输入新组名：",true,"",false,"全部应用不能改名！");
    });
    // 删除当前组
    // 删除当前组
    $("#reomve-groupname").click(function(){
        FnLayer("",false,"您确定要删除当前组么？",false,"全部应用不能删除！");
    });
    // 新增组
    $("#add-groupname").click(function(){
        FnLayer("请输入新增组名",true,"",true,"");
    });
    // 新增组
    
    //弹出层
    function FnLayer(textTit,onoff,text,newonoff,tipsText){
        var sedVal = $("#app-group option:selected").val(); // 取应用ID
        if(sedVal == "0" && !newonoff){
            swal(tipsText);
            return false;
        }else{
            ///
            var oDiv = '<div class="layerbg"><div class="layermain"></div></div>';
            var oCloseBtn = '<a href="javascript:;" class="closebtn fn-close">X</a>';
            var oTit = '<p class="layer-tit">'+ textTit +'</p>';
            var oInput ='<p class="input-css"><input name="" type="text" value="" /></p>';
            var oText ='<p class="tipstext">'+ text +'</p>';
            var oLink = '<p class="layerlink"><a href="javascript:;" class="fn-sure">确定</a><a href="javascript:;" class="fn-close">取消</a></p>';
            $("body").append(oDiv);
            $("div.layermain").append(oCloseBtn,oTit);
            if(onoff){
               $("div.layermain").append(oInput);
            }else{
                $("div.layermain").append(oText);
            }
            $("div.layermain").append(oLink);
            $(".fn-close").click(function(){
                $("div.layerbg").remove();
            });
            $(".fn-sure").click(function(){
                if(onoff){
                    if(inputText == ""){
                        swal("您还没有输入组名！")
                        return false;
                    }else{
                        var inputText = $(".input-css input").val();
                        if(newonoff){
                            ///
                            $.ajax({
                                type : "post",
                                url : "/apps/" + tenant_Name  + "/group/add",
                                data : {
                                    group_name : inputText
                                },
                                cache : false,
                                beforeSend : function(xhr, settings) {
                                    var csrftoken = $.cookie('csrftoken');
                                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                                },
                                success : function(msg) {
                                    if (msg.ok){
                                        window.location.reload();
                                    }else{
                                        swal(msg.info)
                                    }
                                },
                                error : function() {
                                    swal("系统异常,请重试");
                                }
                            });
                            ///
                        }else{
                            ///
                            $.ajax({
                                type : "post",
                                url : "/apps/" + tenant_Name  + "/group/update",
                                data : {
                                    new_group_name : inputText,
                                    group_id : sedVal
                                },
                                cache : false,
                                beforeSend : function(xhr, settings) {
                                    var csrftoken = $.cookie('csrftoken');
                                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                                },
                                success : function(msg) {
                                    window.location.reload();
                                },
                                error : function() {
                                    swal("系统异常,请重试");
                                }
                            });
                            ///
                        }
                    }
                }else{
                    ///
                    $.ajax({
                        type : "post",
                        url : "/apps/" + tenant_Name  + "/group/delete",
                        data : {
                            group_id : sedVal,
                        },
                        cache : false,
                        beforeSend : function(xhr, settings) {
                            var csrftoken = $.cookie('csrftoken');
                            xhr.setRequestHeader("X-CSRFToken", csrftoken);
                        },
                        success : function(msg) {
                            var dataObj = msg;
                            window.location.reload();
                        },
                        error : function() {
                            swal("系统异常,请重试");
                        }
                    });
                    ///
                }
            });
            ///
        }        
    }
    //  弹出层
    /////////////////////

    

    // 搜索当前页面应用
    jQuery.expr[':'].Contains = function(a,i,m){
        return (a.textContent || a.innerText || "").toUpperCase().indexOf(m[3].toUpperCase())>=0;
    };
    function filterList(list) { 
    input = $("input#search");
    $(input)
        .change( function () {
            var filter = $(this).val();
            if(filter) {
              $matches = $(list).find('a:Contains(' + filter + ')').parent().parent().parent();
              $('tr', list).not($matches).hide();
              $matches.slideDown();
            } else {
              $(list).find("tr").show();
            }
            return false;
        })
        .keyup( function () {
            $(this).change();
        });
    }
    filterList($("#tab-box"));
    // 搜索当前页面应用

    //  选择分组
    $(".fn-name").click(function(){
        $(this).next("div.fn-show-select").show();
    });
    $(".fn-groupname-sure").click(function(){
        var oThis = $(this);
        var new_group_id = $(this).prev().find("option:selected").val();
        var new_group_name = $(this).prev().find("option:selected").html();
        var ser_id = $(this).attr("data-id");
        /////
        $.ajax({
            type : "post",
            url : "/apps/" + tenant_Name + "/group/change-group",
            data : {
                "group_id" : new_group_id,
                "service_id" : ser_id
            },
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {
                var dataObj = msg;
                oThis.parent().prev().html(new_group_name);
                oThis.parent("div.fn-show-select ").hide();
                //window.location.reload();
            },
            error : function() {
                swal("系统异常,请重试");
            }
        });
        /////

    });
    $(".fn-groupname-close").click(function(){
        $(this).parent("div.fn-show-select ").hide();
    });
    //  选择分组
 
});










