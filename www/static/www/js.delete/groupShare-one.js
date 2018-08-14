$(function () {


    gWidget.define("bindConsoleUrl", {
        extend:'dialog',
        _defaultOption:{
             title:'提示',
             minWidth: '550px',
             width: '550px',
             height:'450px',
             showFooter: true,
             eid:''
        },
        _init:function(opt){
           
            this.callParent(opt);
            if(this.ClassName == 'bindConsoleUrl'){
                this._create();
                this.bind();
            }
        },
        _create:function(opt){
            this.callParent(opt);
            this.setContent(
                "<div  class='beforeToCheck' style='color:#333;'>"+
                    "<p style='font-size:20px; text-align:center; color:#333; margin-bottom:0; margin-top:10px;'>您的私有云帮需要在好雨官方认证通过</p>"+
                    "<p style='color:#a94442;text-align:center; margin-bottom:40px;'>(请按以下步骤操作进行认证)</p>"+
                    "<p style='font-size:14px; color:#333; padding-left:70px; padding-bottom:10px;'><span style='display:inline-block; width:26px; height:26px; background:#28cb75; text-align:center; color:#fff; line-height:26px; border-radius:13px; margin-right:5px;'>1</span>到好雨官方获取您企业的认证信息,<a class='to-check' style='margin-left:10px;'>去获取</a></p>"+
                    "<p style='font-size:14px; padding-bottom:20px; color:#333; padding-left:70px; padding-bottom:20px;'><span style='display:inline-block; width:26px; height:26px; background:#28cb75; text-align:center; color:#fff; line-height:26px; border-radius:13px; margin-right:5px;'>2</span>请在下方输入框中输入您的认证信息，并提交认证</p>" +
                    "<p class='clearfix'><label style='width:120px; text-align:right; padding-right:5px; line-height:32px;'>企业ID</label><input type='text' id='clientId' style='border-radius:4px; width:340px; border:1px #ddd solid; height:32px;'/></p>" +
                    "<p class='clearfix' ><label style='width:120px; text-align:right; padding-right:5px; line-height:32px;'>企业Token</label><input type='text' id='clientToken' style='border-radius:4px; width:340px; border:1px #ddd solid; height:32px;'/></p>" + 
                "</div>"
            )
        },
        bind:function(){
            var self = this;
            this.callParent();

            this.element.delegate('.to-check', 'click', function(e){
                window.open("https://www.goodrain.com/#/check-console/"+self.option.eid);
            });

            this.element.delegate('.btn-success', 'click', function(e){
                console.log(self.option.eid)
                console.log($("#clientId").val());
                console.log($("#clientToken").val());
                if($("#clientId").val() == ""){
                    gWidget.Message.warning("企业ID不能为空！");
                    return;
                }
                if($("#clientToken").val() == ""){
                    gWidget.Message.warning("企业Token不能为空！");
                    return;
                }
                ///
                $.ajax({
                    url: '/ajax/enterprises/active',
                    type : 'post',
                    data:{
                        "enterprise_id" : self.option.eid,
                        "market_client_id" : $("#clientId").val(),
                        "market_client_token" : $("#clientToken").val()
                    },
                    headers:{
                        "X-CSRFToken": $.cookie('csrftoken')
                    },
                    success: function(data){
                        if(data.ok == true){
                            gWidget.Message.success("认证成功！");
                            self.destroy();
                            window.location.reload();
                        }
                    },
                    error: function(data){
                        gWidget.Message.warning("认证失败，请重新认证");
                    }
                })
                ///
            })
           
        }
    })



    $("#nextstep").click(function () {
        var params = getParams();
        if (params.create_name) {
            $("#create_name_notice").css({"display": "none"});
        }
        else {
            $("#create_name_notice").css({"display": "block"});
            return;
        }

        if (params.version_no) {
            $("#version_no_notice").css({"display": "none"});
        } else {
            $("#version_no_notice").css({"display": "block"});
            return;
        }

        var is_enterprise_active = $("#is_enterprise_active").val();
        var eid = $("#enterprise_id").val();




        if (params.share_scope === 'market' && is_enterprise_active === "0") {
            gWidget.create('bindConsoleUrl', {
                eid: eid
            })
            return;
        }

        $.ajax({
            type: "POST",
            url: "/apps/" + params.tenant_name + "/" + params.group_id + "/first/",
            data: {
                "alias": params.create_name,
                "publish_type": params.publish_type,
                "group_version": params.version_no,
                "desc": params.desc,
                "is_market": params.is_market,
                "installable": params.installable,
                "share_scope":params.share_scope

            },
            cache: false,
            beforeSend: function (xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function (msg) {
                var json_data = eval(msg);
                if (json_data.code == 200) {
                    console.log(json_data.next_url);
                    location.href = json_data.next_url;
                } else {
                    swal(json_data.msg);
                }
            },
            error: function () {
                swal("系统异常");
            }
        });
    });

    /**
     * 发布到云市显示是否允许安装选项
     */
    $("select[name=publish_dest]").change(function () {
        var selectItem = $("select[name=publish_dest]");
        var shareScope = selectItem.val()


    });

});

/**
 * 获取页面数据
 * @returns {{tenant_name: (*|jQuery), group_id: (*|jQuery), share_id: (*|jQuery), create_name: (*|jQuery), version_no: (*|jQuery), publish_type: string, desc: (*|jQuery), is_market: boolean, installable: boolean}}
 */
function getParams() {
    /** 默认值 */
    var publish_type = "services_group"; // 旧参数，发布类型默认为services_group
    var installable = true; // 旧参数，是否允许安装，默认允许安装
    /** 取值*/
    var tenant_name = $("#tenant_name").val();
    var group_id = $("#group_id").val();
    var create_name = $("#create_name").val();
    var version_no = $("#version_no").val();

    var desc = $("#desc").val();
    var is_market = false;

    var selectItem = $("select[name=publish_dest]");
    var shareScope = selectItem.val();

    var params = {
        tenant_name: tenant_name,
        group_id: group_id,
        create_name: $.trim(create_name),
        version_no: $.trim(version_no),
        publish_type: publish_type,
        desc: desc,
        is_market: is_market,
        installable: installable,
        share_scope: shareScope
    };
    return params;
}
