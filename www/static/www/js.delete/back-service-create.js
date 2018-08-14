//服务创建
function service_create(tenantName, service_key, app_version) {
	window.location.href = "/apps/" + tenantName
			+ "/service-deploy/?service_key=" + service_key + "&app_version=" + app_version
}

function service_update(tenantName, service_key, app_version, update_version) {
    window.location.href = '/ajax/'+tenantName+'/remote/market?service_key='
            + service_key + '&app_version=' + app_version+'&update_version='+update_version+'&action=update';
}


//创建应用
$(function(){
    /*
    $('#create_service_name').blur(function(){
        var appName = $(this).val(),
            checkReg = /^[a-z][a-z0-9-]*[a-z0-9]$/,
            result = true;
            
        if(appName == ""){
            $('#create_service_notice').slideDown();
            return;
        }else{
            $('#create_service_notice').slideUp();
        }
    });
    //第一步
    
    $('#back_service_step1').click(function(){
        var appName = $('#create_service_name').val(),
            checkReg = /^[a-z][a-z0-9-]*[a-z0-9]$/,
            result = true;
            
        if(appName == ""){
            $('#create_service_notice').slideDown();
            return;
        }else{
            $('#create_service_notice').slideUp();
        }
		var tenantName = $("#tenantName").val()
		$("#back_service_step1").prop('disabled', true)
		var _data = $("form").serialize();
    	$.ajax({
    		type : "post",
    		url : "/apps/" + tenantName + "/service-deploy/",
    		data : _data,
    		cache : false,
    		beforeSend : function(xhr, settings) {
    			var csrftoken = $.cookie('csrftoken');
    			xhr.setRequestHeader("X-CSRFToken", csrftoken);
    		},
    		success : function(msg) {
    			var dataObj = msg;
                $("#back_service_finished").prop('disabled', false);
    			if (dataObj["status"] == "notexist"){
    				swal("所选的服务类型不存在");
    			} else if (dataObj["status"] == "depend_service_notexit"){
    			    swal("依赖的服务类型不存在，请先下载到服务市场");
    			} else if (dataObj["status"] == "owed"){
    				swal("余额不足请及时充值")
    			} else if (dataObj["status"] == "expired"){
                    swal("试用已到期")
                } else if (dataObj["status"] == "exist") {
    				swal("服务名已存在");
    			} else if (dataObj["status"] == "over_memory") {
    				swal("资源已达上限，不能创建");
    			} else if (dataObj["status"] == "over_money") {
    				swal("余额不足，不能创建");
    			} else if (dataObj["status"] == "empty") {
    				swal("服务名称不能为空");    				
    			}else if (dataObj["status"] == "success") {
    				service_alias = dataObj["service_alias"]
    				window.location.href = "/apps/" + tenantName + "/" + service_alias + "/setup/extra/";
    			} else {
    				swal("创建失败");
                }
    		},
    		error : function() {
    			swal("系统异常,请重试");
    			$("#back_service_finished").prop('disabled', false)
    		}
    	})
    });
    */

    $('#back_service_finished').click(function() {
        envs = []
        var flag = false
        $('tbody tr').each(function() {
            env = {};
            $(this).find('[name^=attr]').each(function(event) {
                i = $(this);
                name = $(this).attr('name');
                value = $(this).val() || i.html();
                if (value) {
                    env[name] = value;
                } else {
                    showMessage("有未填写的内容");
                    flag = true
                }
            });
            envs.push(env);
        });
        if (flag) {
            return false;
        }
        var csrftoken = $.cookie('csrftoken');
        data = {"envs": envs};
        $.ajax({
          url: window.location.pathname,
          method: "POST",
          data: $.stringify(data),
          beforeSend: function(xhr) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
          },
          success :function (event) {
            if (event.success) {
              window.location.href = event.next_url;
            } else {
              showMessage(event.info);
            }
          },
          contentType: 'application/json; charset=utf-8',

          statusCode: {
            403: function(event) {
              alert("你没有此权限");
            }
          },
        });
    });

    //// ww-2016-12-6 选择 groupname start
    //弹出层
    function FnLayer(textTit){
        var oDiv = '<div class="layerbg"><div class="layermain"></div></div>';
        var oCloseBtn = '<a href="javascript:;" class="closebtn fn-close" style="color:#fff;"><i class="fa fa-times"></i></a>';
        var oTit = '<p class="layer-tit">'+ textTit +'</p>';
        var oInput ='<p class="input-css"><input name="" type="text" value="" /></p>';
        var oLink = '<p class="layerlink text-center"><button type="button" class="fn-sure btn btn-success" style="margin:0 5px;">确定</button><button type="button" class="fn-close btn btn-danger" style="margin:0 5px;">取消</button></p>';
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
                var tenant_name = $("#tenantName").val();
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
        var arr = [];
        var value_min = $(".node_memory").attr("min");
        var value_max = $(".node_memory").attr("max");
        var next = value_min;
        var num = 0;
        while(next<=value_max){
            next = value_min * Math.pow(2,num);
            arr.push(next);
            num++;
        }
        console.log(arr);
        range.addEventListener("mouseup", function() {
            if(inputid == "OneMemory"){
                for( var i = 0;i<arr.length-1;i++ )
                {
                    if( range.value >= arr[i] && range.value < arr[i+1] )
                    {
                        var size = arr[i];
                        $("#OneMemoryWid").attr("data-size",size);
                        if( size < 1024 )
                        {
                            result.innerHTML = size + "M";
                        }
                        else{
                            result.innerHTML = parseInt(size/1024) + "G";
                        }
                    }
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
                for( var i = 0;i<arr.length-1;i++ )
                {
                    if( range.value >= arr[i] && range.value < arr[i+1] )
                    {
                        var size = arr[i];
                        result.setAttribute("data-size",size);
                        if( size < 1024 )
                        {
                            result.innerHTML = size + "M";
                        }
                        else{
                            result.innerHTML = parseInt(size/1024) + "G";
                        }
                    }
                }
            }else{
               result.innerHTML = range.value; 
            }
            wid.style.width = (range.value-num)/(maxnum-num)*100 + "%";

        }, false);
    }
    
   
    var small_memory = $("#small-memory").attr("value");
    var is_tenant_free = $("#is_tenant_free").attr("value");
    if(small_memory >= 1024){
        console.log(2);
        $("#OneMemoryText").html(small_memory/1024 + "G");
    }else{
        console.log(3);
        $("#OneMemoryText").html(small_memory + "M");
    }
    if(is_tenant_free == "True"){
        var tenant_name=$("#tenantName").val();
        if(small_memory > 1024 && tenant_name !="sinoteach"){
            swal("免费用户应用内存最多1G！");
        }
    }
    
   
    // $("#OneMemory").attr("min",small_memory);
    // FnRange("OneMemory","OneMemoryText","OneMemoryWid",small_memory);
    // FnRange("NodeNum","NodeText","NodeWid",1);
    // FnRange("Disk","DiskText","DiskWid",1);
    //FnRange("TimeLong","TimeLongText","TimeLongWid",1);
    
   
   
    
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

    // FnPrice();

    function FnPrice(){
        var  memory_num = parseInt($("#OneMemoryText").attr("data-size"));
        if(memory_num > 10){
           memory_num = memory_num / 1024;
        }
        var node_num = parseInt(document.getElementById("NodeText").innerHTML);
        var Disk_num = parseInt(document.getElementById("DiskText").innerHTML);
        var time_num = parseInt($(".buy_month li.active").attr("data-time"));
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
            var total_money= onehour * 24 * time_num  *30 * node_num;
            // console.log("===> onehour "+onehour+" \t node_num "+node_num+"\t time_num "+time_num);
            $("del.before_money").html((total_money*2).toFixed(2));
            if(time_num == 12){
                total_money = total_money * 0.9;
            }else if(time_num == 24){
                total_money = total_money * 0.8;
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
    /*
    $("#MoneyBefore").change(function(){
        var onoff = $("#MoneyBefore").prop("checked");
        var onoff2 = $("#DiskBefore").prop("checked");
        if((onoff == true) | (onoff2 == true)){
            $("#baoyuegoumai").show();
        }else{
            $("#baoyuegoumai").hide();
        }
        FnPrice();
    });
    $("#MoneyAfter").change(function(){
        var onoff = $("#MoneyBefore").prop("checked");
        var onoff2 = $("#DiskBefore").prop("checked");
        if((onoff == true) | (onoff2 == true)){
            $("#baoyuegoumai").show();
        }else{
            $("#baoyuegoumai").hide();
        }
        FnPrice();
    });
    */
    $("#DiskBefore").change(function(){
        var onoff = $("#DiskBefore").prop("checked");
        var onoff2 = $("#MoneyBefore").prop("checked");
        if(onoff == true){
            $(".fn-disk").show();
        }else{
            $(".fn-disk").hide();
        }
        if((onoff == true) | (onoff2 == true)){
            $("#baoyuegoumai").show();
        }else{
            $("#baoyuegoumai").hide();
        }
        FnPrice();
    });
    $("#DiskAfter").change(function(){
        var onoff = $("#DiskBefore").prop("checked");
        var onoff2 = $("#MoneyBefore").prop("checked");
        if(onoff == true){
            $(".fn-disk").show();
        }else{
            $(".fn-disk").hide();
        }
        if((onoff == true) | (onoff2 == true)){
            $("#baoyuegoumai").show();
        }else{
            $("#baoyuegoumai").hide();
        }
        FnPrice();
    });
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

    //ww-2017-10-31 new 内存start 
    $("#MemoryRange").bind('input propertychange',function(){
        var memoryVal = $(this).val();
        if(Number(memoryVal)>1000){
            var Memory = parseInt(memoryVal/1024);
            if(Memory>=1 && Memory<2){
                memoryVal = 1
            }else if(Memory>=2 && Memory<4){
                memoryVal = 2
            }else if(Memory>=4 && Memory<6){
                memoryVal = 4
            }else if(Memory>=6 && Memory<8){
                memoryVal = 6
            }else{
                memoryVal = 8 
            }
        }else{
            if(memoryVal >=128 &&  memoryVal < 256){
                memoryVal = 128
            }else if(memoryVal >= 256 &&  memoryVal < 512){
                memoryVal = 256
            }else{
                 memoryVal = 512
            }
        }
        $("#MemoryText").html(memoryVal>10 ? memoryVal + "M" : memoryVal + "G");
    });
    $("#NodeNum").bind('input propertychange',function(){
        var nodeVal = $(this).val();
        $("#NodeText").html(nodeVal + "个");
    });
    //ww-2017-10-31 new 内存start 

    /// 从应用提交
    //提交 
    $("#back_service_step1").click(function(event){
        var small_memory = $("#small-memory").attr("value");
        var is_tenant_free = $("#is_tenant_free").attr("value");
        var tenant_name=$("#tenantName").val();
        if(is_tenant_free == "True"){
            if(small_memory > 1024 && tenant_name !="sinoteach"){
                swal("内存不够！");
                return false;
            }
        }
        var appname = $("#create_name").val();
        var groupname = $("#group-name option:selected").html();
        var groupid = $("#group-name option:selected").attr("value");
        var myWay = $(".fn-way").attr("data-action");
        
        if(appname == ""){
            $("#create_name_notice").show();
            return false;
        }else{
            $("#create_name_notice").hide();
        }
        
        ///
        $("#back_service_step1").attr('disabled', true);
        var tenantName= $('#tenantName').val();
        var service_key = $("#service_key").val();
        var app_version = $("#app_version").val();
        $.ajax({
            type : "post",
            url : "/apps/" + tenantName + "/service-deploy/",
            data : {
                "create_app_name" : appname,
                "service_key" : service_key,
                "app_version" :app_version,
                "groupname" : groupname,
                "select_group_id" : groupid
                //"memory_pay_method" : memory_onoff ? "prepaid":"postpaid",
                //"disk_pay_method" : disk_onoff ? "prepaid":"postpaid",
                //"service_min_memory" : memory_num,
                //"service_min_node" : node_num,
                //"disk_num" : disk_num,
                //"pre_paid_period" : time_num
            },
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {
                var dataObj = msg;
                if (dataObj["status"] == "notexist"){
                    swal("所选的服务类型不存在");
                } else if (dataObj["status"] == "owed"){
                    swal("余额不足请及时充值")
                } else if (dataObj["status"] == "expired"){
                    swal("试用已到期")
                } else if (dataObj["status"] == "over_memory") {
                    if (dataObj["tenant_type"] == "free"){
                        swal("资源已达上限, 不能创建");
                    }else
                        swal("资源已达上限，不能创建");
                } else if (dataObj["status"] == "over_money") {
                    swal("余额不足，不能创建");
                } else if (dataObj["status"] == "empty") {
                    swal("服务名称不能为空");
                }else if (dataObj["status"] == "success") {
                    service_alias = dataObj["service_alias"]
                    window.location.href = "/apps/" + tenantName + "/" + service_alias + "/deploy/setting/";
                } else if (dataObj["status"] == "failure"){
                    swal("创建失败");
                }else{
                    swal("创建失败");
                }
                $("#back_service_step1").attr('disabled', false);
            },
            error : function() {
                swal("系统异常,请重试");
                $("#BtnFirst").attr('disabled', false);
                $("#back_service_step1").attr('disabled', false);
            }
        });
        ///

    }); 
    $('.fn-tips').tooltip();



    /* ljh 2017-03-07 */
    $(".buy_month li").click(function(){
        $(this).addClass("active").siblings().removeClass("active");
        FnPrice();
    });
    /* ljh 2017-03-07 */
});