$(function () {
    $("#nextstep").click(function () {
        var tenant_name = $("#tenant_name").val();
        var group_id = $("#group_id").val();
        var share_id = $("#share_id").val();
        var create_name = $("#create_name").val();
        if (create_name) {
            console.log($("#create_name").val());
            $("#create_name_notice").css({"display": "none"});
        }
        else {
            $("#create_name_notice").css({"display": "block"});
            return;
        }

        $.ajax({
            type: "POST",
            url: "/apps/" + tenant_name + "/" + group_id + "/" + share_id + "/first/",
            data: {
                "alias": create_name
            },
            cache: false,
            beforeSend: function (xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function (msg) {
                var json_data = eval(msg);
                if (json_data.code == 200) {
                    location.href = "/apps/" + tenant_name + "/" + group_id + "/" + share_id + "/second/";
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
