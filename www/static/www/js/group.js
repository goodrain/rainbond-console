$(function(){
    // var ser_alias = $("#app-group").attr("data-serviceAlias");
    var groupID = $("#group-tit").attr("data-group");
    var tenant_Name = $("#app-group").attr("data-tenantName");
	// 复选框开始
	var chackboxnums = $(".fn-SelectItem input:checked").length;
    
    if(chackboxnums == 0){
        $("#batchStart").prop("disabled",true);
        $("#batchEnd").prop("disabled",true);
        $("#newStart").prop("disabled",true);
        //$("#groupShare").prop("disabled",true);
    }else{
        $("#batchStart").removeAttr("disabled",true);
        $("#batchEnd").removeAttr("disabled",true);
        $("#newStart").removeAttr("disabled",true);
        //$("#groupShare").removeAttr("disabled",true);
    }
	$(".fn-SelectItem input").click(function(){
    	chackboxnums = $(".fn-SelectItem input:checked").length;
    	$("#nums-app p").children("span").html(chackboxnums);
        if(chackboxnums < $(".fn-SelectItem input").length){
            $(".fn-SelectAll input").removeAttr("checked");
        }else{
            $(".fn-SelectAll input").prop("checked",true);
        }
        if(chackboxnums == 0){
            $("#batchStart").prop("disabled",true);
            $("#batchEnd").prop("disabled",true);
            $("#newStart").prop("disabled",true);
            //$("#groupShare").prop("disabled",true);
        }else{
            $("#batchStart").removeAttr("disabled",true);
            $("#batchEnd").removeAttr("disabled",true);
            $("#newStart").removeAttr("disabled",true);
           // $("#groupShare").removeAttr("disabled",true);
        }
    });
    $(".fn-SelectAll input").on("click",function(){
    	if($(".fn-SelectAll input:checked").length == 1){
			$(".fn-SelectItem input").prop("checked",true);
			chackboxnums = $(".fn-SelectItem input:checked").length;
    		$("#nums-app p").children("span").html(chackboxnums);
            $("#batchStart").removeAttr("disabled",true);
            $("#batchEnd").removeAttr("disabled",true);
            $("#newStart").removeAttr("disabled",true);
            //$("#groupShare").removeAttr("disabled",true);
		}else{
			$(".fn-SelectItem input").removeAttr("checked");
    		$("#nums-app p").children("span").html("0");
            $("#batchStart").prop("disabled",true);
            $("#batchEnd").prop("disabled",true);
            $("#newStart").prop("disabled",true);
            //$("#groupShare").prop("disabled",true);
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

    //批量分享
    $("#groupShare").click(function(){
        // var Arraycheck = [];
        // $(".fn-SelectItem input:checked").each(function(){
        //     Arraycheck.push($(this).val());
        // });
        // Arraycheck.sort();
        // var data = Arraycheck.join(',');
        // console.log(data);

        var group_id = $("#group_id_input").val();
        $.ajax({
            type : "POST",
            url : "/apps/" + tenantName + "/" + group_id + "/preview/",
            data : {
                // "service_ids":JSON.stringify(Arraycheck)
                "group_id":group_id
            },
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {
                var json_data = eval(msg);
                if (json_data.code == 200 || json_data.code == 201) {
                    location.href = json_data.next_url;
                } else {
                    swal(json_data.msg);
                }
            },
            error : function() {
                swal("系统异常");
            }
        });
    });
    //批量分享


    
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
        $(".group-set-box").slideUp();
        $("#setbtn").removeClass("sed");
        onoff = true;
        FnLayer("请输入新组名：",true,"",false,"全部应用不能改名！");
    });
    // 删除当前组
    // 删除当前组
    $("#reomve-groupname").click(function(){
        $(".group-set-box").slideUp();
        $("#setbtn").removeClass("sed");
        onoff = true;
        FnLayer("",false,"您确定要删除当前组么？",false,"全部应用不能删除！");
    });
    // 新增组
    $("#add-groupname").click(function(){
        $(".group-set-box").slideUp();
        $("#setbtn").removeClass("sed");
        onoff = true;
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
            var oCloseBtn = '<a href="javascript:;" class="closebtn fn-close"><i class="fa fa-times"></i></a>';
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
                console.log(XMLHttpRequest.status);
                if (XMLHttpRequest.status == '403'){
                    swal("您的权限不够");
                }else {
                    swal("系统异常,请重试");
                }
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
    if(groupID == -1){
        $("#tabBox").show();
        $("#imgBox").hide();
    }else{
        ///
        $.ajax({
            type : "get",
            url : "/ajax/" + tenant_Name + "/topological/" + groupID,
            //data : {},
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(data) {
               
                var oData = eval(data);
                //console.log(data);
                //console.log(oData.json_svg);
                //console.log(oData.json_data);
               
                if(oData.status == 200){
                    //console.log(oData.json_svg);
                    //console.log(oData.json_data);
                   // FnSvg(oData.json_svg,oData.json_data);
                }else{
                    // swal(oData.msg);
                }
            },
            error : function() {
                swal("系统异常,请重试");
            }
        });
        ///
    }
    
    
function FnSvg(json_svg,json_data){
    //console.log(json_svg);
    //console.log(json_data);
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
   var val_main = val_svg;
   var val_main_single = [];
   //console.log(val_main);
   for(i=0;i<val_main.length;i++){
        if(val_main_single.indexOf(val_main[i])<0){
            val_main_single.push(val_main[i])
        }
    }
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
    
    //console.log(my_svg);
    //console.log(AppTop);
    //console.log(AppMid);
    console.log(val_main_single);
    //console.log(AppBot);
    console.log(AppBot_B);
    var main_bot = [];
    for(var m=0; m<val_main_single.length; m++){
        for(var n=0; n<AppBot_B.length;n++){    
            if(val_main_single[m] == AppBot_B[n]){
                main_bot.push(val_main_single[m]);
            }
        }
    }
    console.log("/////////");
    console.log(main_bot);
    for(var k=0;k<main_bot.length;k++){
        AppBot_B.remove(main_bot[k]);
    }
    console.log(AppBot_B);
    //绘图
    var svgNS = 'http://www.w3.org/2000/svg';
    var svgLink="http://www.w3.org/1999/xlink";
    var oSvgDiv = document.getElementById("svg-box");
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
    var oSvg = createTag('svg',{'xmlns':svgNS,'xmlns:xlink':svgLink,'width':'100%','height':'800'});
    var oDefs = createTag('defs',{});
    var oMarker = createTag('marker',{'id':'markerArrow','markerWidth':'13','markerHeight':'13','refX':'35','refY':'6','orient':'auto'});
    var oPath = createTag('path',{'d':'M2,2 L2,11 L10,6 L2,2 z','fill':'#ccc'});
    oSvg.appendChild(oDefs);
    oDefs.appendChild(oMarker);
    oMarker.appendChild(oPath);


    // 添加图片
    function FnSvgIcon(wid,hei,num,txt,txtWid){
        if(json_data[txt]){
            var url = "/apps/" + tenant_Name + "/" + json_data[txt]["service_alias"] + "/detail/";
        }else{
            url = "";
        }
        var oImg = createTag('image',{'width':'60px','height':'60px','x':(wid*num+wid/2-30),'y':hei});
        var oText = createTag('text',{'x':(wid*num+wid/2),'y':hei+70,'font-size':'12','text-anchor':'middle','fill':'#999','lengthAdjust':'spacing'});
        oText.innerHTML = txt;
        oImg.setAttributeNS(svgLink,'xlink:href','/static/www/images/app1.png');
        var oA= createTag('a',{'href':url});
        oA.setAttributeNS(svgLink,'xlink:href',url);
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
            axisXY[AppMid[i]] = [(mid_width*i+mid_width/2),150];
        }
    }
    if(main_bot.length != 0){
        for(var i=0; i<main_bot.length;i++){
            var bot_width = divWidth/main_bot.length;
            var bot_w = bot_width - 20;
            //FnSvgIcon(bot_width,320,i,AppBot_B[i],bot_w);
            axisXY[main_bot[i]] = [(bot_width*i+bot_width/2),250];
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
            FnSvgIcon(mid_width,130,i,AppMid[i],mid_w);
            //axisXY[AppMid[i]] = [(mid_width*i+mid_width/2),200];
        }
    }
    if(main_bot.length != 0){
        for(var i=0; i<main_bot.length;i++){
            var bot_width = divWidth/main_bot.length;
            var bot_w = bot_width - 20;
            FnSvgIcon(bot_width,230,i,main_bot[i],bot_w);
            //axisXY[AppBot_B[i]] = [(bot_width*i+bot_width/2),350];
        }
    }
    if(AppBot_B.length != 0){
        for(var i=0; i<AppBot_B.length;i++){
            var bot_width = divWidth/8;
            var bot_w = bot_width - 20;
            var indexnum = i%8;
            var oldh = 0;
            if(AppTop.length == 0 && main_bot.length == 0){
                oldh = 30 
            }else{
                oldh = 330
            }

            var indexh = parseInt(i/8)*100+oldh;
            FnSvgIcon(bot_width,indexh,indexnum,AppBot_B[i],bot_w);
        }
    }
    //
    

    oSvgDiv.appendChild(oSvg);
}
    //////图

    //ww - 2017- 1-10  -- 修改
    var onoff = true;
    $("#setbtn").click(function(){
        if(onoff){
            $(".group-set-box").slideDown();
            $("#setbtn").addClass("sed");
            onoff = false;
        }else{
            $(".group-set-box").slideUp();
            $("#setbtn").removeClass("sed");
            onoff = true;
        }
    });
    //ww - 2017- 1-10  -- 修改
});










