$(function(){
    // // //上传compose文件 start
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

    $("#nextcomposestep").click(function(){
        var formData = new FormData($("#myForm")[0]);
		var tenantName = $("#tenantNameValue").val();
		var appname = $("#create_name").val();
		if(appName == ""){
            $('#create_name_notice').slideDown();
            return;
        }else{
            $('#create_name_notice').slideUp();
        }
		upload_url = "/apps/"+tenantName+"/compose-create/"
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
						window.location.href = "/apps/"+tenantName+"/compose-params?id="+responseStr.compose_file_id

					}else{
						swal("文件上传异常")
					}
                },  
                error : function(responseStr) {  
                   
                }  
            });  
    });
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
    // // //上传compose文件 end

    // // // 第二步 基本设置 start
    // 图 start 
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
    //图 end 
    
    /////切换 start
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
    // 切换 end


    $(".fn-circle").each(function(){
        var this_id= $(this).attr("id");
        $("#"+ this_id +"_MoneyBefore").change(function(){
            var onoff = $("#"+ this_id +"_MoneyBefore").prop("checked");
            if(onoff == true){
                // $(".fn-memory-node").show();
                $("#"+ this_id + "_aft-memory-box").hide();
            }else{
                //$(".fn-memory-node").hide();
                $("#"+ this_id + "_aft-memory-box").show();
            }
            // FnPrice(this_id);
        });
        $("#"+ this_id +"_MoneyAfter").change(function(){
            
            var onoff = $("#"+ this_id +"_MoneyAfter").prop("checked");
            if(onoff == false){
                //$(".fn-memory-node").show();
                $("#"+ this_id +"_aft-memory-box").hide();
            }else{
                //$(".fn-memory-node").hide();
                $("#"+ this_id +"_aft-memory-box").show();
            }
            //FnPrice(this_id);
        });
        $("#"+ this_id +"DiskBefore").change(function(){
            var onoff = $("#"+ this_id +"_DiskBefore").prop("checked");
            if(onoff == true){
                $("#"+ this_id + "_disk_box").show();
                $("#"+ this_id +"_aft-disk-box").hide();
            }else{
                $("#"+ this_id + "_disk_box").hide();
                $("#"+ this_id +"_aft-disk-box").show();
            }
            //FnPrice(this_id);
        });
        $("#"+ this_id +"_DiskAfter").change(function(){
            var onoff = $("#"+ this_id +"_After").prop("checked");
            if(onoff == false){
                $("#"+this_id +"_disk_box").show();
                $("#"+ this_id +"_aft-disk-box").hide();
            }else{
                $("#"+this_id +"_disk_box").hide();
                $("#"+ this_id +"_aft-disk-box").show();
            }
           // FnPrice(this_id);
        });
     });
    
    // // // 第二步 基本设置 end
});
