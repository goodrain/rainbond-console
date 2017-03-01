$(function(){
    $(document).ready(function(){
        $(".dcjq-parent").eq(0).addClass("active");
        $("#sidebar ul.sidebar-menu li").eq(2).find("ul.sub").css({"display":"block"});
        $("#sidebar ul.sidebar-menu li").eq(2).find("ul.sub li.third_app").addClass("active");
    });
    $("button.add_domain").click(function(){
        $("p.input_domain").show();
        $("input.domain_name").focus();
    });
    $("button.add_sure").click(function(){
        if( $("input.domain_name").val() )
        {
            var tenantName = $("#tenantName").val();
            var app_id = $("#app_id").val();
            $.ajax({
                type : "POST",
                url : "/ajax/"+tenantName+"/"+app_id+"/domain/add",
                data : {
                    domain : $("input.domain_name").val()
                },
                cache: false,
                beforeSend : function(xhr, settings) {
                    var csrftoken = $.cookie('csrftoken');
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                },
                success : function(data){
                    swal(data["message"]);
                    if(data["status"] == "success")
                    {
                        history.go(0);
                    }
                },
                error : function(){
                    swal("系统异常");
                }
            });
        }
        else{
            swal("请输入域名");
        }
    });
    $("button.add_cancel").click(function(){
        $("p.input_domain").hide();
        $("input.domain_name").val("");
    });
    del_domain();
    function del_domain(){
        $("a.del_domain").off('click');
        $("a.del_domain").on('click',function(){
            var that = $(this);
            var tenantName = $("#tenantName").val();
            var app_id = $("#app_id").val();
            var domain_name = $(this).parents("tr").find("td").eq(0).html();
            $.ajax({
                type : "POST",
                url : "/ajax/"+tenantName+"/"+app_id+"/domain/delete",
                data : {
                    domain : domain_name
                },
                cache: false,
                beforeSend : function(xhr, settings) {
                    var csrftoken = $.cookie('csrftoken');
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                },
                success : function(data){
                    swal(data["message"]);
                    if( data["status"] == "success" )
                    {
                        //that.parents("tr").remove();
                        history.go(0);
                    }
                },
                error : function(){
                    swal("系统异常");
                }
            });
        });
    }

    $("button.add_operator").click(function(){
        $("p.input_operator").show();
        $("input.operator_name").focus();
    });
    $("button.operator_sure").click(function(){
        if( $("input.operator_name").val() && $("input.operator_realName").val() && $("input.operator_password").val() )
        {
            var reg = /^[\w]{3,60}$/;
            if( $("input.operator_name").val().match(reg) )
            {
                var tenantName = $("#tenantName").val();
                var app_id = $("#app_id").val();
                $.ajax({
                    type : "POST",
                    url : "/ajax/"+tenantName+"/"+app_id+"/operator/add",
                    data : {
                        operator_name : $("input.operator_name").val(),
                        realname : $("input.operator_realName").val(),
                        password : $("input.operator_password").val()
                    },
                    cache: false,
                    beforeSend : function(xhr, settings) {
                        var csrftoken = $.cookie('csrftoken');
                        xhr.setRequestHeader("X-CSRFToken", csrftoken);
                    },
                    success : function(data){
                        swal(data["message"]);
                        if( data["status"] == "success" )
                        {
                            history.go(0);
                        }
                    },
                    error : function(){
                        swal("系统异常");
                    }
                });
            }
            else{
                swal("操作员名称由3~60个字符，英文数字和_组成");
            }
        }
        else{
            swal("请输入信息");
        }
    });
    $("button.operator_cancel").click(function(){
        $("p.input_operator").hide();
        $("input.operator_name").val("");
        $("input.operator_realName").val("");
        $("input.operator_password").val("");
    });
    del_operator();
    function del_operator(){
        $("a.del_operator").off('click');
        $("a.del_operator").on('click',function(){
            var that = $(this);
            var tenantName = $("#tenantName").val();
            var app_id = $("#app_id").val();
            var operator_name = $(this).parents("tr").find("td").eq(0).html();
            $.ajax({
                type : "POST",
                url : "/ajax/"+tenantName+"/"+app_id+"/operator/delete",
                data : {
                    operator_name : operator_name
                },
                cache: false,
                beforeSend : function(xhr, settings) {
                    var csrftoken = $.cookie('csrftoken');
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                },
                success : function(data){
                    swal(data["message"]);
                    if( data["status"] == "success" )
                    {
                        //that.parents("tr").remove();
                        history.go(0);
                    }
                },
                error : function(){
                    swal("系统异常");
                }
            });
        });
    }
    $("a.changeName").click(function(){
       $("p.cdn_name").show();
        $("p.cdn_name input").focus();
    });
    $("button.name_cancel").click(function(){
        $("p.cdn_name").hide();
        $("p.cdn_name input").val("");
    })
    $("button.name_sure").click(function(){
        if( $("p.cdn_name input").val() )
        {
            var tenantName = $("#tenantName").val();
            var app_id = $("#app_id").val();
            $.ajax({
                type : "POST",
                url : "/ajax/"+tenantName+"/"+app_id+"/updateName",
                data : {
                    name : $("p.cdn_name input").val()
                },
                cache: false,
                beforeSend : function(xhr, settings) {
                    var csrftoken = $.cookie('csrftoken');
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                },
                success : function(data){
                    swal(data["message"]);
                    if( data["status"] == "success" )
                    {
                        $("#cdn_name").html($("p.cdn_name input").val());
                        $("p.cdn_name").hide();
                        $("p.cdn_name input").val("");
                    }
                },
                error : function(){
                    swal("系统异常");
                }
            });
        }
        else{
            swal("请输入名称");
        }
    });
    $("select.flow_size").change(function(){
        var data = {
            "500G" : "130元",
            "1T" : "260元",
            "5T" : "1250元",
            "10T" : "2440元",
            "50T" : "11200元",
            "200T" : "43000元",
            "1PB" : "204800元"
        };
        $("span.flow_money").html(data[$(this).val()]);
    });
    $("button.flow_buy").click(function(){
        var size = $("select.flow_size").val();
        var tenantName = $("#tenantName").val();
        var app_id = $("#app_id").val();
        $.ajax({
            type : "POST",
            url : "/ajax/"+tenantName+"/"+app_id+"/traffic/add",
            data : {
                traffic_size : size
            },
            cache: false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success : function(data){
                swal(data["message"]);
                if( data["status"] == "success" )
                {
                    history.go(0);
                }
            },
            error : function(){
                swal("系统异常");
            }
        });
    });
    $("button.delete_cdn").click(function(){
        var notify_text = "确定删除当前服务吗？";
        swal({
            title : notify_text,
            type : "warning",
            showCancelButton : true,
            confirmButtonColor : "#DD6B55",
            confirmButtonText : "确定",
            cancelButtonText : "取消",
            closeOnConfirm : false,
            closeOnCancel : false
        }, function(isConfirm) {
            if (isConfirm) {
                var tenantName = $("#tenantName").val();
                var app_id = $("#app_id").val();
                $.ajax({
                    type : "POST",
                    url : "/ajax/"+tenantName+"/"+app_id+"/delete",
                    data : {},
                    cache : false,
                    beforeSend : function(xhr, settings) {
                        var csrftoken = $.cookie('csrftoken');
                        xhr.setRequestHeader("X-CSRFToken", csrftoken);
                        swal({
                            title : "正在执行删除操作，请稍候...",
                            text : "5秒后自动关闭",
                            timer : 5000,
                            showConfirmButton : false
                        });
                    },
                    success : function(msg) {
                        var dataObj = msg;
                        if (dataObj["status"] == "success")
                        {
                            swal("操作成功");
                            window.location.href = "/apps/"+tenantName+"/third_app/list"
                        }
                        else
                        {
                            swal("操作失败");
                        }
                    },
                    error : function() {
                        swal("系统异常");
                    }
                });
            } else {
                swal.close();
            }
        });
    });
    $("#open_thirdApp").click(function(){
        var tenantName = $("#tenantName").val();
        var app_id = $("#app_id").val();
        $.ajax({
            type : "POST",
            url : "/ajax/"+tenantName+"/"+app_id+"/open",
            data : {},
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
                swal({
                    title : "正在执行启动操作，请稍候...",
                    text : "5秒后自动关闭",
                    timer : 5000,
                    showConfirmButton : false
                });
            },
            success : function(msg) {
                var dataObj = msg;
                if (dataObj["status"] == "success")
                {
                    swal("操作成功");
                    history.go(0);
                }
                else
                {
                    swal("操作失败");
                }
            },
            error : function() {
                swal("系统异常");
            }
        });
    });
    $("#close_thirdApp").click(function(){
        var tenantName = $("#tenantName").val();
        var app_id = $("#app_id").val();
        $.ajax({
            type : "POST",
            url : "/ajax/"+tenantName+"/"+app_id+"/close",
            data : {},
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
                swal({
                    title : "正在执行关闭操作，请稍候...",
                    text : "5秒后自动关闭",
                    timer : 5000,
                    showConfirmButton : false
                });
            },
            success : function(msg) {
                var dataObj = msg;
                if (dataObj["status"] == "success")
                {
                    swal("操作成功");
                    history.go(0);
                }
                else
                {
                    swal("操作失败");
                }
            },
            error : function() {
                swal("系统异常");
            }
        });
    });
    $("#app_refresh").click(function(){
        var tenantName = $("#tenantName").val();
        var app_id = $("#app_id").val();
        $.ajax({
            type : "POST",
            url : "/ajax/"+tenantName+"/"+app_id+"/purge",
            data : {},
            cache : false,
            beforeSend : function(xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
                swal({
                    title : "正在执行刷新操作，请稍候...",
                    text : "5秒后自动关闭",
                    timer : 5000,
                    showConfirmButton : false
                });
            },
            success : function(msg) {
                var dataObj = msg;
                if (dataObj["status"] == "success")
                {
                    swal("操作成功");
                    history.go(0);
                }
                else
                {
                    swal("操作失败");
                }
            },
            error : function() {
                swal("系统异常");
            }
        });
    });
    $(".app_manage").click(function(){
        $(".layer-body-bg").css({"display":"block"});
    });
    $(".cancel").on("click",function(){
        $(".layer-body-bg").css({"display":"none"});
    });
    $(".del").on("click",function(){
        $(".layer-body-bg").css({"display":"none"});
    });
    manage_del();
    function manage_del(){
        $("span.manage_del").off("click");
        $("span.manage_del").on('click',function(){
            $(this).parents("tr").remove();
        });
    }
    $("span.manage_add").click(function(){
        var str = '<tr><td><input type="text" placeholder="IP或域名"></td><td><input type="number" value="443"></td><td><select><option data-toggle="true">主线路</option><option>备用线路</option></select></td>';
        str += '<td><input type="number" value="1"></td><td><input type="number" value="3"></td><td><input type="number" value="30"></td><td><span class="manage_del"></span></td></tr>';
        $(str).appendTo("table.tab-box tbody");
        manage_del();
    });
    $(".saveManage").click(function(){
        var data = {};
        data["manage_host"] = $(".manage_host").val();
        if( $(".manage input[type='radio'][name='way']:checked").data("id") )
        {
            console.log($(".manage input[type='radio'][name='way']:checked"));
            data["source_type"] = $(".manage input[type='radio'][name='way']:checked").attr("data-id");
            var line = $(".manage table.tab-box tbody tr");
            var servers = [];
            console.log(line.length);
            for( var i = 0; i<line.length; i++ )
            {
                var data_json = {};
                console.log(line.eq(i).find("input").eq(0).val());
                console.log(line.eq(i).find("input").eq(1).val());
                if( line.eq(i).find("input").eq(0).val() )
                {
                    data_json["host"] = line.eq(i).find("input").eq(0).val();
                    if( line.eq(i).find("input").eq(1).val() )
                    {
                        data_json["port"] = line.eq(i).find("input").eq(1).val();
                        data_json["weight"] = line.eq(i).find("input").eq(2).val();
                        data_json["max_fails"] = line.eq(i).find("input").eq(3).val();
                        data_json["fail_timeout"] = line.eq(i).find("input").eq(4).val();
                        data_json["backup"] = line.eq(i).find("option:checked").attr("data-toggle")?1:0;
                        servers.push(data_json);
                    }
                    else{
                        swal("请输入第"+(i+1)+"个端口号");
                    }
                }
                else{
                    swal("请输入第"+(i+1)+"个回源地址");
                }
            }
            data["servers"] = servers;
        }
        else{
            swal("请选择回源方式");
        }
        console.log(data);
    });
})