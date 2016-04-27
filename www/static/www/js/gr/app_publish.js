$(function(){
    getCategoryList($('#app_type_first').val(), 'app_type_second');
    $('#app_type_first').change(function(){
        var cateId = $(this).val();
        getCategoryList(cateId, 'app_type_second');
    });
    $('#app_type_second').change(function(){
        var cateId = $(this).val();
        getCategoryList(cateId, 'app_type_third');
    });
});

//分类列表
function getCategoryList(cateId, contId){
    if(cateId * 1){
        $.get('https://app.goodrain.com/ajax/category_list/' + cateId + '?callback=?', {flag: 'cross'}, function(res){
            if(res.length){
                var listStr = '<option value="0" selected="selected">选择分类</option>';
                for(var i=0, len=res.length; i<len; i++){
                    listStr += '<option value="'+ res[i].id +'">'+ res[i].display_name +'</option>';
                }
                $('#' + contId).html(listStr);
                if(contId == 'app_type_second'){
                    $('#app_type_third').html('<option value="0" selected="selected">选择分类</option>');
                }
            }
        }, 'json');
    }else{
        if(contId == 'app_type_second'){
            $('#app_type_second').html('<option value="0" selected="selected">选择分类</option>');
            $('#app_type_third').html('<option value="0" selected="selected">选择分类</option>');
        }else if(contId == 'app_type_third'){
            $('#app_type_third').html('<option value="0" selected="selected">选择分类</option>');
        }
    }
}

$('.select-all-envs').click(
  function() {
    var checked = $(this).prop('checked');
    if (checked) {
      $(this).closest('table').find('tbody tr').addClass('warning');
      $(this).closest('table').find('input.env-select').prop('checked',true);
    } else {
      $(this).closest('table').find('tbody tr').removeClass('warning');
      $(this).closest('table').find('input.env-select').prop('checked',false);
    }
  }
);

$('.env-select').click(
  function() {
    var checked = $(this).prop('checked');
    if (checked) {
        $(this).closest('tr').addClass('warning');
    } else {
        $(this).closest('tr').removeClass('warning');
        $('.select-all-envs').prop('checked',false);
    }
  }
);

$('.rw-option').change(function() {
    var curr_tr = $(this).closest('tr');
    var rewrite_td = curr_tr.find('.rewrite-attr-value');
    var option = $(this).val();
    var html_content = '';
    if (option=='custom') {
        old_value = rewrite_td.html();
        console.log(old_value);
        rewrite_td.attr('old_value', old_value);
        //removeAttr('name');
        content = '<input name="attr_value" type="text" value="" placeholder="填写示例">';
        rewrite_td.html(content);
    } else if (option=='readonly') {
        old_value = rewrite_td.attr('old_value');
        console.log(old_value);
        rewrite_td.html(old_value);
        rewrite_td.attr('name', 'attr_value');
    }
});

$('#confirm-commit').click(function() {
    envs = []
    $('#service-envs tbody tr.warning').each(function() {
        env = {};
        $(this).find('[name^=attr]').each(function(event) {
            i = $(this);
            name = $(this).attr('name');
            value = $(this).val() || i.html();
            env[name] = value;
        });
        envs.push(env);
    });
    var csrftoken = $.cookie('csrftoken');
    data = {"envs": envs};
    $.ajax({
      url: window.location.pathname,
      method: "POST",
      data: $.stringify(data),
      beforeSend: function(xhr) {
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
      },
      success :function (event) {
        if (event.success) {
          window.location.href = event.next_url;
        } else {
          showMessage(event.info);
        }
      },
      contentType: 'application/json; charset=utf-8',

      statusCode: {
        403: function(event) {
          alert("你没有此权限");
        }
      },
    });
  });

$(document).ready(
  function () {
      $('.select-all-envs').prop('checked', true);
      $('.env-select').prop('checked', true);
      $('.env-select').closest('tr').addClass('warning');
  }
);

// 添加依赖关系
$("#addRelation").bind("click", function () {
    // 获取服务的信息
    var tmpKey = $("#id_app_relation").val();
    var tmpVersion = $("#id_app_relation").attr("version");
    if (tmpKey == null) {
        alert("请选择服务!")
    }
    // 获取依赖关系
    var tmpValue = $("input[name=relationRadio]").val();
    if (tmpValue == null) {
        alert("请选择依赖关系")
    }
    // 添加到对应的div区域
    if (tmpValue == "inner") {
        suffixarray.add({key: tmpKey, version: tmpVersion})
        $("#app_suffix").val(suffixarray)
    } else {
        prefixarray.add({key: tmpKey, version: tmpVersion})
        $("#app_prefix").val(prefixarray)
    }
});

$("#add_service_attr").bind("click", function () {
    //获取当前数量
    var num = parseInt($("#env_list_len").val()) + 1;
    var tr = $("<tr />");
    $("<td/>").append($("<input/>").attr({"type":"text", "name":"env_list["+num+"].attr_name"})).appendTo(tr);
    $("<td/>").append($("<input/>").attr({"type":"text", "name":"env_list["+num+"].name"})).appendTo(tr);
    $("<td/>").append($("<input/>").attr({"type":"text", "name":"env_list["+num+"].attr_value"})).appendTo(tr);
    $("<select/>").attr({"name":"env_list["+num+"].scope"})
            .append($("<option/>").val("inner").text("对内"))
            .append($("<option/>").val("outer").text("对外"))
            .appendTo($("<td/>").appendTo(tr));
    $("<td/>").append($("<button/>").text("X").attr("onclick", "javascript:removetr(this);")).appendTo(tr);
    $("#env_body").append(tr);
    $("#env_list_len").val(num);
});
$("#add_service_port").bind("click", function () {
    var num = parseInt($("#port_list_len").val()) + 1;
    var tr = $("<tr/>");
    $("<td/>").append($("<input/>").attr({"type":"text", "name":"port_list["+num+"].container_port"})).appendTo(tr);
    $("<td/>").append($("<input/>").attr({"type":"text", "name":"port_list["+num+"].mapping_port"})).appendTo(tr);
    $("<select/>").attr({"name":"port_list["+num+"].protocol"})
            .append($("<option/>").val("http").text("HTTP"))
            .append($("<option/>").val("stream").text("STREAM"))
            .appendTo($("<td/>").appendTo(tr));
    $("<td/>").append($("<input/>").attr({"type":"text", "name":"port_list["+num+"].port_alias"})).appendTo(tr);
    $("<td/>").append($("<input/>").attr({"type":"checkbox", "name":"port_list["+num+"].is_inner_service"}).addClass("switch-box")).appendTo(tr);
    $("<td/>").append($("<input/>").attr({"type":"checkbox", "name":"port_list["+num+"].is_outer_service"}).addClass("switch-box")).appendTo(tr);
    $("<td/>").append($("<button/>").text("X").attr("onclick", "javascript:removetr(this);")).appendTo(tr);
    $("#port_body").append(tr);
    $("#port_list_len").val(num);
});

var removetr = function (td) {
    var trobj = $(td).closest('tr');
    $(trobj).remove();
    return false;
}

var checkdata = function () {
    //拼接portlist
    var num = parseInt($("#env_list_len").val());
    for (var i = 1; i <= num; i++) {
        var tmparray = new Array(4)
        var tmpname = "env_list["+ num + "].name";
        tmparray[0] = $('input[name=tmpname]').val();
        tmpname = "env_list["+ num + "].attr_name";
        tmparray[1] = $('input[name=tmpname]').val();
        tmpname = "env_list["+ num + "].attr_value";
        tmparray[2] = $('input[name=tmpname]').val();
        tmpname = "env_list["+ num + "].scope";
        tmparray[3] = $('input[name=tmpname]').val();
        $("<input/>").attr({"type":"hidden", "name":"env_list"})
                .val(tmparray.join(',')).appendTo($("#env_body"));
    }
    //拼接envlist
    num = parseInt($("#port_list_len").val())
    for (var i = 1; i <= num; i++) {
        var tmparray = new Array(6)
        var tmpname = "port_list["+ num + "].container_port";
        tmparray[0] = $('input[name=tmpname]').val();
        tmpname = "port_list["+ num + "].mapping_port";
        tmparray[1] = $('input[name=tmpname]').val();
        tmpname = "port_list["+ num + "].protocol";
        tmparray[2] = $('input[name=tmpname]').val();
        tmpname = "port_list["+ num + "].port_alias";
        tmparray[3] = $('input[name=tmpname]').val();
        tmpname = "port_list["+ num + "].is_inner_service";
        tmparray[4] = $('input[name=tmpname]').val();
        tmpname = "port_list["+ num + "].is_outer_service";
        tmparray[5] = $('input[name=tmpname]').val();
        $("<input/>").attr({"type":"hidden", "name":"port_list"})
                .val(tmparray.join(',')).appendTo($("#env_body"));
    }
    return true;
}

