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
        _url = "/ajax/" + tenantName + "/batch-action";
        ///
        $.ajax({
            type : "POST",
            url : _url,
            data:{
                "action":"deploy",
                service_ids : JSON.stringify(app_id)
            },
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {
                if(msg.ok){
                    swal(msg.info)
                }else(
                    swal(msg.info)
                )
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
            url : "/ajax/" + tenantName + "/batch-action",
            data : {
                "action":"stop",
                "service_ids":JSON.stringify(Arraycheck)
            },
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {
                var dataObj = msg

                if(msg.ok){
                    swal(msg.info)
                }
                else{
                    swal(msg.info)
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
            url : "/ajax/" + tenantName + "/batch-action",
            data : {
                "action":"start",
                "service_ids":JSON.stringify(Arraycheck)
            },
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {

                if(msg.ok){
                    swal(msg.info)
                }
                else{
                    swal(msg.info)
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
        var sedVal = $("#group-tit").attr("data-group"); // 取应用ID
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
                                url : "/ajax/" + tenant_Name  + "/group/add",
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
                                url : "/ajax/" + tenant_Name  + "/group/update",
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
                        url : "/ajax/" + tenant_Name  + "/group/delete",
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
                            window.location.href="/apps/"+tenant_Name+"/myservice/?gid=-1";
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
            url : "/ajax/" + tenant_Name + "/group/change-group",
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
                window.location.reload();
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

    //切换
    $("#imgbtn").click(function(){
        $("#tabBox").hide();
        $("#imgBox").show()
        $(this).addClass("sed");
        $("#tabbtn").removeClass("sed");
    });
    $("#tabbtn").click(function(){
        $("#tabBox").show();
        $("#imgBox").hide()
        $(this).addClass("sed");
        $("#imgbtn").removeClass("sed");
    });
    
    //////图
    var json_svg = {
        "service_dep_cname1" :["service_dep_cname2"],
        "service_dep_cname2" :["service_dep_cname3"],
        "service_dep_cname3" :[],
        "service_dep_cname4" :[],
        "service_dep_cname5" :["service_dep_cname8","service_dep_cname3"],
        "service_dep_cname6" :["service_dep_cname9"],
        "service_dep_cname7" :["service_dep_cname3"], 
        "service_dep_cname8" :["service_dep_cname4"],
        "service_dep_cname9" :["service_dep_cname3"],
    }
    var json_data = {
        "service_cname1" : {"service_id" : "serone","service_alias" : "aliasone"},
        "service_cname2" : {"service_id" : "sertwo","service_alias" : "aliastwo"},
        "service_cname3" : {"service_id" : "serthree","service_alias" : "aliasthree"},
        "service_cname4" : {"service_id" : "serfour","service_alias" : "aliasfour"},
        "service_cname5" : {"service_id" : "serfive","service_alias" : "aliasfive"},
        "service_cname6" : {"service_id" : "sersix","service_alias" : "aliassix"},
        "service_cname7" : {"service_id" : "serseven","service_alias" : "aliasseven"},
        "service_cname8" : {"service_id" : "sereight","service_alias" : "aliaseight"},
        "service_cname9" : {"service_id" : "sernine","service_alias" : "aliasnine"},
       
    }
    var svgNS = 'http://www.w3.org/2000/svg';
    var arrDepApp =[];  //全部依赖别的
    var arrApp =[];  //组合数组  右边所有依赖合并
    var AppBot =[];
    var AppTop = [];
    var AppMid = []; // 中部，即依赖别的
    for(var key in json_svg){
        if(json_svg[key].length == 0){
            AppBot.push(key);
        }else{
            arrDepApp.push(key);
            arrApp = arrApp.concat(json_svg[key]);
        }
    }
    //console.log(AppBot);
    //console.log(arrDepApp);
    //console.log(arrApp);

    var AppMB = []; 
    //数组去重
    for(i=0;i<arrApp.length;i++){
        if(AppMB.indexOf(arrApp[i])<0){
            AppMB.push(arrApp[i])
        }
    }

    //console.log(AppMB);
    var strMB =  AppMB.join("&");
    strMB = strMB + "&";
    //console.log(strMB);
    
    var strTM = arrDepApp.join("&");
    strTM = strTM  + "&";

    for(var i=0; i<AppBot.length;i++){
        var str = AppBot[i] + "&";
        var rex = new RegExp(str, 'g');
        strMB = strMB.replace(rex, "");       
    }
    //console.log(strMB);
    var strM = strMB.substring(0,(strMB.length-1));
    //console.log(strM);
    
    AppMid = strM.split("&");
    

    for(var i=0; i<AppMid.length;i++){
        var str = AppMid[i] + "&";
        var rex = new RegExp(str, 'g');
        strTM  = strTM.replace(rex, "");       
    }
    var strT = strTM.substring(0,(strTM.length-1));
    AppTop =  strT.split("&");
    //console.log(AppTop);
    //console.log(AppMid);

    // svg 绘图
    var svgNS = 'http://www.w3.org/2000/svg';
    var oSvgDiv = document.getElementById("svg-box");
    var axisXY  = {};
    function createTag(tag,objAttr){
        var oTag = document.createElementNS(svgNS , tag);
        for(var attr in objAttr){
            oTag.setAttribute(attr,objAttr[attr]);
        }
        return oTag;
    }
    var oSvg = createTag('svg',{'xmlns':svgNS,'width':'100%','height':'600'});
    
    var divWidth = oSvgDiv.offsetWidth;
    //console.log(divWidth);
    
    for(var i=0; i<AppTop.length;i++){
        var top_width = divWidth/AppTop.length;
        var top_w = top_width - 20;
        //FnSvgIcon(top_width,50,i,AppTop[i],top_w,""); 
        axisXY[AppTop[i]] = [(top_width*i+top_width/2),80];
    }
    for(var i=0; i<AppMid.length;i++){
        var mid_width = divWidth/AppMid.length;
        var mid_w = mid_width - 20;
        //FnSvgIcon(mid_width,250,i,AppMid[i],mid_w,"");
        axisXY[AppMid[i]] = [(mid_width*i+mid_width/2),280];
    }
    for(var i=0; i<AppBot.length;i++){
        var bot_width = divWidth/AppBot.length;
        var bot_w = bot_width - 20;
        //FnSvgIcon(bot_width,450,i,AppBot[i],bot_w,"");
        axisXY[AppBot[i]] = [(bot_width*i+bot_width/2),480];
    }
    //console.log(axisXY);
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
                var oLine = createTag('line',{'x1':startX,'y1':startY,'x2':endX,'y2':endY,'stroke':'#ccc'});
                //console.log(oLine);
                oSvg.appendChild(oLine);
            }
        }
    }
    //
    function FnSvgIcon(wid,hei,num,txt,txtWid,url){
        var oImg = createTag('image',{'width':'60px','height':'60px','x':(wid*num+wid/2-30),'y':hei,'href':'/www/static/www/images/app1.png'});
        var oText = createTag('text',{'x':(wid*num+wid/2),'y':hei+70,'font-size':'12','text-anchor':'middle','fill':'#999','lengthAdjust':'spacing'});
        oText.innerHTML = txt;
        var oA= createTag('a',{'href':url});
        var oG = createTag('g',{'style':'cursor:pointer'});
        oA.appendChild(oText);
        oA.appendChild(oImg);
        oG.appendChild(oA);
        oSvg.appendChild(oG);
    }
   for(var i=0; i<AppTop.length;i++){
        var top_width = divWidth/AppTop.length;
        var top_w = top_width - 20;
        FnSvgIcon(top_width,50,i,AppTop[i],top_w,"");  
    }
    for(var i=0; i<AppMid.length;i++){
        var mid_width = divWidth/AppMid.length;
        var mid_w = mid_width - 20;
        FnSvgIcon(mid_width,250,i,AppMid[i],mid_w,"");  
    }
    for(var i=0; i<AppBot.length;i++){
        var bot_width = divWidth/AppBot.length;
        var bot_w = bot_width - 20;
        FnSvgIcon(bot_width,450,i,AppBot[i],bot_w,""); 
    }
    oSvgDiv.appendChild(oSvg);
    //////图
});










