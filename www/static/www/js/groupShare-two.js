$(function () {
    $("#tab a").click(function () {
        $("#tab a").css({"color": "#838383"});
        $("#tab a").eq($(this).index()).css({"color": "#2bcb75"});
        console.log($(this).index());
        $("section.appShare").hide();
        $("section.appShare").eq($(this).index()).show();
    });
    $("#nextstep").click(function () {
        var tenant_name = $("#tenant_name").val();
        var group_id = $("#group_id").val();
        var share_id = $("#share_id").val();
        var appShare = $("section.appShare");
        var data = {};
        console.log(appShare.length);
        for( var i = 0; i<appShare.length; i++ )
        {
            var dataId = {};
            var env_id = $("section.appShare").eq(i).find("tbody.variable tr");
            for( var j = 0; j<env_id.length; j++ )
            {
                var num = env_id.eq(j).find("input.yOn").prop("checked")?1:0;
                dataId[env_id.eq(j).attr("data-id")] = num;
            }

            data[appShare.eq(i).attr("data-id")] = dataId;
        }
        data = JSON.stringify(data)
        console.log(data);
        $.ajax({
           type: "POST",
           url: "/apps/" + tenant_name + "/" + group_id + "/" + share_id + "/second/",
           data: {
               "env_data": data
           },
           cache: false,
           beforeSend: function (xhr, settings) {
               var csrftoken = $.cookie('csrftoken');
               xhr.setRequestHeader("X-CSRFToken", csrftoken);
           },
           success: function (msg) {
               var json_data = eval(msg);
               if (json_data.code == 200) {
                   location.href = "/apps/" + tenant_name + "/" + group_id + "/" + share_id + "/third/";
               } else {
                   swal(json_data.msg);
               }
           },
           error: function () {
               swal("系统异常");
           }
        });
    })
});