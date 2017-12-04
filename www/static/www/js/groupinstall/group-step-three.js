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

    $(".tablink a").eq(0).addClass("sed");
    $("section.app-box").eq(0).show();
    $(".tablink a").click(function () {
        $(".tablink a").removeClass("sed");
        $(".tablink a").eq($(this).index()).addClass("sed");
        $("section.app-box").hide();
        $("section.app-box").eq($(this).index()).show();
    });

   /*ww-2017-11-7*/
    $(".fn-app-box").each(function(){
        var this_id= $(this).attr("data-id");
        var minMemoryval = $("#"+ this_id + "_MemoryRange").attr("data-min");
        var Memeryonoff = $("#"+ this_id + "_MemoryRange").attr("data-money");
        var memoryStr = "";
            if(Memeryonoff == "free"){
                if(minMemoryval == "128"){
                    memoryStr = '<a href="javascript:;" class="sed">128M</a><a href="javascript:;">256M</a><a href="javascript:;">512M</a><a href="javascript:;">1G</a>';
                }else if(minMemoryval == "256"){
                    memoryStr = '<a href="javascript:;" class="sed">256M</a><a href="javascript:;">512M</a><a href="javascript:;">1G</a>';
                }else if(minMemoryval == "512"){
                    memoryStr = '<a href="javascript:;" class="sed">512M</a><a href="javascript:;">1G</a>';
                }else if(minMemoryval == "1024"){
                    memoryStr = '<a href="javascript:;" class="sed">1G</a>';
                }else{
                    memoryStr = '此应用所需内存超过能使用的最大内存！';
                }
            }else{
                if(minMemoryval == "128"){
                    memoryStr = '<a href="javascript:;" class="sed">128M</a><a href="javascript:;">256M</a><a href="javascript:;">512M</a><a href="javascript:;">1G</a><a href="javascript:;">2G</a><a href="javascript:;">4G</a><a href="javascript:;">8G</a>';
                }else if(minMemoryval == "256"){
                    memoryStr = '<a href="javascript:;" class="sed">256M</a><a href="javascript:;">512M</a><a href="javascript:;">1G</a><a href="javascript:;">2G</a><a href="javascript:;">4G</a><a href="javascript:;">8G</a>';
                }else if(minMemoryval == "512"){
                    memoryStr = '<a href="javascript:;" class="sed">512M</a><a href="javascript:;">1G</a><a href="javascript:;">2G</a><a href="javascript:;">4G</a><a href="javascript:;">8G</a>';
                }else if(minMemoryval == "1024"){
                    memoryStr = '<a href="javascript:;" class="sed">1G</a><a href="javascript:;">2G</a><a href="javascript:;">4G</a><a href="javascript:;">8G</a>';
                }else if(minMemoryval == "2048"){
                    memoryStr = '<a href="javascript:;" class="sed">2G</a><a href="javascript:;">4G</a><a href="javascript:;">8G</a>';
                }else if(minMemoryval == "4096"){
                    memoryStr = '<a href="javascript:;" class="sed">4G</a><a href="javascript:;">8G</a>';
                }else if(minMemoryval == "8192"){
                    memoryStr = '<a href="javascript:;" class="sed">8G</a>';
                }else{
                    memoryStr = '此应用所需内存超过能使用的最大内存！';
                }
            }
            $("#"+ this_id + "_MemoryRange").html(memoryStr);
            $("#"+ this_id + "_MemoryText").html(minMemoryval<1000 ? minMemoryval + "M" : parseInt(minMemoryval/1024) + "G");
            $("#"+ this_id + "_MemoryRange a").click(function(){
                $("#"+ this_id + "_MemoryRange a").removeClass("sed");
                $(this).addClass("sed");
                var memoryVal = $(this).html();
                $("#"+ this_id + "_MemoryText").html(memoryVal);
            }); 
    });

    
    /*ww-2017-11-7*/


    $("#group_install_three").on("click", function () {
        var share_group_id = $("#shared_group_id").val();
        var service_group_id = $("#service_group_id").val();
        var tenantName = $("#tenantNameValue").val();
        var keyEnvMap = {};
        var keyMethodval = {};
        var keyMemoryNum = {};
        $(".app-box").each(function () {
            var service_key = $(this).attr("data-key");
            var appid = $(this).attr("data-id");
            var  methodval= $('input[name="'+ appid +'_extend_method"]:checked').val();
            var  memory_num = parseInt($("#"+ appid + "_MemoryText").html());
            var env_tr = $(this).find("tbody.environment").children("tr");
            var envList = [];
            $(env_tr).each(function(){
                var attr_name = $(this).find("td[name='attr_name']").html();
                console.log("attr_name:"+attr_name);
                var attr_value = $(this).find("[name='attr_value']").val() || $(this).find("[name='attr_value']").html() ;
                console.log(attr_value);
                var envMap = {
                    "attr_name":attr_name,
                    "attr_value":attr_value
                };
                envList.push(envMap);
            });

            keyEnvMap[service_key] = envList;
            keyMethodval[service_key] = methodval;
            keyMemoryNum[service_key] = memory_num;
        });

        
        var envs = JSON.stringify(keyEnvMap);
        var data = {
            "group_id":service_group_id,
            "envs":envs,
            "methodval": JSON.stringify(keyMethodval),
            "service_min_memory" : JSON.stringify(keyMemoryNum)
        };
        console.log(data);
        $.ajax({
            type : "post",
            url : "/apps/" + tenantName + "/group-deploy/" + share_group_id+"/step3/",
            data : data,
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {
                var dataObj = msg;
                if (dataObj["success"]) {
                    window.location.href=dataObj["next_url"]
                } else {
                    swal("系统异常");
                    $("#group_install_three").removeAttr('disabled');
                }
            },
            error : function() {
                swal("系统异常,请重试");
                $("#group_install_three").removeAttr('disabled');
            }
        })

    });

});