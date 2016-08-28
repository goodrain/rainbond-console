$(function(){
    /*  正则表达式 */
    var regname = /^[a-z\u4E00-\u9FA5\u2000-\u206F]{1,32}$/i; // 套餐名 英文 中文 一般标点符号
    var regprice = /^[1-9]{0,1}[0-9]{0,6}\.?[0-9]{0,2}$/;  //定价
    var tipsArray =['请输入用户名','请输入价格','您输入的应用名称不符合规则！','您输入的价格不符合规则！','您输入的价格超出范围！','提交失败，请重新添加！','暂时不能修改！','删除失败！','修改成功'];
    
    // 表单内容
    var oFmName = '<div class="form-group"><div class="col-sm-1"></div><label class="col-sm-2 control-label">应用名称:</label><div class="col-sm-6"><input type="text" class="form-control fmname" placeholder="请输入中英文或者符号，32个字符以内"></div></div>';
    var oFmMemory = '<div class="form-group"><div class="col-sm-1"></div><label class="col-sm-2 control-label">内存需求:</label><div class="col-sm-6"><select class="form-control fmsecmemory"><option value="128">128M</option><option value="256">256M</option><option value="512">512M</option><option value="1024">1G</option><option value="2048">2G</option><option value="4096">4G</option><option value="8192">8G</option></select></div></div>';
    var oFmNode = '<div class="form-group"><div class="col-sm-1"></div><label class="col-sm-2 control-label">节点要求:</label><div class="col-sm-6"><select class="form-control fmsecnode"><option value="1">1个</option><option value="2">2个</option><option value="3">3个</option><option value="4">4个</option><option value="5">5个</option><option value="6">6个</option><option value="7">7个</option><option value="8">8个</option><option value="9">9个</option><option value="10">10个</option><option value="11">11个</option><option value="12">12个</option><option value="13">13个</option><option value="14">14个</option><option value="15">15个</option><option value="16">16个</option><option value="17">17个</option><option value="18">18个</option><option value="19">19个</option><option value="20">20个</option></select></div></div>';
    var oFmTime = '<div class="form-group"><div class="col-sm-1"></div><label class="col-sm-2 control-label">试用时长:</label><div class="col-sm-6"><select class="form-control fmsectime"><option value="7">7天</option><option value="30">30天</option></select></div></div>';
    var oFmPrice = '<div class="form-group"><div class="col-sm-1"></div><label  class="col-sm-2 control-label">订价:</label><div class="col-sm-6"><input type="text" class="form-control fmprice"  placeholder="请输入不超过9999999元的订价，支持小数点后两位"></div><div class="col-sm-2"><p class="unit">元/月</p></div></div>';
    var oFmAddBtn = '<div class="litlinkbtn"><a href="javascript:;" class="litgreenbtn" id="addbtn">确定新增</a><a href="javascript:;" class="litgraybtn" id="readdbtn">取消新增</a></div>';
    var oFmReviseBtn = '<div class="litlinkbtn"><a href="javascript:;" class="litgreenbtn changebtn">确定修改</a><a href="javascript:;" class="litgraybtn rechangebtn" >取消修改</a></div>';

    // 弹出层
    function tipsFnbox(tipstext){
        var oLayerBox = '<div class="litlayer" id="litlayer"><div class="layerbox"><a href="javascript:;" id="closelayer01" class="closeicon"></a><p class="laytiptext clearfix"><span class="warnicon"></span><cite>'+ tipstext +'</cite></p><a href="javascript:;" class="rewhite" id="closelayer02">重新填写</a></div></div>';
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
    function listaddFn(id, TextName,TextMemory,TextNode,TextTime,TextPrice,TextTotal){
    	// var unit = TextMemory > 100 ? "M" : "G";
        var unit = "M";
        var old_memory = TextMemory
        var value = TextMemory/1024;
        if (value >= 1) {
            TextMemory = value;
            unit = "G"
        }
        var new_li = $("<li/>").attr("data-id", id).appendTo($('#oldlistbox'));
        var new_div = $("<div />").addClass("textlist").appendTo(new_li);
        $("<p/>").append($("<span />").html("应用名称:"))
                .append($("<cite />").attr("data-value", TextName).html(TextName))
                .appendTo(new_div);
        $("<p/>").append($("<span />").html("内存需求:"))
                .append($("<cite />").attr("data-value", old_memory).html(TextMemory + unit))
                .appendTo(new_div);
        $("<p/>").append($("<span />").html("节点要求:"))
                .append($("<cite />").attr("data-value", TextNode).html(TextNode + "个"))
                .appendTo(new_div);
        $("<p/>").append($("<span />").html("试用时长:"))
                .append($("<cite />").attr("data-value", TextTime).html(TextTime + "天"))
                .appendTo(new_div);
        $("<p/>").append($("<span />").html("订价:"))
                .append($("<cite />").attr("data-value", TextPrice).html(TextPrice + "元／月"))
                .appendTo(new_div);
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
        $(oFmName).appendTo($('#addbox'));
        $(oFmMemory).appendTo($('#addbox'));
        $(oFmNode).appendTo($('#addbox'));
        $(oFmTime).appendTo($('#addbox'));
        $(oFmPrice).appendTo($('#addbox'));
        $(oFmAddBtn).appendTo($('#addbox'));
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
            var oPTotal = (0.069 * 2 * parseInt(oPMemory) * parseInt(oPNode) / 1024 + 0.0082) * 30 * 24 + 0.8 + parseFloat(oPPrice);
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
                var step4_url = "/apps/" + tenant_name + "/" + service_alias + "/share/package";
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
                        "app_version": app_version
                    },
		            beforeSend : function(xhr, settings) {
		                var csrftoken = $.cookie('csrftoken');
		                xhr.setRequestHeader("X-CSRFToken", csrftoken);
		            },
		            success:function(data){
		                var oData = eval(data);
		                if(oData.code == 200){
                            var info = eval('(' + oData.info + ')');
                            listaddFn(info.ID, oPName,oPMemory,oPNode,oPTime,oPPrice,info.total_price);
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
                                var step4_url = "/apps/" + tenant_name + "/" + service_alias + "/share/package";
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

    ///// 操作list

    // 添加表单
    function reFmFn(obtn){
    	var outfmbox = obtn.parent().parent().parent('li').find('div.refmbox');
        var inforbox = obtn.parent().parent('div.textlist');
        var oId = obtn.parent().parent().parent('li').attr('id');
        var oDataId = obtn.parent().parent().parent('li').attr('data-id');
    	/////
        var oldname = inforbox.find('p:eq(0) cite').attr("data-value");
        var oldmemory = inforbox.find('p:eq(1) cite').attr("data-value");
        var oldnode = inforbox.find('p:eq(2) cite').attr("data-value");
        var oldtime = inforbox.find('p:eq(3) cite').attr("data-value");
        var oldprice = inforbox.find('p:eq(4) cite').attr("data-value");
        var oldtotal = inforbox.find('div.total span').attr("data-value");

        inforbox.hide();
        $(oFmName).appendTo(outfmbox);
        $(oFmMemory).appendTo(outfmbox);
        $(oFmNode).appendTo(outfmbox);
        $(oFmTime).appendTo(outfmbox);
        $(oFmPrice).appendTo(outfmbox);
        $(oFmReviseBtn).appendTo(outfmbox);

        // var tenant_name = $("#tenant_name").val();
        // var service_alias = $("#service_alias").val();
        // var step4_url = "/apps/" + tenant_name + "/" + service_alias + "/share/package";
        // $.ajax({
         //    url: step4_url,
         //    type: "GET",
         //    dataType: "json",
         //    data: {
         //        "id" : oDataId
         //    },
         //    beforeSend : function(xhr, settings) {
         //        var csrftoken = $.cookie('csrftoken');
         //        xhr.setRequestHeader("X-CSRFToken", csrftoken);
         //    },
         //    success:function(data){
         //        var oData = eval(data);
         //        if(oData.code == 200){
         //            var oldname = oData.data-name;
         //            var oldmemory = oData.data-memory;
         //            var oldnode = oData.data-node;
         //            var oldtime = oData.data-time;
         //            var oldprice = oData.data-price;
         //            var oldtotal = oData.data-total;
         //            inforbox.hide();
         //            $(oFmName).appendTo(outfmbox);
         //            $(oFmMemory).appendTo(outfmbox);
         //            $(oFmNode).appendTo(outfmbox);
         //            $(oFmTime).appendTo(outfmbox);
         //            $(oFmPrice).appendTo(outfmbox);
         //            $(oFmReviseBtn).appendTo(outfmbox);
         //        }
         //    },
         //    error: function() {
         //        tipsFnbox(tipsArray[5]);
         //    },
         //    cache: false
         //    // processData: false
        // });
        //////  

        $('.changebtn').click(function(){
        	var oPName = $(this).parent().parent().find('input.fmname').val();
            var oPMemory = $(this).parent().parent().find('select.fmsecmemory').val();
            var unit = "M";
            var value = oPMemory/1024;
            var oPNode = $(this).parent().parent().find('select.fmsecnode').val();
            var oPTime = $(this).parent().parent().find('select.fmsectime').val();
            var oPPrice = $(this).parent().parent().find('input.fmprice').val();
            var oPTotal = (0.069 * 2 * parseInt(oPMemory) * parseInt(oPNode) / 1024 + 0.0082) * 30 * 24 + 0.8 + parseFloat(oPPrice);
            if (value >= 1) {
                oPMemory = value;
                unit = "G";
            }
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
            }
            var tenant_name = $("#tenant_name").val();
            var service_alias = $("#service_alias").val();
            var service_key = $("#service_key").val();
            var app_version = $("#app_version").val();
            var step4_url = "/apps/" + tenant_name + "/" + service_alias + "/share/package";
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
                    "app_version": app_version
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
        	inforbox.find('p:eq(0) cite').html(oldname);
            var unit = "M";
            var value = oldmemory/1024;
            if (value >= 1) {
                oldmemory = value
                unit = "G"
            }
        	inforbox.find('p:eq(1) cite').html(oldmemory + unit);
        	inforbox.find('p:eq(2) cite').html(oldnode + '个');
        	inforbox.find('p:eq(3) cite').html(oldtime + '天');
        	inforbox.find('p:eq(4) cite').html(oldprice + '元／月');
        	inforbox.find('div.total span').html(oldtotal + '元／月');
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
        var step4_url = "/apps/" + tenant_name + "/" + service_alias + "/share/package";
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