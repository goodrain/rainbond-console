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

    var service_name = $("#service_name").val();
    var regstr = /\s{2,}/;
    var main_url = window.location.href;
    var new_url = main_url.split('&params=');
    var base64str = new_url[new_url.length-1];
    //console.log(base64str);
    //
    var base64DecodeChars = new Array(  
        -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  
        -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,  
        -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 62, -1, -1, -1, 63,  
        52, 53, 54, 55, 56, 57, 58, 59, 60, 61, -1, -1, -1, -1, -1, -1,  
        -1,  0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14,  
        15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, -1, -1, -1, -1, -1,  
        -1, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,  
        41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, -1, -1, -1, -1, -1);  
     
   
    function base64decode(str) {  
        var c1, c2, c3, c4;  
        var i, len, out;  
      
        len = str.length;  
        i = 0;  
        out = "";  
        while(i < len) {  
        /* c1 */  
        do {  
            c1 = base64DecodeChars[str.charCodeAt(i++) & 0xff];  
        } while(i < len && c1 == -1);  
        if(c1 == -1)  
            break;  
      
        /* c2 */  
        do {  
            c2 = base64DecodeChars[str.charCodeAt(i++) & 0xff];  
        } while(i < len && c2 == -1);  
        if(c2 == -1)  
            break;  
      
        out += String.fromCharCode((c1 << 2) | ((c2 & 0x30) >> 4));  
      
        /* c3 */  
        do {  
            c3 = str.charCodeAt(i++) & 0xff;  
            if(c3 == 61)  
            return out;  
            c3 = base64DecodeChars[c3];  
        } while(i < len && c3 == -1);  
        if(c3 == -1)  
            break;  
      
        out += String.fromCharCode(((c2 & 0XF) << 4) | ((c3 & 0x3C) >> 2));  
      
        /* c4 */  
        do {  
            c4 = str.charCodeAt(i++) & 0xff;  
            if(c4 == 61)  
            return out;  
            c4 = base64DecodeChars[c4];  
        } while(i < len && c4 == -1);  
        if(c4 == -1)  
            break;  
        out += String.fromCharCode(((c3 & 0x03) << 6) | c4);  
        }  
        return out;  
    }  
    
    function utf8to16(str) {  
        var out, i, len, c;  
        var char2, char3;  
      
        out = "";  
        len = str.length;  
        i = 0;  
        while(i < len) {  
        c = str.charCodeAt(i++);  
        switch(c >> 4)  
        {   
          case 0: case 1: case 2: case 3: case 4: case 5: case 6: case 7:  
            // 0xxxxxxx  
            out += str.charAt(i-1);  
            break;  
          case 12: case 13:  
            // 110x xxxx   10xx xxxx  
            char2 = str.charCodeAt(i++);  
            out += String.fromCharCode(((c & 0x1F) << 6) | (char2 & 0x3F));  
            break;  
          case 14:  
            // 1110 xxxx  10xx xxxx  10xx xxxx  
            char2 = str.charCodeAt(i++);  
            char3 = str.charCodeAt(i++);  
            out += String.fromCharCode(((c & 0x0F) << 12) |  
                           ((char2 & 0x3F) << 6) |  
                           ((char3 & 0x3F) << 0));  
            break;  
        }  
        } 
        return out;  
    } 
    var str_url = utf8to16(base64decode(base64str)); 
    //console.log(str_url);
    //console.log('++++1111111++++');
    var str_url_Arr = str_url.split("^_^");
    //console.log(str_url_Arr);
    //console.log('++++222222++++')
    var json_url_Arr_key = [];
    var json_url_Arr_value = [];
    for(var i=0;i<str_url_Arr.length;i++){
        //var url_json = {};
        var json_sin_arr =[];
        json_sin_arr = str_url_Arr[i].split("==");
        //url_json[json_sin_arr[0]] = json_sin_arr[1];
        json_url_Arr_key.push(json_sin_arr[0]);
        json_url_Arr_value.push(json_sin_arr[1]);
    }
    //console.log(json_url_Arr_key);
    //console.log(json_url_Arr_value);
    
    var old_arr_link = [];
    var old_arr_id=[];
    $(".cho-text").each(function(){
        old_arr_link.push($(this).html());
        old_arr_id.push($(this).attr("for"));
    });
    //console.log(old_arr_link);
    //console.log(old_arr_id);

    for(var i=0;i<json_url_Arr_key.length;i++){
        //端口
        if(json_url_Arr_key[i] == "-p" || json_url_Arr_key[i] == "--publish" ||json_url_Arr_key[i] == "--expose"){
            var portnum = json_url_Arr_value[i];
            var oTr = '<tr><td><a href="javascript:void(0);" class="portNum edit-port fn-tips" data-original-title="当前应用提供服务的端口号。">'+ portnum +'</a></td>';
            oTr += '<td><label class="checkbox fn-tips" data-original-title="打开对外服务，其他应用即可访问当前应用。"><input type="checkbox" name="" value="" id="'+ portnum +'inner" /><span class="check-bg" for="'+ portnum +'inner"></span></label></td>';
            oTr += '<td><label class="checkbox fn-tips" data-original-title="打开外部访问，用户即可通过网络访问当前应用。"><input class="checkDetail" type="checkbox" name="" value="" id="'+ portnum +'outer" checked="true" /><span class="check-bg" for="'+ portnum +'outer"></span></label></td><td>';
            oTr += '<select class="fn-tips" data-original-title="请设定用户的访问协议。" data-port-http="'+ portnum +'http">';
            oTr += '<option value="http">http</option><option value="tcp">tcp</option><option value="udp">udp</option><option value="mysql">mysql</option>';
            oTr += '</select></td><td><img class="rubbish" src="/static/www/images/rubbish.png"/></td></tr>';
            $(oTr).appendTo(".port");
        }
        //服务依赖
        if(json_url_Arr_key[i] == "--link"){
            var linkstr = json_url_Arr_value[i];
            var num = 0;
            for(var m=0; m<old_arr_link.length; m++){
                if(linkstr == old_arr_link[m]){
                    num += 1;
                }
            }
            for(var k=0;k<old_arr_link.length;k++){
                if(linkstr == old_arr_link[k] && num == 1){
                    var str = '';
                    str += '<li><a href="javascript:void(0);" data-serviceId="'+ old_arr_id[k]+'" class="appName fn-tips" data-original-title="点击应用名，可以查看依赖该应用的连接方法。">'+ old_arr_link[k] +'</a>';
                    str += '<img src="/static/www/images/rubbish.png" class="delLi"/></li>';
                    $(str).appendTo(".applicationName");
                }
            }
        }
        //环境变量
        if(json_url_Arr_key[i] == "-e" || json_url_Arr_key[i] == "--env"){
            var estr = json_url_Arr_value[i];
            var estr_arr =[];
            estr_arr = estr.split("=");
            var str = '<tr><td><a href="javascript:void(0);" class="enviromentName edit-env-name">'+ estr_arr[0] +'</a></td>';
            str += '<td><a href="javascript:void(0);" class="edit-env-key enviromentKey">'+estr_arr[0]+'</a></td>';
            str += '<td><a href="javascript:void(0);" class="edit-env-val enviromentValue">'+estr_arr[1]+'</a></td>';
            str += '<td><img class="rubbish" src="/static/www/images/rubbish.png"/></td></tr>';
            $(str).appendTo(".enviroment");
        }
        //文件存储
        if(json_url_Arr_key[i] == "-v" || json_url_Arr_key[i] == "--volume"){
            var filestr =  json_url_Arr_value[i];
            var fstr = '<tr><td class="fn-tips pathval" data-original-title="使用持久化目录请注意路径关系。">'+ filestr +'</td><td class="path_name add_pathName">当前应用'+  service_name +'自有</td><td class="stateVal" data-value="share-file">共享存储(文件)</td><td><img src="/static/www/images/rubbish.png" class="delLi"></td></tr>';
            $(fstr).appendTo(".fileBlock");
        }
        //镜像地址
        if(json_url_Arr_key[i] == "image"){
            var imgstr = json_url_Arr_value[i];
            var istr = '<a href="javascript:void(0);" class="portNum edit-mirroraddress">'+ imgstr +'</a>'; 
            $(istr).appendTo(".fn-mirroraddress div");
        }
        //容器运行命令
        if(json_url_Arr_key[i] == "run_exec"){
            var runstr = json_url_Arr_value[i];
            var rstr = '<textarea rows="4" style="width:80%;">'+ runstr +'</textarea>'; 
            $(rstr).appendTo(".fn-run-command div");
        }
    }
    
    
    //
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
        // $(this).parents(".fn-showblock").find(".fn-tabtit").show();
        $(".checkTip").css({"display":"none"});
        $(".addPort").css({"display":"table-row"});
    });
    $(".add_port").blur(function(){
       

        var portNum = parseInt($(".add_port").val());
        if( portNum>0 && portNum<65536 )
        {
            $(this).parents('tr').find('p.checkTip').css({"display":"none"});
        }
        else{
            $(this).parents('tr').find('p.checkTip').css({"display":"block"});
        }
    })
    //确定添加端口号
    $(".fn-add").on("click",function(){
        var portNum = parseInt($(".add_port").val());
        if( portNum>0 && portNum<65536 )
        {
            var addOnoff = matchArr(portNum,$(".portNum"));
            if( addOnoff )
            {
                var arr = ['http','tcp','udp','mysql'];
                var oTr = '<tr><td><a href="javascript:void(0);" class="portNum edit-port fn-tips" data-original-title="当前应用提供服务的端口号。">'+$(".add_port").val()+'</a></td>';
                if( $("#addInner").prop("checked") == true )
                {
                    oTr += '<td><label class="checkbox fn-tips" data-original-title="打开对外服务，其他应用即可访问当前应用。"><input type="checkbox" name="" value="" id="'+$(".add_port").val()+'inner" checked="true" /><span class="check-bg" for="'+$(".add_port").val()+'inner"></span></label></td>';
                }
                else{
                    oTr += '<td><label class="checkbox fn-tips" data-original-title="打开对外服务，其他应用即可访问当前应用。"><input type="checkbox" name="" value="" id="'+$(".add_port").val()+'inner" /><span class="check-bg" for="'+$(".add_port").val()+'inner"></span></label></td>';
                }
                if( $("#addOuter").prop("checked") == true )
                {
                    oTr += '<td><label class="checkbox fn-tips"  data-original-title="打开外部访问，用户即可通过网络访问当前应用。"><input class="checkDetail" type="checkbox" name="" value="" id="'+$(".add_port").val()+'outer" checked="true" /><span class="check-bg" for="'+$(".add_port").val()+'outer"></span></label></td><td>';
                    oTr += '<select style="" class="fn-tips"  data-original-title="请设定用户的访问协议。" data-port-http="'+$(".add_port").val()+'http">';
                }
                else{
                    oTr += '<td><label class="checkbox fn-tips"  data-original-title="打开外部访问，用户即可通过网络访问当前应用。"><input class="checkDetail" type="checkbox" name="" value="" id="'+$(".add_port").val()+'outer" /><span class="check-bg" for="'+$(".add_port").val()+'outer"></span></div></td><td>';
                    oTr += '<select style="" class="fn-tips"  data-original-title="请设定用户的访问协议。" data-port-http="'+$(".add_port").val()+'http">';
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
                     if( !(value>0 && value<65536) ){
                        return "端口范围为1-65535";
                     }

                     if (!$.trim(value)) {
                        return '不能为空';
                     }
                });
                // fntabtit();
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
        $(".add_port").val("");
        // fntabtit();
    });
    //取消端口号的添加
    $(".fn-noAdd").on("click",function(){
        $(".addPort").css({"display":"none"});
        // fntabtit();
    });
    delPort();
    //删除端口号与环境变量
    function delPort(){
        $("img.rubbish").off("click");
        $("img.rubbish").on("click",function(){
            $(this).parents("tr").remove();
            // fntabtit();
        })
    }
    delLi();
    //删除依赖与目录
    function delLi(){
        $("img.delLi").off("click");
        $("img.delLi").on("click",function(){
            $(this).parents("tr").remove();
            // fntabtit();
        })
    }
    //修改端口号
    editCom('.edit-port', function(value){
         if( !(value>0 && value<65536) ){
            return "端口范围为1-65535";
         }

         if (!$.trim(value)) {
            return '不能为空';
         }
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
    //修改镜像地址
    editCom('.edit-mirroraddress', function(value){
        if(!$.trim(value)){
            return "请输入镜像地址";
        }
    })

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

                if (!$.trim(value)) {
                    return '不能为空';
                }
                
                if(validate){
                    return validate(value)
                }
            }
        });
    }
    //显示添加环境变量内容
    $(".openAddEnviroment").on("click",function(){
        $(".addContent").css({"display":"table-row"});
        // $(this).parents(".fn-showblock").find(".fn-tabtit").show();
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
    $(".catalogueName").blur(function(){
        if( $(".catalogueName").val() )
        {
            $(this).parent().find(".checkTip").css({"display":"none"});
        }
        else{
            $(this).parent().find(".checkTip").html("请输入持久化名称");
            $(this).parent().find(".checkTip").css({"display":"inline-block"});
        }
    })
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
        // fntabtit();
        $('.fn-tips').tooltip();
    });
    $(".noAddEnviroment").on("click",function(){
        $(".addContent").css({"display":"none"});
        $(".enviroKey").val('');
        $(".enviroValue").val('');
        // fntabtit();
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
                    if( $("a.appName")[j].getAttribute("data-serviceid") == $(".depend input")[i].getAttribute("data-id") )
                    {
                        onOff = false;
                        break;
                    }
                }
                if( onOff )
                {
                    var str = '';
                    str += '<tr><td data-serviceId="'+$(".depend input")[i].getAttribute("data-serviceId")+'" class="appName fn-tips" data-original-title="点击应用名，可以查看依赖该应用的连接方法。">'+$(".depend input")[i].getAttribute("data-action")+'</td><td>';
                    str += '<img src="/static/www/images/rubbish.png" class="delLi"/></td></tr>';
                    $(str).appendTo(".applicationName");
                    delLi();
                    
                    appMes();
                }
            }
        }
        $(".layer-body-bg").css({"display":"none"});
    });

    //新设持久化目录
    $(".addCata").on("click",function(){
        $(".catalogue").css({"display":"table-row"});
        // $(this).parents(".fn-showblock").find(".fn-tabtit").show();
    })
    $(".catalogueContent").blur(function(){
        if( $(".catalogueContent").val() )
        {
            var len = $(".add_pathName").length;
            for( var i = 0; i<len; i++ )
            {
                var str =  $(".catalogueContent").val();
                if( str == $(".add_pathName").eq(i).parent().find("td.pathval").html() )
                {
                    result = false;
                    swal("目录冲突，请重新输入");
                    $(".catalogueContent").val('');
                    return false;
                }
            }
        }
        else{
            swal("请输入目录");
            
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
                if( str == $(".add_pathName").eq(i).parent().find("td.pathval").html() )
                {
                    result = false;
                    swal("目录冲突，请重新输入");
                    $(".catalogueContent").val('');
                    break;
                    return false;
                }
            }
        }else{
            result = false;
            swal("请输入目录");
            return false;
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
                    $(this).parent().find(".checkTip").html("名称冲突，请重新输入");
                    $(".catalogueName").val('');
                    break;
                    return false;
                }
            }
        }else{
            swal("请输入名称");
            return false;
        }
        
        if( result )
        {
                var service_name = $("#service_name").val();
                var str = '<tr><td class="fn-tips pathval" data-original-title="使用持久化目录请注意路径关系。">'+$(".catalogueContent").val()+'</td>';
                str += '<td class="path_name add_pathName">'+ $(".catalogueName").val() +'</td>';
                str += '<td data-value="'+$(".catalogue").find("select option:selected").attr("value")+'" class="stateVal">'+ $(".catalogue").find('select option:selected').html() +'</td>';
                str += '<td><img src="/static/www/images/rubbish.png" class="delLi"/></td></tr>';
                $(str).appendTo(".fileBlock");
                $(".catalogue").css({"display":"none"});
                $(".catalogueContent").val("");
                $(".catalogueName").val('');
                delLi();
        }
        // fntabtit();
        $('.fn-tips').tooltip();
    });
    $(".noAddCatalogue").on("click",function(){
        $(".catalogue").css({"display":"none"});
        // fntabtit();
    });
   
    $('#stateless').change(function(){
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
    
    $('#state').change(function(){
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

    // new 内存start 
    $("#MemoryRange a").click(function(){
        $("#MemoryRange a").removeClass("sed");
        $(this).addClass("sed");
        var memoryVal = $(this).html();
        $("#MemoryText").html(memoryVal);
    });
    // new 内存start 


    $(".submit").on("click",function(){
        var start_cmd_str = $(".fn-run-command").find("textarea").prop("value");
        if(regstr.test(start_cmd_str)){
            swal("您输入的命令有多个空格！");
            return false;
        }
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
            app_json["volume_path"] = $(".add_pathName").eq(j).parent().children(".pathval").html();
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

        var otherAppidLen = $(".otherAppName").length;
        var otherAppidArr = [];
        for( var m = 0; m<otherAppidLen; m++ )
        {

            var otherAppid_json = {};

            //otherAppid_json["name"] = $(".otherAppid").eq(m).html();
            otherAppid_json["path"] = $(".localdirectoryval").eq(m).html();
            otherAppid_json["id"] = $(".otherAppName").eq(m).attr("data-id");
            //otherAppidArr[m] = otherAppid_json;

            //var dataid = $(".otherAppid").eq(m).attr("data-id");
            otherAppidArr[m] = otherAppid_json;
        }
        var  service_id = $("#service_id").val();
        var  methodval= $('input[name="extend_method"]:checked').val();
        var memory_num = parseInt($("#MemoryText").html());
        
        var service_config = {
            "service_id" : service_id,
            "port_list" : JSON.stringify(portArr),
            "env_list" : JSON.stringify(enviromentArr),
            "volume_list" : JSON.stringify(appArr),
            "mnt_list" : JSON.stringify(otherAppidArr),
            "depend_list" : JSON.stringify(appNameArr),
            "image_url" : $(".fn-mirroraddress").find("a").html(),
            "start_cmd" : $(".fn-run-command").find("textarea").prop("value"),
            "methodval": methodval,
            "service_min_memory" : memory_num
        }

        var tenantName = $("#tenantName").val();

        $.ajax({
            type : "post",
            url : "/apps/"+tenantName+"/image-params/",
            data : service_config,
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(msg) {
                if (msg["status"] == "success") {
                    var service_alias = msg["service_alias"];
                    window.location.href = "/apps/" + tenantName + "/" + service_alias + "/detail/";
                }else if(msg["status"] == "notfound"){
                    swal("服务不存在");
                }else if(msg["status"] == "over_memory") {
                    swal("资源已达上限");
                }else{
                    swal("配置失败");
                }
            },
            error : function() {
                swal("系统异常,请重试");
                $(".submit").attr('disabled', false);
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
                            info_div += '<p class="layer-tit-lit">'+service_name+'&nbsp;'+port+'&nbsp;端口对外服务环境变量</p>';
                            info_div += '<table class="tab-box lit"><thead><tr><th>说明</th><th>变量名</th><th>变量值</th></tr></thead><tbody>';
                            var len = envs.length;
                            for( var i = 0; i<len; i++ ){
                                info_div += '<tr><td>'+envs[i].name+'</td>';
                                info_div += '<td>'+envs[i].attr_name+'</td>';
                                info_div += '<td>'+envs[i].attr_value+'</td>'
                                info_div += '</tr>'
                            }
                        }
                    }
                    var extra_info = env_map[-1];
                    if (typeof(extra_info)!='undefined' || extra_info !=null){
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
        // fntabtit();
        $('.fn-tips').tooltip();
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
                    var str = '<tr><td class=" otherAppval" ><em class="localdirectoryval fn-tips" data-original-title="本地目录">'+ $("input.fn-localdirectory").eq(i).val() +'</em>&nbsp;&nbsp;&nbsp;&nbsp;<span class="fn-tips" data-original-title="使用持久化目录请注意路径关系。">'+$("input.addOther").eq(i).attr("data-path")+'</span></td>';
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
                    var str = '<li><em class="fn-tips" data-original-title="使用持久化目录请注意路径关系。">'+$("input.addOther").eq(i).attr("data-path")+'</em>';
                    str += '<span class="path_name otherAppName" data-id="'+$("input.addOther").eq(i).attr("id")+'"><cite>挂载自</cite>'+$("input.addOther").eq(i).attr("data-name")+'</span>';
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
        // fntabtit();
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
    // fntabtit();
    $('.fn-tips').tooltip();
    //访问方式切换
    selectChange();
    function selectChange(){
        var selectLen = $("table.tabport select").length;
        for( var j = 0; j<selectLen; j++ )
        {
            $("table.tabport select").eq(j).attr("index",j);
            $("table.tabport select").eq(j).change(function(){
                if( $(this).val() == '非HTTP' )
                {
                    var len = $("table.tabport tbody select").length;
                    for( var i = 0; i<len; i++ )
                    {
                        if( $("table.tabport tbody input.checkDetail").eq(i).prop("checked") && $("table.tabport tbody select").eq(i).val() == '非HTTP' && i != $(this).attr("index") )
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