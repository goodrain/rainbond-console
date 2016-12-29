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

    // // // 第二步 基本设置 开始 
    //弹出层
    function FnLayer(textTit){
        var oDiv = '<div class="layerbg"><div class="layermain"></div></div>';
        var oCloseBtn = '<a href="javascript:;" class="closebtn fn-close">X</a>';
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
                            $("#group-name option").eq(0).after(Option);
                            $("#group-name option").each(function(){
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
    $("#group-name").change(function(){
     var groupName=$("#group-name option:selected").val();
        //console.log(groupName);
        if(groupName == -2) {
            FnLayer("请输入新增组名");  
        }
    });
    //// ww-2016-12-6 选择 groupname end 
    
	// 滑块 开始 
	function FnRange(inputid,textid,widid,num){
		var range= document.getElementById(inputid);
		var result = document.getElementById(textid);
		var wid = document.getElementById(widid);
        var maxnum = range.getAttribute("max");
		cachedRangeValue = /*localStorage.rangeValue ? localStorage.rangeValue :*/ num; 
		// 检测浏览器
		var o = document.createElement('input');
	    o.type = 'range';
	    if ( o.type === 'text' ) alert('不好意思，你的浏览器还不够酷，试试最新的浏览器吧。');
	    range.value = cachedRangeValue;
	    wid.style.width = (range.value-num)/(maxnum-num)*100 + "%";
	    range.addEventListener("mouseup", function() {
            if(inputid == "OneMemory"){
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
            FnPrice();
	    }, false);
	    // 滑动时显示选择的值
	    range.addEventListener("input", function() {
            if(inputid == "OneMemory"){
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
    
    FnRange("OneMemory","OneMemoryText","OneMemoryWid",128);
    FnRange("NodeNum","NodeText","NodeWid",1);
    FnRange("Disk","DiskText","DiskWid",1);
    FnRange("TimeLong","TimeLongText","TimeLongWid",1);
    
   
   
    
    // 滑动框 结束
    
    //计算价格
    var before_memory= $("#pre_paid_memory_price").attr("value");
    var before_disk= $("#pre_paid_disk_price").attr("value");
    var before_net= $("#post_paid_net_price").attr("value");
    var after_memory= $("#post_paid_memory_price").attr("value");
    var after_disk= $("#post_paid_disk_price").attr("value");
    var after_net= $("#post_paid_net_price").attr("value");
    $("#aft-memory").html(after_memory);
    $("#aft-disk").html(after_disk);
    $("#aft-net").html(after_net);

    FnPrice();

    function FnPrice(){
        var  memory_num = parseInt(document.getElementById("OneMemoryText").innerHTML);
        if(memory_num > 10){
            memory_num = memory_num / 1024;
        }
        var node_num = parseInt(document.getElementById("NodeText").innerHTML);
        var Disk_num = parseInt(document.getElementById("DiskText").innerHTML);
        var time_num = parseInt(document.getElementById("TimeLongText").innerHTML);
        var memory_onoff = document.getElementById("MoneyBefore").checked;
        var disk_onoff = document.getElementById("DiskBefore").checked;
        var onehour;
        //计算
        if(memory_onoff == true && disk_onoff == true){
            onehour = before_memory * memory_num  +  before_disk * Disk_num;
            Fnmemory();
        }else if(memory_onoff == true && disk_onoff != true){
            onehour = before_memory * memory_num;
            Fnmemory();
        }else if(memory_onoff != true && disk_onoff == true){
            onehour = before_disk * Disk_num;
            Fnmemory();
        }else{
            onehour = 0;
            Fnmemory();
        }
        //计算 
        function Fnmemory(){
            var total_money= onehour * 24 * time_num  *30 * 4 * node_num;
            var buy_money;
            if(time_num>=12){
                buy_money = onehour * 24 * time_num *1.5 *30;
            }else{
                buy_money = onehour * 24 * time_num *2*30;
            }
            $("#need-money").html(total_money.toFixed(2));
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
    $("#MoneyBefore").change(function(){
        var onoff = $("#MoneyBefore").prop("checked");
        if(onoff == true){
            // $(".fn-memory-node").show();
            $("#aft-memory-box").hide();
        }else{
            //$(".fn-memory-node").hide();
            $("#aft-memory-box").show();
        }
        FnPrice();
    });
    $("#MoneyAfter").change(function(){
        
        var onoff = $("#MoneyAfter").prop("checked");
        if(onoff == false){
            //$(".fn-memory-node").show();
            $("#aft-memory-box").hide();
        }else{
            //$(".fn-memory-node").hide();
            $("#aft-memory-box").show();
        }
        FnPrice();
    });
    $("#DiskBefore").change(function(){
        var onoff = $("#DiskBefore").prop("checked");
        if(onoff == true){
            $(".fn-disk").show();
            $("#aft-disk-box").hide();
        }else{
            $(".fn-disk").hide();
            $("#aft-disk-box").show();
        }
        FnPrice();
    });
    $("#DiskAfter").change(function(){
        var onoff = $("#After").prop("checked");
        if(onoff == false){
            $(".fn-disk").show();
            $("#aft-disk-box").hide();
        }else{
            $(".fn-disk").hide();
            $("#aft-disk-box").show();
        }
        FnPrice();
    });
    // 输入框输入样式

    // 01 输入用户名
    $('#create_app_name').blur(function(){
        var appName = $(this).val();
        //var checkReg = /^[a-z][a-z0-9-]*[a-z0-9]$/;
        //var result = true;
        if(appName == ""){
            $('#create_appname_notice').slideDown();
            return;
        }else{
            $('#create_appname_notice').slideUp();
        }
    });
    // 01 end 
    // // // 第二步 基本设置 结束 
});
