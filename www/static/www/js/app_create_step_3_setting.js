$(function () {

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

    //fntabtit();
    function fntabtit(){
        $(".fn-tabcenter").each(function(){
            var thislength = $(this).find("tr").length;
            if(thislength == 0){
                $(this).parent(".fn-tabbox").find(".fn-tabtit").hide();
            }else{
                 $(this).parent(".fn-tabbox").find(".fn-tabtit").show();
            }
        })
    }
    
    //打开新增端口号窗口
    $(".fn-openAdd").on("click",function(){
        // if( $(this).parents("tfoot").find("input.checkDetail").prop("checked") )
        // {
        //     $(this).parents('tfoot').find("option.changeOption").remove();
        //     $("select.add_http").val("HTTP");
        // }
        // else{
        //     var $option = $("<option class='changeOption'>请打开外部访问</option>");
        //     $("select.add_http").prepend($option);
        //     $("select.add_http").val("请打开外部访问");
        // }
        //$(this).parents(".fn-showblock").find(".fn-tabtit").show();
        $(".checkTip").css({"display":"none"});
        $(".addPort").css({"display":"table-row"});
    });

    function checkPort(portNum){
        // dockerfile类型服务端口处理
        var language = $("#language").val();
        if(language == 'docker' || language == 'docker-image' || language == 'docker-compose' ){
            if(!(portNum>0 && portNum<65536)){
                return "端口范围为1~65535";
            }
        }else{
            if(!(portNum>1024 && portNum<65536)){
                return "端口范围为1025~65535";
            }
        }
        return '';
    }

    $(".add_port").blur(function(){

        

        var portNum = parseInt($(".add_port").val());
        if( checkPort(portNum) == '' )
        {
            $(this).parents('tr').find('p.checkTip').css({"display":"none"});
        }
        else{
            $(this).parents('tr').find('p.checkTip').css({"display":"block"});
        }
        // dockerfile类型服务端口处理
        var language = $("#language").val();
        if (language == "docker") {
            $(this).parents('tr').find('p.checkTip').css({"display":"none"});
        }
    })
    //确定添加端口号
    $(".fn-add").on("click",function(){
        var portNum = parseInt($(".add_port").val());
        var language = $("#language").val();
        // dockerfile应用或者端口号在1024-65535之间
        if(checkPort(portNum) == '')
        {
            var addOnoff = matchArr(portNum,$(".portNum"));
            if( addOnoff )
            {
                var arr = ['http','tcp','udp','mysql'];
                var oTr = '<tr><td><a href="javascript:void(0);" class="portNum edit-port fn-tips" data-original-title="当前应用提供服务的端口号。">'+$(".add_port").val()+'</a></td>';
                if( $("#addInner").prop("checked") == true )
                {
                    oTr += '<td><label class="checkbox fn-tips" data-original-title="打开对外服务，其他应用即可访问当前应用。"><input type="checkbox" name="" value="" id="'+$(".add_port").val()+'inner" checked="true" /><span class="check-bg" for="'+$(".add_port").val()+'inner"></span></div></td>';
                }
                else{
                    oTr += '<td><label class="checkbox fn-tips" data-original-title="打开对外服务，其他应用即可访问当前应用。"><input type="checkbox" name="" value="" id="'+$(".add_port").val()+'inner" /><span class="check-bg" for="'+$(".add_port").val()+'inner"></span></label></td>';
                }
                if( $("#addOuter").prop("checked") == true )
                {
                    oTr += '<td><label class="checkbox fn-tips" data-original-title="打开外部访问，用户即可通过网络访问当前应用。"><input class="checkDetail" type="checkbox" name="" value="" id="'+$(".add_port").val()+'outer" checked="true" /><span class="check-bg" for="'+$(".add_port").val()+'outer"></span></label></td><td>';
                    oTr += '<select style="" class="fn-tips" data-original-title="请设定用户的访问协议。" data-port-http="'+$(".add_port").val()+'http">';
                }
                else{
                    oTr += '<td><label class="checkbox fn-tips" data-original-title="打开外部访问，用户即可通过网络访问当前应用。"><input class="checkDetail" type="checkbox" name="" value="" id="'+$(".add_port").val()+'outer" /><span class="check-bg" for="'+$(".add_port").val()+'outer"></span></label></td><td>';
                    oTr += '<select class="fn-tips" data-original-title="请设定用户的访问协议。" data-port-http="'+$(".add_port").val()+'http">';
                }
                for( var i = 0; i < 4; i++ )
                {
                    if( $('.add_http option:selected').val() == arr[i] )
                    {
                        oTr += '<option selected="selected" value='+  arr[i] +'>'+ arr[i]+'</option>';
                    }
                    else{
                        oTr += '<option value='+ arr[i]  +'>'+arr[i]+'</option>';
                    }
                }
                oTr += '</select></td><td><img class="rubbish" src="/static/www/images/rubbish.png"/></td></tr>';
                $(oTr).appendTo(".port");
                $(".addPort").css({"display":"none"});
                delPort();
                //修改端口号
                editCom('.edit-port', function(value){
                     return checkPort(value);
                });
                $('.fn-tips').tooltip();
                checkDetail();
                selectChange();
            }
            else{
                swal("端口号冲突～～");
            }
        }
        else{
            $(this).parents('tr').find('p.checkTip').css({"display":"block"});
        }
        //fntabtit();
        $(".add_port").val("");
    });
    //取消端口号的添加
    $(".fn-noAdd").on("click",function(){
        $(".addPort").css({"display":"none"});
    });
    delPort();
    //删除端口号与环境变量
    function delPort(){
        $("img.rubbish").off("click");
        $("img.rubbish").on("click",function(){
            $(this).parents("tr").remove();
            //fntabtit();
        })
    }
    
    $("#MemoryRange a").click(function(){
        $("#MemoryRange a").removeClass("sed");
        $(this).addClass("sed");
        var memoryVal = $(this).html();
        $("#MemoryText").html(memoryVal);
    });
    delLi();
    //删除依赖与目录
    function delLi(){
        $("img.delLi").off("click");
        $("img.delLi").on("click",function(){
            $(this).parents("tr").remove();
            //fntabtit();
        })
    }
    //修改端口号
    editCom('.edit-port', function(value){
         return checkPort(value);
    });
     //修改变量name
    editCom('.edit-env-name')
    //修改变量key
    editCom('.edit-env-key', function(value){
        var variableReg = /^[A-Z][A-Z0-9_]*$/;
        if( !variableReg.test(value||'') )
        {
            return '变量名由大写字母与数字组成且大写字母开头';
        }
    })
    //修改变量值
    editCom('.edit-env-val');
     function editCom(selector, validate){
        $(selector).editable({
            type: 'text',
            pk: 1,
            success: function (data) {

            },
            error: function (data) {
                msg = data.responseText;
                res = $.parseJSON(msg);
                showMessage(res.info);
            },
            ajaxOptions: {
                beforeSend: function(xhr, settings) {
                    xhr.setRequestHeader("X-CSRFToken", $.cookie('csrftoken'));
                    settings.data += '&action=change_port';
                },
            },
            validate: function (value) {
              
                if(validate){
                    return validate(value)
                }
            }
        });
    }
    //显示添加环境变量内容
    $(".openAddEnviroment").on("click",function(){
        $(".addContent").css({"display":"table-row"});
        //$(this).parents(".fn-showblock").find(".fn-tabtit").show();
    });
    $(".enviroKey").blur(function(){
        var variableReg = /^[A-Z][A-Z0-9_]*$/;
        if( variableReg.test($(".enviroKey").val()) )
        {
            $(this).parent().find("p.checkTip").css({"display":"none"});
        }
        else{
            $(this).parent().find("p.checkTip").css({"display":"block"});
        }
    });
    $(".addEnviroment").on("click",function(){
        if( $(".enviroKey").val() && $(".enviroValue").val() && $(".enviroName").val() )
        {
            var onOff = matchArr($(".enviroKey").val(),$(".enviromentKey"));
            if( onOff )
            {
                var variableReg = /^[A-Z][A-Z0-9_]*$/;
                if( variableReg.test($(".enviroKey").val()) )
                {
                    var str = '<tr><td><a href="javascript:void(0);" class="enviromentName edit-env-name">'+$(".enviroName").val()+'</a></td>';
                    str += '<td><a href="javascript:void(0);" class="edit-env-key enviromentKey">'+$(".enviroKey").val()+'</a></td>';
                    str += '<td><a href="javascript:void(0);" class="edit-env-val enviromentValue">'+$(".enviroValue").val()+'</a></td>';
                    str += '<td><img class="rubbish" src="/static/www/images/rubbish.png"/></td></tr>';
                    $(str).appendTo(".enviroment");
                    $(".enviroName").val('');
                    $(".enviroKey").val('');
                    $(".enviroValue").val('');
                    $(".addContent").css({"display":"none"});
                    delPort();
                    //修改端口号
                     //修改变量name
                    editCom('.edit-env-name')
                    //修改变量key
                    editCom('.edit-env-key', function(value){
                        var variableReg = /^[A-Z][A-Z0-9_]*$/;
                        if( !variableReg.test(value||'') )
                        {
                            return '变量名由大写字母与数字组成且大写字母开头';
                        }
                    })
                    editCom('.edit-env-val')
                }
                else{
                    swal("变量名由大写字母开头，可以加入数字～～");
                }
            }
            else{
                swal("变量名冲突～～");
            }
        }
        else{
            swal("请输入环境变量");
        }
        //fntabtit();
    });
    $(".noAddEnviroment").on("click",function(){
        $(".addContent").css({"display":"none"});
        $(".enviroKey").val('');
        $(".enviroValue").val('');
        //fntabtit();
    });

    //关闭弹出层
    $("button.cancel").on("click",function(){
        $(".layer-body-bg").css({"display":"none"});
    });
    $(".del").on("click",function(){
        $(".layer-body-bg").css({"display":"none"});
    });
    $(".sureAddDepend").on("click",function(){
        var len = $(".depend input").length;
        for( var i = 0; i<len; i++ )
        {
            if( $(".depend input")[i].checked )
            {
                var appNameLen = $("a.appName").length;
                var onOff = true;
                for( var j = 0; j<appNameLen; j++ )
                {
                    if( $("a.appName")[j].getAttribute("data-serviceId") == $(".depend input")[i].getAttribute("data-id") )
                    {
                        onOff = false;
                        break;
                    }
                }
                if( onOff )
                {
                    var str = '';
                    str += '<tr><td><a href="javascript:void(0);" data-serviceId="'+$(".depend input")[i].getAttribute("data-id")+'" class="appName fn-tips" data-original-title="点击应用名，可以查看依赖该应用的连接方法。">'+$(".depend input")[i].getAttribute("data-action")+'</a></td>';
                    str += '<td><img src="/static/www/images/rubbish.png" class="delLi"/></td></tr>';
                    $(str).appendTo(".applicationName");
                    delLi();
                    appMes();
                    $('.fn-tips').tooltip();
                }
            }
        }
        //fntabtit();
        $(".layer-body-bg").css({"display":"none"});
    });

    //新设持久化目录
    $(".addCata").on("click",function(){
        $(".catalogue").show();
        //$(this).parents(".fn-showblock").find(".fn-tabtit").show();
    })
    $(".catalogueContent").blur(function(){
        if( $(".catalogueContent").val() )
        {
            var len = $(".add_pathName").length;
            for( var i = 0; i<len; i++ )
            {
                var str =  $(".catalogueContent").val();
                if( str == $(".add_pathName").eq(i).parent().find(".pathval").find("span").html() )
                {
                    swal("目录冲突，请重新输入");
                    $(".catalogueContent").val('');
                    break;
                }
            }
        }
        else{
            swal("请输入持久化目录");
            
        }
    })
    $(".catalogueName").blur(function(){
        if( $(".catalogueName").val() )
        {
            var len = $(".add_pathName").length;
            for( var i = 0; i<len; i++ )
            {
                var str =  $(".catalogueName").val();
                if( str == $(".add_pathName").eq(i).html() )
                {
                    swal("名称冲突，请重新输入");
                    $(".catalogueName").val('');
                    break;
                }
            }
        }
        else{
            swal("请输入持久化名称");
           
        }
    })
    $(".addCatalogue").on("click",function(){
        var result = true;
        if( $(".catalogueContent").val() )
        {
            var len = $(".add_pathName").length;
            for( var i = 0; i<len; i++ )
            {
                var str =  $(".catalogueContent").val();
                if( str == $(".add_pathName").eq(i).parent().find(".pathval").find("span").html() )
                {
                    result = false;
                    swal("目录冲突，请重新输入");
                    $(".catalogueContent").val('');
                    break;
                }
            }
        }else{
            result = false;
            swal("请输入目录");
        }
        if( $(".catalogueName").val() )
        {
            var len = $(".add_pathName").length;
            for( var i = 0; i<len; i++ )
            {
                var str =  $(".catalogueName").val();
                if( str == $(".add_pathName").eq(i).html() )
                {
                    result = false;
                    swal("名称冲突，请重新输入");
                    $(".catalogueName").val('');
                    break;
                }
            }
        }else{
            result = false;
            swal("请输入目录");
        }
        if( result ){
            var service_name = $("#service_name").val();
            var str = '<tr><td class="pathval"><span class="fn-tips " data-original-title="使用持久化目录请注意路径关系。">'+$(".catalogueContent").val()+'</span></td>';
            str += '<td class="path_name add_pathName">'+ $(".catalogueName").val() +'</td>';
            str += '<td class="stateVal" data-value="'+ $(".catalogue").find("select option:selected").attr("value") +'">'+ $(".catalogue").find('select option:selected').html() +'</td>';
            str += '<td><img src="/static/www/images/rubbish.png" class="delLi"/></td></tr>';
            $(str).appendTo(".fileBlock");
            $(".catalogue").hide();
            $(".catalogueContent").val("");
            $(".catalogueName").val('');
            delLi();
            $('.fn-tips').tooltip();
        }
    });
    $(".noAddCatalogue").on("click",function(){
        $(".catalogue").hide();
        //fntabtit();
    });
    
    $('#stateless').click(function(){
        var oval= $('#stateless').prop("checked");
        if(oval == true){
            $(".fn-stateless").show();
            $(".fn-state").hide();
            var optionbox = '<option value="share-file">共享存储(文件)</option><option value="memoryfs">内存文件存储</option>';
        }else{
            $(".fn-stateless").hide();
            $(".fn-state").show();
            var optionbox = '<option value="share-file">共享存储(文件)</option><option value="local">本地存储</option><option value="memoryfs">内存文件存储</option>';
        }
        var selectbox = $(".catalogue").find('select');
        $(".catalogue").find('select').empty();
        $(optionbox).appendTo($(selectbox));
    });

    $('#state').click(function(){
        var oval= $('#state').prop("checked");
        if(oval == false){
            $(".fn-stateless").show();
            $(".fn-state").hide();
            var optionbox = '<option value="share-file">共享存储(文件)</option><option value="memoryfs">内存文件存储</option>';
        }else{
            $(".fn-stateless").hide();
            $(".fn-state").show();
            var optionbox = '<option value="share-file">共享存储(文件)</option><option value="local">本地存储</option><option value="memoryfs">内存文件存储</option>';
        }
        var selectbox = $(".catalogue").find('select');
        $(".catalogue").find('select').empty();
        $(optionbox).appendTo($(selectbox));
        
    });
    
    $(".submit").on("click",function(){
        var portLen = $("tbody.port tr").length;
        var portArr = [];
        var service_alias = $("#service_alias").val();
        for( var i = 0; i<portLen; i++ )
        {
            var port_json = {};
            var container_port = $("tbody.port tr").eq(i).find("td").eq(0).children("a").html();
            port_json["container_port"] = container_port
            port_json["protocol"] = $("tbody.port tr").eq(i).find("td").eq(3).find("select option:selected").val();
            // if( port_json["protocol"] == 'HTTP' )
            // {
            //     port_json["protocol"] = 'http';
            // }
            // else if( port_json["protocol"] == '非HTTP' ){
            //     port_json["protocol"] = 'stream';
            // }
            // else{
            //     port_json["protocol"] = 'http';
            // }
            port_json["is_inner_service"] = $("tbody.port tr").eq(i).find("td").eq(1).find("input").prop("checked")?1:0;
            port_json["is_outer_service"] = $("tbody.port tr").eq(i).find("td").eq(2).find("input").prop("checked")?1:0;
            port_json["port_alias"] = service_alias.toUpperCase()+container_port;
            portArr[i] = port_json;
        }
        console.log(JSON.stringify(portArr));

        var appNameLen = $(".appName").length;
        var appNameArr = [];
        for( var n = 0; n<appNameLen; n++ )
        {
            appNameArr.push($(".appName").eq(n).attr("data-serviceid"))
        }
        //console.log(appNameArr);

        var appLen = $(".add_pathName").length;
        var appArr = [];
        for( var j = 0; j<appLen; j++ )
        {
            var app_json = {};
            app_json["volume_name"] = $(".add_pathName").eq(j).html();
            app_json["volume_path"] = $(".add_pathName").eq(j).parent().children(".pathval").find('span').html();
            app_json["volume_type"] = $(".add_pathName").eq(j).parent().find(".stateVal").attr("data-value");
            appArr[j] = app_json;
        }
        //console.log(JSON.stringify(appArr));

        var enviromentLen = $(".enviromentName").length;
        var enviromentArr = [];
        for( var k = 0; k<enviromentLen; k++ )
        {
            var enviroment_json = {};
            enviroment_json["name"] = $("tbody.enviroment tr").eq(k).find("td").eq(0).children("a").html();
            enviroment_json["attr_name"] = $("tbody.enviroment tr").eq(k).find("td").eq(1).children("a").html();
            enviroment_json["attr_value"] = $("tbody.enviroment tr").eq(k).find("td").eq(2).children("a").html();
            enviromentArr[k] = enviroment_json;
        }
        //console.log(JSON.stringify(enviromentArr));

        var otherAppNameLen = $(".otherAppName").length;
        var otherAppNameArr = [];
        for( var m = 0; m<otherAppNameLen; m++ )
        {
            var otherAppName_json = {};
            otherAppName_json["path"] = $(".localdirectoryval").eq(m).html();
            otherAppName_json["id"] = $(".otherAppName").eq(m).attr("data-id");
            console.log(m);
            console.log($(".otherAppName").eq(m).attr("data-id"))
            otherAppNameArr[m] = otherAppName_json;
            console.log(otherAppName_json);
        }


        var  methodval= $('input[name="extend_method"]:checked').val();
        var memory_num = parseInt($("#MemoryText").html());
    
        var service_config = {
            "port_list" : JSON.stringify(portArr),
            "env_list" : JSON.stringify(enviromentArr),
            "volume_list" : JSON.stringify(appArr),
            "mnt_list" : JSON.stringify(otherAppNameArr),
            "depend_list" : JSON.stringify(appNameArr),
            "methodval": methodval,
            "service_min_memory" : memory_num
        }
        //console.log(service_config);
        var service_alias = $("#service_alias").val();
        var tenantName = $("#tenantName").val();

        $.ajax({
            type : "post",
            url : "/apps/" + tenantName + "/"+ service_alias + "/app-setting/",
            data : service_config,
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {
                if (msg["status"] == "success") {
                    window.location.href = "/apps/" + tenantName + "/"+ service_alias + "/app-language/"
                }else if (msg["status"] == "over_memory") {
                    swal("资源已达上限")
                }else{
                    swal("配置失败")
                }
            },
            error : function() {
                swal("系统异常,请重试");
                $("#BtnFirst").attr('disabled', false);
            }
        });

        console.log(service_config);
    });

    //打开弹出层，选择服务依赖
    $(".fn-addDepend").on("click",function(){
        var marleft = $("#main-content").attr("style");
        if(marleft){
            var arrleft = marleft.split(":");
           if(arrleft[1] == " 210px;"){
                $(".layer-body-bg").css({"left":"-210px;"});
            }else{
                $(".layer-body-bg").css({"left":"0px;"});
            }
        }else{
            $(".layer-body-bg").css({"left":"-210px;"});
        }
        $(".applicationMes").css({"display":"none"});
        $(".otherApp").css({"display":"none"});
        $(".depend").css({"display":"block"});
        $(".layer-body-bg").css({"display":"block"});
    })
    //依赖应用相关信息
    appMes();
    function appMes(){
        $(".appname").off('click');
        $(".appName").on("click",function(){
            var service_id = $(this).attr("data-serviceId");
            console.log(service_id);
            getServiceInfo(service_id);
            var marleft = $("#main-content").attr("style");
            if(marleft){
                var arrleft = marleft.split(":");
               if(arrleft[1] == " 210px;"){
                    $(".layer-body-bg").css({"left":"-210px;"});
                }else{
                    $(".layer-body-bg").css({"left":"0px;"});
                }
            }else{
                $(".layer-body-bg").css({"left":"-210px;"});
            }
            $(".applicationMes").css({"display":"block"});
            $(".otherApp").css({"display":"none"});
            $(".depend").css({"display":"none"});
            $(".layer-body-bg").css({"display":"block"});
        });
    }
    function getServiceInfo(service_id){
        var tenant_name = $("#tenantName").val();
        $.ajax({
            type : "post",
            url : "/ajax/" + tenant_name  + "/create/dep-info",
            data : {
                service_id : service_id
            },
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {
                if(msg.ok){
                    $('.appendDiv').html('');
                    var env_map = msg.obj;
                    var service_name = msg.service_name;
                    var info_div = '<div class="port_info">';
                    for (var port in env_map){
                        var envs = env_map[port];
                        if( port != -1 )
                        {
                            info_div += '<p class="layer-tit">'+service_name+'&nbsp;'+port+'&nbsp;端口对外服务环境变量</p>';
                            info_div += '<table class="table"><thead><tr><th>说明</th><th>变量名</th><th>变量值</th></tr></thead><tbody>';
                            var len = envs.length;
                            for( var i = 0; i<len; i++ ){
                                info_div += '<tr><td>'+envs[i].name+'</td>';
                                info_div += '<td>'+envs[i].attr_name+'</td>';
                                info_div += '<td>'+envs[i].attr_value+'</td>'
                                info_div += '</tr>'
                            }
                            //info_div += '</tbody></table>'
                        }
                    }
                    var extra_info = env_map[-1];
                    if (typeof(extra_info)!='undefined' || extra_info !=null){
                        //info_div += '<table class="tab-box lit"><tbody>';
                        for (var i = 0; i< extra_info.length;i++){
                            info_div += '<tr><td>'+extra_info[i].name+'</td>';
                            info_div += '<td>'+extra_info[i].attr_name+'</td>';
                            info_div += '<td>'+extra_info[i].attr_value+'</td>'
                            info_div += '</tr>'
                        }
                    }
                    info_div += '</tbody></table></div>';
                    $(info_div).appendTo('.appendDiv');

                }else{
                    swal(msg.info);
                }
            },
            error : function() {
                swal("系统异常,请重试");
            }
        });
    }

    //挂载其他应用持久化目录
    $(".addOtherApp").on("click",function(){
        var marleft = $("#main-content").attr("style");
        if(marleft){
            var arrleft = marleft.split(":");
           if(arrleft[1] == " 210px;"){
                $(".layer-body-bg").css({"left":"-210px;"});
            }else{
                $(".layer-body-bg").css({"left":"0px;"});
            }
        }else{
            $(".layer-body-bg").css({"left":"-210px;"});
        }
        $(".applicationMes").css({"display":"none"});
        $(".depend").css({"display":"none"});
        $(".otherApp").css({"display":"block"});
        $(".layer-body-bg").css({"display":"block"});
    });

    $("input.addOther").change(function(){
        var onoff = $(this).prop("checked");
        if(onoff == true){
            $(this).parents("tr").find(".fn-localdirectory").removeClass("input80gray").addClass("input80").removeAttr("disabled");
        }else{
            $(this).parents("tr").find(".fn-localdirectory").removeClass("input80").addClass("input80gray").attr({"disabled":"true"}).val("");
        }
    })
    //挂载其他应用服务
    $(".sureAddOther").on("click",function(){
        var len = $("input.addOther").length;
        for( var i = 0; i<len; i++ )
        {
            if( $("input.addOther").eq(i).is(":checked") )
            {
                var length = $(".otherAppName").length;
                var onOff = true;
                for( var j = 0; j<length; j++ )
                {
                    if( $("input.addOther").eq(i).attr("id") == $(".otherAppName").eq(j).attr("data-id") )
                    {
                        onOff = false;
                        break;
                    }
                }

                if($("input.fn-localdirectory").eq(i).val() == ""){
                    swal("选择的服务,本地持久化目录不能为空！");
                    onOff = false;
                    return false;
                }
                
                if( onOff )
                {
                    var str = '<tr><td class=" otherAppval" ><em class="localdirectoryval fn-tips" data-original-title="本地目录">'+ $("input.fn-localdirectory").eq(i).val() +'</em>&nbsp;&nbsp;&nbsp;&nbsp; d<span class="fn-tips" data-original-title="使用持久化目录请注意路径关系。">'+$("input.addOther").eq(i).attr("data-path")+'</span></td>';
                    str += '<td class="path_name otherAppName" data-id="'+$("input.addOther").eq(i).attr("id")+'">挂载自'+$("input.addOther").eq(i).attr("data-name")+'</td>';
                    str += '<td>共享存储(文件)</td>';
                    str += '<td><img src="/static/www/images/rubbish.png" class="delLi"/></td></tr>';
                    $(str).appendTo(".fileBlock");
                    $(".applicationMes").css({"display":"none"});
                    $(".layer-body-bg").css({"display":"none"});
                    delLi();
                    $('.fn-tips').tooltip();
                }
                /*
                if( onOff )
                {
                    var str = '<li>本地目录<em class="localdirectoryval">'+ $("input.fn-localdirectory").eq(i).val() +'</em>&nbsp;&nbsp;持久化目录<em class="fn-tips" data-original-title="使用持久化目录请注意路径关系。">'+$("input.addOther").eq(i).attr("data-path")+'</em>';
                    str += '<span class="path_name otherAppName" data-id="'+$("input.addOther").eq(i).attr("id")+'">挂载自<cite>'+$("input.addOther").eq(i).attr("data-name")+'</cite></span>';
                    str += '<img src="/static/www/images/rubbish.png" class="delLi"/></li>';
                    $(str).appendTo(".fileBlock ul.clearfix");
                    $(".applicationMes").css({"display":"none"});
                    $(".layer-body-bg").css({"display":"none"});
                    delLi();
                    tip();
                }
                */
            }
        }
        //fntabtit();
        $(".applicationMes").css({"display":"none"});
        $(".layer-body-bg").css({"display":"none"});
    });

   


    //外部访问开关
    //checkDetail();
    function checkDetail(){
        $("input.checkDetail").off("click");
        $("input.checkDetail").on("click",function(){
            if( $(this).prop("checked") )
            {
                $(this).parents("tr").find("option.changeOption").remove();
                $(this).parents("tr").find("select").css({"color":"#28cb75"}).removeAttr("disabled");
            }
            else
            {
                var $option = $("<option class='changeOption'></option>")
                $(this).parents("tr").find("select").prepend($option);
                $(this).parents("tr").find("option.changeOption").html("请打开外部访问");
                $(this).parents("tr").find("select").val("请打开外部访问");
                $(this).parents("tr").find("select").css({"color":"#838383"}).attr("disabled",true);
            }
            // if( $(this).parents("tr").find("select").val() == '非HTTP' )
            // {
            //     var len = $("table.tab-box tbody select").length;
            //     var num = 0;
            //     for( var i = 0; i<len; i++ )
            //     {
            //         if( $("table.tab-box tbody input.checkDetail").eq(i).prop("checked") && $("table.tab-box tbody select").eq(i).val() == '非HTTP' )
            //         {
            //             num++;
            //         }
            //     }
            //     if( num >= 2 )
            //     {
            //         swal("访问方式只能有一个非HTTP");
            //         $(this).parents("tr").find("select").val("HTTP");
            //     }
            // }
        });
    }
    //访问方式切换
    selectChange();
    function selectChange(){
        var selectLen = $("table.tab-box select").length;
        for( var j = 0; j<selectLen; j++ )
        {
            $("table.tab-box select").eq(j).attr("index",j);
            $("table.tab-box select").eq(j).change(function(){
                if( $(this).val() == '非HTTP' )
                {
                    var len = $("table.tab-box tbody select").length;
                    for( var i = 0; i<len; i++ )
                    {
                        if( $("table.tab-box tbody input.checkDetail").eq(i).prop("checked") && $("table.tab-box tbody select").eq(i).val() == '非HTTP' && i != $(this).attr("index") )
                        {
                            swal("访问方式只能有一个非HTTP");
                            $(this).val("HTTP");
                            break;
                        }
                    }
                }
            })
        }
    }
    $('.fn-tips').tooltip();
    //检测是否存在
    function matchArr( str,arr ){
        var len = arr.length;
        var onOff = true;
        for( var i = 0; i<len; i++ )
        {
            if( str == arr.eq(i).html() )
            {
                onOff = false;
                break;
            }
        }
        return onOff;
    }
})