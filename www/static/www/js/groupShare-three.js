$(function () {
    $("#tab a").click(function () {
        $("#tab a").css({"color": "#838383"});
        $("#tab a").eq($(this).index()).css({"color": "#2bcb75"});
        console.log($(this).index());
        $("section.appShare").hide();
        $("section.appShare").eq($(this).index()).show();
    });

    // 分发到云市后显示设置
    $(".is_outer").parent().parent().on('switch-change', function (e, data) {
        var $el = $(data.el)
            , value = data.value;
        //alert(value);
        if (value) {
            $("div.form-group[data-alias='show_div']").show();
            $("div.form-group[data-alias='private_div']").hide();
        } else {
            $("div.form-group[data-alias='show_div']").hide();
            $("div.form-group[data-alias='private_div']").show();
        }
    });

    $("#nextstep").bind("click", function () {
        var tenant_name = $("#tenant_name").val();
        var group_id = $("#group_id").val();
        var share_id = $("#share_id").val();
        var appShare = $("section.appShare");
        var data = {};
        var service_ids = [];
        for( var i = 0; i<appShare.length; i++ )
        {
            app_data = {};
            app_data["name"] = $("input.app_name").eq(i).val();
            app_data["version"] = $("input.app_version").eq(i).val();
            app_data["content"] = $("textarea.app_content").eq(i).val();
            app_data["is_init"] = $("input.is_init").eq(i).prop("checked")?1:0;
            var one = $("input.is_outer").eq(i).prop("checked")?1:0;
            var two = $("input.is_private").eq(i).prop("checked")?1:0;
            var three = $("input.show_assistant").eq(i).prop("checked")?1:0;
            var four = $("input.show_cloud").eq(i).prop("checked")?1:0;
            app_data["is_outer"] = one;
            app_data["is_private"] = two;
            app_data["show_assistant"] = three;
            app_data["show_cloud"] = four;
            data[appShare.eq(i).attr("data-id")] = app_data;
            service_ids.push(appShare.eq(i).attr("data-id"));
        }
        data = JSON.stringify(data);
        console.log(data);
        $.ajax({
            type: "POST",
            url: "/apps/" + tenant_name + "/" + group_id + "/" + share_id + "/third/",
            data: {
                "pro_data": data,
                "service_ids": JSON.stringify(service_ids)
            },
            cache: false,
            beforeSend: function (xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function (msg) {
                var json_data = eval(msg);
                if (json_data.code == 200) {
                    location.href = "/apps/" + tenant_name + "/myservice/?gid=" + group_id;
                } else {
                    swal(json_data.msg);
                }
            },
            error: function () {
                swal("系统异常");
            }
        });
    });

});