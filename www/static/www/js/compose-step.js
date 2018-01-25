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
    /*
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

    //oSvgDiv.appendChild(oSvg);
    /// svg
    //图 end 
    */
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

   // 01 输入用户名
   /*
     $(".fn-circle").each(function(){
        var this_id= $(this).attr("id");
        var nameid = "#" +  this_id + "_create_app_name" ;
        $(nameid).blur(function(){
            var appName = $(this).val();
            //var checkReg = /^[a-z][a-z0-9-]*[a-z0-9]$/;
            //var result = true;
            if(appName == ""){
                $(this).parent().next("p.fm-tips").slideDown();
                return;
            }else{
                $(this).parent().next("p.fm-tips").slideUp();
            }
        });
    });
    */
    // 01 end 

    //弹出层
    /*
    function FnLayer(textTit,myid){
        var oDiv = '<div class="layerbg"><div class="layermain"></div></div>';
        var oCloseBtn = '<a href="javascript:;" class="closebtn fn-close"><i class="fa fa-times"></i></a>';
        var oTit = '<p class="layer-tit">'+ textTit +'</p>';
        var oInput ='<p class="input-css"><input name="" type="text" value="" /></p>';
        var oLink = '<p class="layerlink"><a href="javascript:;" class="fn-sure">确定</a><a href="javascript:;" class="fn-close">取消</a></p>';
        $("body").append(oDiv);
        $("div.layermain").append(oCloseBtn,oTit);
        $("div.layermain").append(oInput);
        $("div.layermain").append(oLink);
        $(".fn-close").click(function(){
             $("div.layerbg").remove();
             $(".input-css input").prop("value","");
             $("#group-name").find("option[value='-1']").prop("selected",true);
        });
        $(".fn-sure").click(function(){
            if(inputText == ""){
                swal("您还没有输入组名！")
                return false;
            }else{
                var inputText = $(".input-css input").val();
                var tenant_name = $("#currentTeantName").val();
                ///ajax start

                $.ajax({
                    type : "post",
                    url : "/ajax/" + tenant_name  + "/group/add",
                    data : {
                        group_name : inputText
                    },
                    cache : false,
                    beforeSend : function(xhr, settings) {
                        var csrftoken = $.cookie('csrftoken');
                        xhr.setRequestHeader("X-CSRFToken", csrftoken);
                    },
                    success : function(msg) {
                        if(msg.ok){
                            var  group_id = msg.group_id;
                            var  group_name = msg.group_name;
                            var  Option = "<option value=" +  group_id + ">" + group_name + "</option>";
                            $("div.layerbg").remove();
                            $(".input-css input").prop("value","");
                            $(myid).find("option").eq(0).after(Option);
                            $(myid).find("option").each(function(){
                                var oVal = $(this).prop("value");
                                if(oVal == group_id){
                                    $(this).prop("selected",true);
                                }
                            });
                        }else{
                            swal(msg.info);
                        }
                    },
                    error : function() {
                        swal("系统异常,请重试");
                    }
                });
                
                ///ajax end
            }
              
        });   
    }
    //  弹出层
    $(".fn-circle").each(function(){
        var this_id= $(this).attr("id");
        var group_name = "#" + this_id + "_group-name";
        $(group_name).change(function(){
            var gName = $(group_name).find("option:selected").val();
            if (gName == -2) {
                FnLayer("请输入新增组名",group_name);  
            }
        });
    });
    */
    //// 选择 groupname end 
   

    // 滑块 开始 
    function FnRange(inputid,textid,widid,num,id){
        var range= document.getElementById(inputid);
        var result = document.getElementById(textid);
        var wid = document.getElementById(widid);
        var maxnum = range.getAttribute("max");
        cachedRangeValue = /*localStorage.rangeValue ? localStorage.rangeValue :*/  num; 
        // 检测浏览器
        var o = document.createElement('input');
        o.type = 'range';
        if ( o.type === 'text' ) alert('不好意思，你的浏览器还不够酷，试试最新的浏览器吧。');
        range.value = cachedRangeValue;
        wid.style.width = (range.value-num)/(maxnum-num)*100 + "%";
        range.addEventListener("mouseup", function() {
            if(inputid == (id + "_OneMemory")){
                if(range.value >= 128 && range.value < 256){
                    result.innerHTML = "128M";
                }else if(range.value >= 256 && range.value < 512){
                    result.innerHTML = "256M";
                }else if(range.value >= 512 && range.value < 1024){
                    result.innerHTML = "512M";
                }else if(range.value >= 1024 && range.value < 2048){
                    result.innerHTML = "1G";
                }else if(range.value >= 2048 && range.value < 3072){
                    result.innerHTML = "2G";
                }else if(range.value >= 3072 && range.value < 4096){
                    result.innerHTML = "3G";
                }else if(range.value >= 4096 && range.value < 5120){
                    result.innerHTML = "4G";
                }else if(range.value >= 5120 && range.value < 6144){
                    result.innerHTML = "5G";
                }else if(range.value >= 6144 && range.value < 7168){
                    result.innerHTML = "6G";
                }else if(range.value >= 7168 && range.value < 8100){
                   result.innerHTML = "7G";
                }else{
                   result.innerHTML = "8G";
                }
            }else{
               result.innerHTML = range.value; 
            }
            wid.style.width = (range.value-num)/(maxnum-num)*100 + "%";
            //alert("你选择的值是：" + range.value + ". 我现在正在用本地存储保存此值。在现代浏览器上刷新并检测。");
            //localStorage ? (localStorage.rangeValue = range.value) : alert("数据保存到了数据库或是其他什么地方。");
            //result.innerHTML = range.value;
            FnPrice(id);
        }, false);
        // 滑动时显示选择的值
        range.addEventListener("input", function() {
            if(inputid == (id + "_OneMemory")){
                if(range.value >= 128 && range.value < 256){
                    result.innerHTML = "128M";
                }else if(range.value >= 256 && range.value < 512){
                    result.innerHTML = "256M";
                }else if(range.value >= 512 && range.value < 1024){
                    result.innerHTML = "512M";
                }else if(range.value >= 1024 && range.value < 2048){
                    result.innerHTML = "1G";
                }else if(range.value >= 2048 && range.value < 3072){
                    result.innerHTML = "2G";
                }else if(range.value >= 3072 && range.value < 4096){
                    result.innerHTML = "3G";
                }else if(range.value >= 4096 && range.value < 5120){
                    result.innerHTML = "4G";
                }else if(range.value >= 5120 && range.value < 6144){
                    result.innerHTML = "5G";
                }else if(range.value >= 6144 && range.value < 7168){
                    result.innerHTML = "6G";
                }else if(range.value >= 7168 && range.value < 8100){
                   result.innerHTML = "7G";
                }else{
                   result.innerHTML = "8G";
                }
            }else{
               result.innerHTML = range.value; 
            }
            wid.style.width = (range.value-num)/(maxnum-num)*100 + "%";

        }, false);
    }
    
    
    
   $(".fn-circle").each(function(){
        var this_id= $(this).attr("id");
        var OneMemory =  this_id + "_OneMemory";
        var OneMemoryText = this_id + "_OneMemoryText";
        var OneMemoryWid = this_id + "_OneMemoryWid";
        var NodeNum = this_id + "_NodeNum";
        var NodeText = this_id + "_NodeText";
        var NodeWid = this_id + "_NodeWid";
        var Disk = this_id + "_Disk";
        var DiskText = this_id + "_DiskText";
        var DiskWid = this_id + "_DiskWid";
        var TimeLong = this_id + "_TimeLong";
        var TimeLongText = this_id + "_TimeLongText";
        var TimeLongWid = this_id + "_TimeLongWid";
        //FnRange(OneMemory,OneMemoryText,OneMemoryWid,128,this_id);
        //FnRange(NodeNum,NodeText,NodeWid,1,this_id);
        //FnRange(Disk,DiskText,DiskWid,1,this_id);
        //FnRange(TimeLong,TimeLongText,TimeLongWid,1,this_id);
    });
    
    // 滑动框 结束
    //计算价格
    var before_memory= $("#pre_paid_memory_price").attr("value");
    var before_disk= $("#pre_paid_disk_price").attr("value");
    var before_net= $("#post_paid_net_price").attr("value");
    var after_memory= $("#post_paid_memory_price").attr("value");
    var after_disk= $("#post_paid_disk_price").attr("value");
    var after_net= $("#post_paid_net_price").attr("value");
    $(".aft-memory").html(after_memory);
    $(".aft-disk").html(after_disk);
    $(".aft-net").html(after_net);

    $(".fn-circle").each(function(){
        var this_id= $(this).attr("id");
        //FnPrice(this_id);
    });
        

    function FnPrice(myid){
        var oId = "#" +  myid+"_OneMemoryText";
        var oNode ="#" + myid+ "_NodeText" ;
        var oDisk = "#" + myid+ "_DiskText";
        var oTime ="#" + myid + " .buy_month li.active";
        var omemory_onoff = "#" + myid + "_MoneyBefore";
        var odisk_onoff = "#" + myid + "_DiskBefore";
        var  memory_num = parseInt($(oId).html());
        if(memory_num > 10){
            memory_num = memory_num / 1024;
        }

        var node_num = parseInt($(oNode).html());
        var Disk_num = parseInt($(oDisk).html());
        var time_num = parseInt($(oTime).attr("data-time"));
        var memory_onoff = $(omemory_onoff).prop("checked");
        var disk_onoff = $(odisk_onoff).prop("checked");
        var onehour;
        //计算
        if(memory_onoff == true && disk_onoff == true){
            onehour = before_memory * memory_num  +  before_disk * Disk_num;
            Fnmemory(myid);
        }else if(memory_onoff == true && disk_onoff != true){
            onehour = before_memory * memory_num;
            Fnmemory(myid);
        }else if(memory_onoff != true && disk_onoff == true){
            onehour = before_disk * Disk_num;
            Fnmemory(myid);
        }else{
            onehour = 0;
            Fnmemory(myid);
        }
        //计算 
        function Fnmemory(my_id){
            var total_money= onehour * 24 * time_num  *30 * node_num;
            var buy_money;
            $("del.before_money").html((total_money*2).toFixed(2));
            if(time_num==12){
                total_money = total_money * 0.9;
            }else if(time_num==24){
                total_money = total_money * 0.8;
            }
            var htmlid = "#" + my_id + "_need-money" ;
            $(htmlid).html(total_money.toFixed(2));
        }
    }
    ///
    function toDecimal2(x){
        var f = parseFloat(x);
        if (isNaN(f)) {
            return false;
        }
        var f = Math.round(x * 100) / 100;
        var s = f.toString();
        var rs = s.indexOf('.');
        if (rs < 0) {
            rs = s.length;
            s += '.';
        }
        while (s.length <= rs + 2) {
            s += '0';
        }
        return s;
    }
    ///
    // 计算价格结束

    // 显示 隐藏
     $(".fn-circle").each(function(){
        var this_id= $(this).attr("id");
        /*
        $("#"+ this_id +"_MoneyBefore").change(function(){
            var onoff = $("#"+ this_id +"_MoneyBefore").prop("checked");
            var onoff2 = $("#"+ this_id +"_DiskBefore").prop("checked");
            if((onoff == true) | (onoff2 == true)){
                $("#"+ this_id +"_baoyuegoumai").show();
            }else{
                $("#"+ this_id +"_baoyuegoumai").hide();
            } 
            FnPrice(this_id);
        });
        $("#"+ this_id +"_MoneyAfter").change(function(){
            var onoff = $("#"+ this_id +"_MoneyBefore").prop("checked");
            var onoff2 = $("#"+ this_id +"_DiskBefore").prop("checked");
            if((onoff == true) | (onoff2 == true)){
                $("#"+ this_id +"_baoyuegoumai").show();
            }else{
                $("#"+ this_id +"_baoyuegoumai").hide();
            } 
            FnPrice(this_id);
        });
        */
        //
        
        //
        $("#"+ this_id +"_DiskBefore").change(function(){
            var onoff = $("#"+ this_id +"_DiskBefore").prop("checked");
            var onoff2 = $("#"+ this_id +"_MoneyBefore").prop("checked");
            if(onoff == true){
                $("#"+ this_id + "_disk_box").show();
            }else{
                $("#"+ this_id + "_disk_box").hide();
            }
            if((onoff == true) | (onoff2 == true)){
                $("#"+ this_id +"_baoyuegoumai").show();
            }else{
                $("#"+ this_id +"_baoyuegoumai").hide();
            } 
            FnPrice(this_id);
        });
        $("#"+ this_id +"_DiskAfter").change(function(){
            var onoff = $("#"+ this_id +"_DiskBefore").prop("checked");
            var onoff2 = $("#"+ this_id +"_MoneyBefore").prop("checked");
            if(onoff == true){
                $("#"+ this_id + "_disk_box").show();
            }else{
                $("#"+ this_id + "_disk_box").hide();
            }
            if((onoff == true) | (onoff2 == true)){
                $("#"+ this_id +"_baoyuegoumai").show();
            }else{
                $("#"+ this_id +"_baoyuegoumai").hide();
            } 
            FnPrice(this_id);
        });
     });
    
    // 上一步
    /*
    $("#pre_page").click(function () {
        var compose_file_id = $("#compose_file_id").val();
        var tenantName = $("#tenantNameValue").val();
        url = "/apps/"+tenantName+"/compose-create?id="+compose_file_id;
        window.location.href = url
    });*/

    //提交
    $("#compose2").click(function(){
        $(this).attr('disabled',true);
        var secbox= $(".fn-circle");
        var secdate = [];
        $(secbox).each(function(){
            var appid = $(this).attr("id");
            var appname = $("#"+appid+"_create_app_name").val();
            var service_image = $(this).attr("service_image")
            /*
            if(appname == ""){
                $("#"+appid+"_create_app_name").parent().next("p.fm-tips").slideDown();
                 $("#compose2").attr('disabled',false);
                return;
            }else{
                $("#"+appid+"_create_app_name").parent().next("p.fm-tips").slideUp();
            }*/
           
            var this_json={
                "service_image":service_image,
                "service_id" : appid,
                "app_name" : appname
            }
            //console.log(this_json);
            secdate.push(this_json);
        });
       
        //
        var tenantName = $("#tenantNameValue").val();
        var compose_group_name = $("#com-name").val();
        var group_id = $("#group_id").val();
        var compose_file_id = $("#compose_file_id").val();
        ///
        
        $.ajax({
            type: "post",
            url: "/apps/"+tenantName+"/compose-step2/",
            dataType: "json",
            data: {
                    "compose_file_id":compose_file_id,
                    "group_id":group_id,
                    "services_attach_infos":JSON.stringify(secdate)
                    },
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success:function(data){
                status = data.status;
                if (status == 'success'){
                    var compse_file_id = data.compose_file_id;
                    var group_id = data.group_id;
                    window.location.href="/apps/"+tenantName +"/compose-step3/?id="+compse_file_id+"&group_id="+group_id;
                }else if (status == "failure"){
                    swal("数据中心初始化失败");
                }else if (status == "owed"){
                    swal("余额不足请及时充值");
                }else if (status =="no_group"){
                    swal("当前组不存在");
                }else if(status =="over_memory"){
                    if (data.tenant_type == "free"){
                        swal("资源已达上限,不能创建");
                    }else
                        swal("资源已达上限，不能创建");
                }else if(status == "over_money"){
                    swal("余额不足无法创建");
                }else if(status == "empty"){
                    swal("应用名为空");
                }else if(status == "no_service"){
                    swal("应用不存在");
                }
                else{
                    swal("创建失败");
                }
                $("#compose2").attr('disabled',false);
            },
            error: function() {
                $("#compose2").attr('disabled',false);
            },
            cache: false
            // processData: false
        });
        
        ///
    });
    //////
    $('.fn-tips').tooltip();
    // // // 第二步 基本设置 end

    /* ljh 2017-03-07 */
    $(".buy_month li").click(function(){
        $(this).addClass("active").siblings().removeClass("active");
       // FnPrice($(this).parents("section.fn-circle").attr("id"));
    });
    /* ljh 2017-03-07 */
});
