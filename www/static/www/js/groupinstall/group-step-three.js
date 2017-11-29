$(function(){

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
        var minMeVal = $("#"+ this_id + "_MemoryRange").attr("min");
        if(Number(minMeVal)>1000){
            var Memory = parseInt(minMeVal/1024);
            if(Memory>=1 && Memory<2){
                    minMeVal = 1
            }else if(Memory>=2 && Memory<4){
                        minMeVal = 2
            }else if(Memory>=4 && Memory<6){
                        minMeVal = 4
            }else if(Memory>=6 && Memory<8){
                        minMeVal = 6
            }else{
                        minMeVal = 8 
            }
        }else{
            if(minMeVal >=128 &&  minMeVal < 256){
                minMeVal = 128
            }else if(minMeVal >= 256 &&  minMeVal < 512){
                minMeVal = 256
            }else{
                minMeVal = 512
            }
        }
        $("#"+ this_id + "_MemoryText").html(minMeVal>10 ? minMeVal + "M" : minMeVal + "G");
        //
        $("#"+ this_id + "_MemoryRange").bind('input propertychange',function(){
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
            $("#"+ this_id + "_MemoryText").html(memoryVal>10 ? memoryVal + "M" : memoryVal + "G");
        });
        $("#"+ this_id + "_extend_method").change(function(){
            var oval= $("#"+ this_id + "_extend_method option:selected") .val();
            if(oval == "stateless"){
                $("#"+ this_id + "_fn_stateless").show();
                $("#"+ this_id + "_fn_state").hide();
            }else{
                $("#"+ this_id + "_fn_stateless").hide();
                $("#"+ this_id + "_fn_state").show();
            }
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
            var  methodval= $("#"+ appid + "_extend_method option:selected").val();
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