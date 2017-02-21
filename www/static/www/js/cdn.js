$(function(){
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
})