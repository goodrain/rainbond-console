$(function () {
    var group_id=$("#group-name option:selected").val();
    if (group_id == -2){
        FnLayer("请输入组名");
    }
    
    $("#group_install_one").on("click", function () {
        // var group_name = $("#group_name").val();
        // if ($.trim(group_name) == "") {
        //     swal("组名称不能为空");
        //     return false;
        // }
        //禁用按钮
        $("#group_install_one").attr('disabled');
        var tenantName = $("#tenantNameValue").val();
        var share_group_id = $("#share_group_id").val();
        var selectedGroupId = $("#group-name option:selected").attr("value");
        var group_name=$("#group-name option:selected").text();
        console.log("===> "+selectedGroupId+"\t"+group_name);
        $.ajax({
            type : "post",
            url : "/apps/" + tenantName + "/group-deploy/" + share_group_id+"/step1/",
            data : {
                "select_group_id":selectedGroupId,
                "group_name":group_name
            },
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
                    swal(dataObj["info"]);
                    $("#group_install_one").removeAttr('disabled');
                }
            },
            error : function() {
                swal("系统异常,请重试");
                $("#group_install_one").removeAttr('disabled');
            }
        })
    });

    $("#group-name").change(function(){
        var groupName=$("#group-name option:selected").val();
        //console.log(groupName);
        if(groupName == -2) {
            FnLayer("请输入新增组名");
        }
    });
});


function FnLayer(textTit){
    var oDiv = '<div class="layerbg"><div class="layermain"></div></div>';
    var oCloseBtn = '<a href="javascript:;" class="btn btn-danger fn-close"><i class="fa fa-times"></i></a>';
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
        $("#group-name").find("option").eq(0).prop("selected",true);
    });
    $(".fn-sure").click(function(){
        if(inputText == ""){
            swal("您还没有输入组名！");
            return false;
        }else{
            var inputText = $(".input-css input").val();
            var tenant_name = $("#tenantNameValue").val();
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