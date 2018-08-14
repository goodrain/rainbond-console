var mem_list = [128, 256, 512, 1024, 2048, 4096, 8192];
var node_list = [1, 2, 3, 4, 5, 6, 7,8, 9,10,11,12,13,14,15,16,17,18,19,20];
var trial_list = [7, 30];
function init_html(target, name, memory, ndvalue, trial, curr_price, dep_service_list) {
    target.empty();
    var name_div = $("<div/>").addClass("form-group").appendTo(target);
    $("<div/>").addClass("col-sm-1").appendTo(name_div);
    $("<label/>").addClass("col-sm-2 control-label").html("套餐名称:").appendTo(name_div);
    var name_input = $("<input/>").addClass("form-control fmname")
            .attr("type", "text")
            .attr("placeholder", "请输入中英文或者符号，32个字符以内");
    if (name && name != "") {
        name_input.val(name);
    }
    $("<div/>").addClass("col-sm-6").append(name_input).appendTo(name_div);
    // memory
    var mem_div = $("<div/>").addClass("form-group").appendTo(target);
    $("<div/>").addClass("col-sm-1").appendTo(mem_div);
    $("<label/>").addClass("col-sm-2 control-label").html("内存需求:").appendTo(mem_div);
    var mem_sel = $("<select/>").addClass("form-control fmsecmemory");
    var index = 0;
    for (index in mem_list) {
        var mem = mem_list[index];
        var option = $("<option/>").val(mem).html(mem + "M");
        if (mem == memory) {
            option.attr("selected", "selected");
        }
        option.appendTo(mem_sel);
    }
    $("<div/>").addClass("col-sm-6").append(mem_sel).appendTo(mem_div);
    // node
    var node_div = $("<div/>").addClass("form-group").appendTo(target);
    $("<div/>").addClass("col-sm-1").appendTo(node_div);
    $("<label/>").addClass("col-sm-2 control-label").html("节点要求:").appendTo(node_div);
    var node_sel = $("<select/>").addClass("form-control fmsecnode");
    for (index in node_list) {
        var nd = node_list[index];
        var option = $("<option/>").val(nd).html(nd + "个");
        if (nd == ndvalue) {
            option.attr("selected", "selected");
        }
        option.appendTo(node_sel);
    }
    $("<div/>").addClass("col-sm-6").append(node_sel).appendTo(node_div);
    // time
    var time_div = $("<div/>").addClass("form-group").appendTo(target).css("display","none");
    $("<div/>").addClass("col-sm-1").appendTo(time_div);
    $("<label/>").addClass("col-sm-2 control-label").html("试用时长:").appendTo(time_div);
    var time_sel = $("<select/>").addClass("form-control fmsectime");
    for (index in trial_list) {
        var trlist= trial_list[index];
        var option = $("<option/>").val(trlist).html(trlist + "天");
        if (trlist == trial) {
            option.attr("selected", "selected");
        }
        option.appendTo(time_sel);
    }
    $("<div/>").addClass("col-sm-6").append(time_sel).appendTo(time_div);
    // Price
    var price_div = $("<div/>").addClass("form-group").appendTo(target);
    $("<div/>").addClass("col-sm-1").appendTo(price_div);
    $("<label/>").addClass("col-sm-2 control-label").html("订价:").appendTo(price_div);
    var price_input = $("<input/>").attr("type", "text")
            .attr("placeholder", "请输入不超过9999999元的订价,支持小数点后两位")
            .addClass("form-control fmprice");
    if (curr_price && curr_price != "") {
        price_input.val(curr_price);
    }
    $("<div/>").addClass("col-sm-6").append(price_input).appendTo(price_div);
    $("<div/>").addClass("col-sm-2")
            .append($("<p/>").addClass("unit").html("元/月"))
            .appendTo(price_div);
    // dep_service
    if (typeof(dep_service_list) == "undefined"){
        dep_service_list = eval($("#dep_service_model").val());
    }
    if (dep_service_list.length > 0) {
        for (index in dep_service_list) {
            var dep_service = dep_service_list[index]
            var dep_div = $("<div/>").addClass("form-group").appendTo(target);
            $("<div/>").addClass("col-sm-1").appendTo(dep_div);
            $("<label/>").addClass("col-sm-2 control-label").html("依赖服务:"+dep_service.service_alias).appendTo(dep_div);
            // dep memory
            var dep_mem_sel = $("<select/>")
                    .attr("data-key", dep_service.service_key)
                    .attr("data-version", dep_service.app_version)
                    .attr("data-alias", dep_service.service_alias)
                    .attr("data-memory", "memory")
                    .css("width", "49%").css("display", "inline-block")
                    .addClass("form-control");
            for (index in mem_list) {
                var mem = mem_list[index];
                var option = $("<option/>").val(mem).html(mem + "M");
                if (mem == dep_service.memory) {
                    option.attr("selected", "selected");
                }
                option.appendTo(dep_mem_sel);
            }
            // dep node
            var dep_node_sel = $("<select/>")
                    .attr("data-key", dep_service.service_key)
                    .attr("data-version", dep_service.app_version)
                    .attr("data-alias", dep_service.service_alias)
                    .attr("data-node", "node")
                    .css("width", "49%").css("display", "inline-block")
                    .addClass("form-control");
            for (index in node_list) {
                var nd = node_list[index];
                var option = $("<option/>").val(nd).html(nd + "个");
                if (nd == ndvalue) {
                    option.attr("selected", "selected");
                }
                option.appendTo(dep_node_sel);
            }
            $("<div/>").addClass("col-sm-6")
                    .append(dep_mem_sel)
                    .append(dep_node_sel)
                    .appendTo(dep_div);
        }
    }

    if (name && name != "") {
        // revise button
        var revise_div = $("<div/>").addClass("litlinkbtn").appendTo(target);
        $("<a/>").attr("href", "javascript:;").addClass("litgreenbtn changebtn").html("确定修改").appendTo(revise_div);
        $("<a/>").attr("href", "javascript:;").addClass("litgraybtn rechangebtn").html("取消修改").appendTo(revise_div);
    } else {
        // add button
        var add_div = $("<div/>").addClass("litlinkbtn").appendTo(target);
        $("<a/>").attr("href", "javascript:;").addClass("litgreenbtn").attr("id", "addbtn").html("确定新增").appendTo(add_div);
        $("<a/>").attr("href", "javascript:;").addClass("litgraybtn").attr("id", "readdbtn").html("取消新增").appendTo(add_div);
    }
}
$(function(){
    /*  正则表达式 */
    var regname = /^[a-z\u4E00-\u9FA5\u2000-\u206F]{1,32}$/i; // 套餐名 英文 中文 一般标点符号
    var regprice = /^[1-9]{0,1}[0-9]{0,6}\.?[0-9]{0,2}$/;  //定价
    var tipsArray =['请输入用户名','请输入价格','您输入的套餐名称不符合规则！','您输入的价格不符合规则！','您输入的价格超出范围！','提交失败，请重新添加！','暂时不能修改！','删除失败！','修改成功'];

    // 弹出层
    function tipsFnbox(tipstext){
        var oLayerBox =
                '<div class="litlayer" id="litlayer">' +
                '   <div class="layerbox">' +
                '       <a href="javascript:;" id="closelayer01" class="closeicon"></a>' +
                '       <p class="laytiptext clearfix">' +
                '           <span class="warnicon"></span>' +
                '           <cite>'+ tipstext +'</cite>' +
                '       </p>' +
                '       <a href="javascript:;" class="rewhite" id="closelayer02">重新填写</a>' +
                '   </div>' +
                '</div>';
        $('body').append(oLayerBox);
        $('#closelayer01').click(function(){
            $('#litlayer').remove();
        });
        $('#closelayer02').click(function(){
            $('#litlayer').remove();
        });
    }

    //新增列表
    // list  内容
    function listaddFn(id, TextName,TextMemory,TextNode,TextTime,TextPrice,TextTotal,dep_service_list){
        // var unit = TextMemory > 100 ? "M" : "G";
        var unit = "M";
        var new_li = $("<li/>").attr("data-id", id).appendTo($('#oldlistbox'));
        var new_div = $("<div />").addClass("textlist").appendTo(new_li);
        $("<p/>").append($("<span />").html("套餐名称:"))
                .append($("<cite />").attr("data-value", TextName).html(TextName))
                .appendTo(new_div);
        $("<p/>").append($("<span />").html("内存需求:"))
                .append($("<cite />").attr("data-value", TextMemory).html(TextMemory + unit))
                .appendTo(new_div);
        $("<p/>").append($("<span />").html("节点要求:"))
                .append($("<cite />").attr("data-value", TextNode).html(TextNode + "个"))
                .appendTo(new_div);
        $("<p/>").css("display","none").append($("<span />").html("试用时长:"))
                .append($("<cite />").attr("data-value", TextTime).html(TextTime + "天"))
                .appendTo(new_div);
        $("<p/>").append($("<span />").html("订价:"))
                .append($("<cite />").attr("data-value", TextPrice).html(TextPrice + "元／月"))
                .appendTo(new_div);
        // dep_service
        if (dep_service_list.length > 0) {
            var index = 0;
            for (index in dep_service_list) {
                var dep_service = dep_service_list[index]
                $("<p/>").append($("<span />").html("依赖服务:"+dep_service.service_alias))
                        .append($("<cite />").attr("data-memory", dep_service.memory)
                                .attr("data-node", dep_service.node)
                                .attr("data-version", dep_service.app_version)
                                .attr("data-alias", dep_service.service_alias)
                                .attr("data-key", dep_service.service_key)
                                .attr("data-dep", "dep")
                                .html("内存:"+dep_service.memory+"M 节点: "+dep_service.node+"个"))
                        .appendTo(new_div);
            }
        }
        $("<div/>").addClass("total").append("本套餐在云市的最终价格为")
                .append($("<span/>").attr("data-value", TextTotal).html(TextTotal + "元／月"))
                .appendTo(new_div);
        $("<div/>").addClass("litlinkbtn")
                .append($("<a/>").addClass("litbluebtn resivebtn").attr("href", "javascript:;").text("修改"))
                .append($("<a/>").addClass("litredbtn removebtn").attr("href", "javascript:;").text("删除"))
                .appendTo(new_div);
        $("<div />").addClass("refmbox").appendTo(new_li);
    }

    //添加表单函数
    function FmFnAdd(){
        $('#addbox').addClass('showbox');
        // 初始化添加窗口
        init_html($("#addbox"));
        $('#readdbtn').click(function(){
            $('#addbox').empty().removeClass('showbox');
        });
        ///
        $('#addbtn').click(function(){
            var oPName = $('#addbox .fmname').val();
            var oPMemory = $('#addbox .fmsecmemory').val();
            var oPNode = $('#addbox .fmsecnode').val();
            var oPTime = $('#addbox .fmsectime').val();
            var oPPrice = $('#addbox .fmprice').val();

            var mem_select = {};
            var node_select = {};
            $("select[data-memory]").each(function () {
                var memory = $(this).val();
                var service_key = $(this).attr("data-key");
                var app_version = $(this).attr("data-version");
                var service_alias = $(this).attr("data-alias");
                var key = service_key + "-" + app_version + "-" + service_alias;
                mem_select[key] = {
                    "service_key": service_key,
                    "app_version": app_version,
                    "service_alias": service_alias,
                    "memory": memory
                }
            });
            $("select[data-node]").each(function () {
                var node = $(this).val();
                var service_key = $(this).attr("data-key");
                var app_version = $(this).attr("data-version");
                var service_alias = $(this).attr("data-alias");
                var key = service_key + "-" + app_version + "-" + service_alias;
                node_select[key] = {
                    "service_key": service_key,
                    "app_version": app_version,
                    "service_alias": service_alias,
                    "node": node
                }
            });
            var info_arry = [];
            var depTotal = 0;
            for (var key in mem_select) {
                var tmp_map = mem_select[key];
                if (node_select.hasOwnProperty(key)) {
                    tmp_map["node"] = node_select[key].node
                    info_arry.push(tmp_map);
                    depTotal += (0.069 * 2 * parseInt(tmp_map["memory"]) * parseInt(tmp_map["node"]) / 1024 + 0.0082) * 30 * 24 + 0.8;
                }
            }
            var dep_info = JSON.stringify(info_arry);
            var oPTotal = (0.069 * 2 * parseInt(oPMemory) * parseInt(oPNode) / 1024 + 0.0082) * 30 * 24 + 0.8 + parseFloat(oPPrice);
            oPTotal += depTotal;
            oPTotal = oPTotal.toFixed(2);

            if(oPName == ''){
                tipsFnbox(tipsArray[0]);
                return;
            }else if(oPPrice == ''){
                tipsFnbox(tipsArray[1]);
                return;
            }else if(!regname.test(oPName)){
                tipsFnbox(tipsArray[2]);
                return;
            }else if(!regprice.test(oPPrice)){
                tipsFnbox(tipsArray[3]);
                return;
            }else if(oPPrice > 9999999){
                tipsFnbox(tipsArray[4]);
                return;
            }else{
                var tenant_name = $("#tenant_name").val();
                var service_alias = $("#service_alias").val();
                var service_key = $("#service_key").val();
                var app_version = $("#app_version").val();

                var step4_url = "/apps/" + tenant_name + "/" + service_alias + "/share/package?fr=share";
                $.ajax({
                    url: step4_url,
                    type: "POST",
                    dataType: "json",
                    data: {
                        "action": "add",
                        "name" : oPName,
                        "memory" : oPMemory,
                        "node" : oPNode,
                        "trial" : oPTime,
                        "price" : oPPrice,
                        "total_price" : oPTotal,
                        "service_key": service_key,
                        "app_version": app_version,
                        "dep_info": dep_info
                    },
                    beforeSend : function(xhr, settings) {
                        var csrftoken = $.cookie('csrftoken');
                        xhr.setRequestHeader("X-CSRFToken", csrftoken);
                    },
                    success:function(data){
                        var oData = eval(data);
                        if(oData.code == 200){
                            var info = eval('(' + oData.info + ')');
                            console.log(info);
                            var dep_info = eval(info.dep_info)
                            listaddFn(info.ID, oPName,oPMemory,oPNode,oPTime,oPPrice,info.total_price,dep_info);
                            $('#addbox').empty().removeClass('showbox');
                            $('.resivebtn').click(function(){
                                reFmFn($(this));
                            });
                            ///
                            $('.removebtn').click(function(){
                                $(this).parent().parent().parent('li').remove();
                                var oId = $(this).parent().parent().parent('li').attr('id');
                                var oDataId = $(this).parent().parent().parent('li').attr('data-id');
                                var tenant_name = $("#tenant_name").val();
                                var service_alias = $("#service_alias").val();
                                var step4_url = "/apps/" + tenant_name + "/" + service_alias + "/share/package?fr=share";
                                $.ajax({
                                    url: step4_url,
                                    type: "POST",
                                    dataType: "json",
                                    data: {
                                        "action": "delete",
                                        "id" : oDataId
                                    },
                                    beforeSend : function(xhr, settings) {
                                        var csrftoken = $.cookie('csrftoken');
                                        xhr.setRequestHeader("X-CSRFToken", csrftoken);
                                    },
                                    success:function(data){
                                        $("li[data-id="+oDataId+"]").remove()
                                    },
                                    error: function() {
                                        tipsFnbox("查询失败!");
                                    },
                                    cache: false
                                    // processData: false
                                });
                            });
                            ///
                            //////

                        } else {
                            tipsFnbox(oData.msg);
                        }
                    },
                    error: function() {
                        tipsFnbox("操作失败!");
                    },
                    cache: false
                    // processData: false
                });
            }
        });
        ///
    }


    //点击新增表单
    $('#addbtn').click(function(){
        if(!$('#addbox').hasClass("showbox")){
            FmFnAdd();
        }else{
            return;
        }
    });

    // 修改套餐
    function reFmFn(obtn){
        var outfmbox = obtn.closest('li').find('div.refmbox');
        var inforbox = obtn.closest('div.textlist');
        var oId = obtn.closest('li').attr('id');
        var oDataId = obtn.closest('li').attr('data-id');
        /////
        var oldname = inforbox.find('p:eq(0) cite').attr("data-value");
        var oldmemory = inforbox.find('p:eq(1) cite').attr("data-value");
        var oldnode = inforbox.find('p:eq(2) cite').attr("data-value");
        var oldtime = inforbox.find('p:eq(3) cite').attr("data-value");
        var oldprice = inforbox.find('p:eq(4) cite').attr("data-value");
        var oldtotal = inforbox.find('div.total span').attr("data-value");
        // dep_service_info
        var info_arry = [];
        inforbox.find("cite[data-dep]").each(function () {
            var memory = $(this).attr("data-memory");
            var node = $(this).attr("data-node");
            var app_version = $(this).attr("data-version");
            var service_alias = $(this).attr("data-alias");
            var service_key = $(this).attr("data-key");
            info_arry.push({
                "memory": memory,
                "node": node,
                "app_version": app_version,
                "service_alias": service_alias,
                "service_key": service_key
            });
        });

        inforbox.hide();
        // init html
        init_html(outfmbox, oldname, oldmemory, oldnode, oldtime, oldprice, info_arry);

        $('.changebtn').click(function(){
            var oPName = $(this).closest("div.refmbox").find('input.fmname').val();
            var oPMemory = $(this).closest("div.refmbox").find('select.fmsecmemory').val();
            var unit = "M";
            var oPNode = $(this).closest("div.refmbox").find('select.fmsecnode').val();
            var oPTime = $(this).closest("div.refmbox").find('select.fmsectime').val();
            var oPPrice = $(this).closest("div.refmbox").find('input.fmprice').val();
            var oPTotal = (0.069 * 2 * parseInt(oPMemory) * parseInt(oPNode) / 1024 + 0.0082) * 30 * 24 + 0.8 + parseFloat(oPPrice);
            //依赖服务资源
            var mem_select = {};
            var node_select = {};
            $(this).closest("div.refmbox").find("select[data-memory]").each(function () {
                var memory = $(this).val();
                var service_key = $(this).attr("data-key");
                var app_version = $(this).attr("data-version");
                var service_alias = $(this).attr("data-alias");
                var key = service_key + "-" + app_version + "-" + service_alias;
                mem_select[key] = {
                    "service_key": service_key,
                    "app_version": app_version,
                    "service_alias": service_alias,
                    "memory": memory
                }
            });
            $(this).closest("div.refmbox").find("select[data-node]").each(function () {
                var node = $(this).val();
                var service_key = $(this).attr("data-key");
                var app_version = $(this).attr("data-version");
                var service_alias = $(this).attr("data-alias");
                var key = service_key + "-" + app_version + "-" + service_alias;
                node_select[key] = {
                    "service_key": service_key,
                    "app_version": app_version,
                    "service_alias": service_alias,
                    "node": node
                }
            });
            var info_arry = [];
            var depTotal = 0;
            for (var key in mem_select) {
                var tmp_map = mem_select[key];
                if (node_select.hasOwnProperty(key)) {
                    tmp_map["node"] = node_select[key].node;
                    info_arry.push(tmp_map);
                    depTotal += (0.069 * 2 * parseInt(tmp_map["memory"]) * parseInt(tmp_map["node"]) / 1024 + 0.0082) * 30 * 24 + 0.8;
                }
            }
            // 添加依赖资源
            oPTotal += depTotal;
            oPTotal = oPTotal.toFixed(2);

            if(oPName == ''){
                tipsFnbox(tipsArray[0]);
                return;
            }else if(oPPrice == ''){
                tipsFnbox(tipsArray[1]);
                return;
            }else if(!regname.test(oPName)){
                tipsFnbox(tipsArray[2]);
                return;
            }else if(!regprice.test(oPPrice)){
                tipsFnbox(tipsArray[3]);
                return;
            }else if(oPPrice > 9999999){
                tipsFnbox(tipsArray[4]);
                return;
            }else{
                inforbox.find('p:eq(0) cite').html(oPName);
                inforbox.find('p:eq(1) cite').html(oPMemory + unit);
                inforbox.find('p:eq(2) cite').html(oPNode + '个');
                inforbox.find('p:eq(3) cite').html(oPTime + '天');
                inforbox.find('p:eq(4) cite').html(oPPrice + '元／月');
                inforbox.find('div.total span').html(oPTotal + '元／月');
                // 更新页面
                inforbox.find("cite[data-dep]").each(function () {
                    var app_version = $(this).attr("data-version");
                    var service_alias = $(this).attr("data-alias");
                    var service_key = $(this).attr("data-key");
                    var key = service_key + "-" + app_version + "-" + service_alias;
                    var new_data = mem_select[key]
                    $(this).attr("data-memory", new_data.memory);
                    $(this).attr("data-node", new_data.node);
                    $(this).html("内存: "+new_data.memory + "M 节点: " + new_data.node + "个");
                });
            }
            var tenant_name = $("#tenant_name").val();
            var service_alias = $("#service_alias").val();
            var service_key = $("#service_key").val();
            var app_version = $("#app_version").val();
            var step4_url = "/apps/" + tenant_name + "/" + service_alias + "/share/package?fr=share";
            $.ajax({
                url: step4_url,
                type: "POST",
                dataType: "json",
                data: {
                    "action" : "update",
                    "id" : oDataId,
                    "name" : oPName,
                    "memory" : oPMemory,
                    "node" : oPNode,
                    "trial" : oPTime,
                    "price" : oPPrice,
                    "total_price" : oPTotal,
                    "service_key": service_key,
                    "app_version": app_version,
                    "dep_info": JSON.stringify(info_arry)
                },
                beforeSend : function(xhr, settings) {
                    var csrftoken = $.cookie('csrftoken');
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                },
                success:function(data){
                    var oData = eval(data);
                    if(oData.code == 200){
                        inforbox.show();
                        outfmbox.empty();
                    } else {
                        tipsFnbox(oData.msg);
                    }
                },
                error: function() {
                    tipsFnbox("查询失败!");
                },
                cache: false
                // processData: false
            });
        });
        $('.rechangebtn').click(function(){
            outfmbox.empty();
            inforbox.show();
        });
    }

   
    //点击修改
    $('.resivebtn').click(function(){
        reFmFn($(this));
    });
   
    $('.removebtn').click(function(){
        //$(this).parent().parent().parent('li').remove();
        var oId = $(this).parent().parent().parent('li').attr('id');
        var oDataId = $(this).parent().parent().parent('li').attr('data-id');
        var domli = $(this).parent().parent().parent('li');
        /////
        var tenant_name = $("#tenant_name").val();
        var service_alias = $("#service_alias").val();
        var step4_url = "/apps/" + tenant_name + "/" + service_alias + "/share/package?fr=share";
        $.ajax({
            url: step4_url,
            type: "POST",
            dataType: "json",
            data: {
                "action": "delete",
                "id" : oDataId
            },
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success:function(data){
                $("li[data-id="+oDataId+"]").remove()
            },
            error: function() {
                tipsFnbox(tipsArray[9]);
            },
            cache: false
            // processData: false
        });
        //////
    });


    $("#subbtn").bind("click", function () {
        $("#package_form").submit();
    });

});