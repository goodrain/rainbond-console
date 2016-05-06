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
    var op = $("#id_app_relation").find("option[value='"+tmpKey+"']")
    var tmpVersion = $(op).attr("data-version");
    var tmpAlias = $(op).attr("data-alias");
    if (tmpKey == null) {
        alert("请选择服务!")
    }
    // 获取依赖关系
    var tmpValue = $("input[name=relationRadio]:checked").val()
    if (tmpValue == null) {
        alert("请选择依赖关系")
    }
    // 添加到对应的div区域
    if (tmpValue == "suffix") {
        $("<div />").text(tmpAlias+'-'+tmpVersion).attr({"data-key":tmpKey, "data-version":tmpVersion, "data-alias": tmpAlias})
                .addClass("controls controls-row")
                .append($("<button/>").text("X").attr("onclick", "javascript:removelabel(this);"))
                .appendTo($("#app_suffix"));
    } else {
        $("<div />").text(tmpAlias+'-'+tmpVersion).attr({"data-key":tmpKey, "data-version":tmpVersion, "data-alias": tmpAlias})
                .addClass("controls controls-row")
                .append($("<button/>").text("X").attr("onclick", "javascript:removelabel(this);"))
                .appendTo($("#app_prefix"));
    }
});
var removelabel = function (label) {
    var lableobj = $(label).closest('div');
    $(lableobj).remove();
    return false;
};
var relationdata = function () {
    var suffix = new Array();
    $("#app_suffix").find("div").each(function (obj, callback, args) {
        skey = $(this).attr("data-key");
        svalue = $(this).attr("data-version");
        salias = $(this).attr("data-alias");
        suffix.push(skey + ", " + svalue + "," + salias)
    });
    $("input[name='suffix']").val(suffix.join(";"))
    var prefix = new Array();
    $("#app_prefix").find("div").each(function (obj, callback, args) {
        pkey = $(this).attr("data-key");
        pvalue = $(this).attr("data-version");
        salias = $(this).attr("data-alias");
        prefix.push(pkey + ", " + pvalue + "," + salias)
    });
    $("input[name='prefix']").val(prefix.join(";"))
    return true;
}

$("#add_service_attr").bind("click", function () {
    //获取当前数量
    var num = parseInt($("#env_list_len").val()) + 1;
    var tr = $("<tr />");
    $("<td/>").append($("<input/>").attr({"type":"text", "id":"env_list_"+num+"_name"})).appendTo(tr);
    $("<td/>").append($("<input/>").attr({"type":"text", "id":"env_list_"+num+"_attr_name"})).appendTo(tr);
    $("<td/>").append($("<input/>").attr({"type":"text", "id":"env_list_"+num+"_attr_value"})).appendTo(tr);
    $("<select/>").attr({"id":"env_list_"+num+"_scope"})
            .append($("<option/>").val("inner").text("对内"))
            .append($("<option/>").val("outer").text("对外"))
            .append($("<option/>").val("both").text("内外"))
            .appendTo($("<td/>").appendTo(tr));
    $("<td/>").append($("<input/>").attr({"type":"checkbox", "id":"env_list_"+num+"_change"})).appendTo(tr);
    $("<td/>").append($("<button/>").text("X").attr("onclick", "javascript:removetr(this);")).appendTo(tr);
    $("#env_body").append(tr);
    $("#env_list_len").val(num);
});
$("#add_service_port").bind("click", function () {
    var num = parseInt($("#port_list_len").val()) + 1;
    var tr = $("<tr/>");
    $("<td/>").append($("<input/>").attr({"type":"text", "id":"port_list_"+num+"_container_port"})).appendTo(tr);
    $("<select/>").attr({"id":"port_list_"+num+"_protocol"})
            .append($("<option/>").val("http").text("HTTP"))
            .append($("<option/>").val("stream").text("STREAM"))
            .appendTo($("<td/>").appendTo(tr));
    $("<td/>").append($("<input/>").attr({"type":"text", "id":"port_list_"+num+"_port_alias"})).appendTo(tr);
    $("<td/>").append($("<input/>").attr({"type":"checkbox", "id":"port_list_"+num+"_is_inner_service"}).addClass("switch-box")).appendTo(tr);
    $("<td/>").append($("<input/>").attr({"type":"checkbox", "id":"port_list_"+num+"_is_outer_service"}).addClass("switch-box")).appendTo(tr);
    $("<td/>").append($("<button/>").text("X").attr("onclick", "javascript:removetr(this);")).appendTo(tr);
    $("#port_body").append(tr);
    $("#port_list_len").val(num);
});

var removetr = function (td) {
    var trobj = $(td).closest('tr');
    $(trobj).remove();
    return false;
}

var ENV_NAME_REG =/^[A-Z][A-Z0-9_]*$/;
var PORT_REG = /^[0-9]*$/;

var checkdata = function () {
    //拼接portlist
    var num = parseInt($("#env_list_len").val());
    $("input[name='env_list']").remove();
    var envarray = new Array()
    for (var i = 1; i <= num; i++) {
        var tmparray = new Array(5)
        var tmpname = "env_list_"+ i + "_name";
        if (typeof($('#'+tmpname+'')) === 'undefined') {
            swal("名称不能为空")
            return false;
        }
        if($('#'+tmpname+'').val() == ""){
            swal("名称不能为空")
            return false;
        }
        
        tmparray[0] = $('#'+tmpname).val();
        tmpname = "env_list_"+ i + "_attr_name";
        if(!ENV_NAME_REG.test($('#'+tmpname+'').val())){
            swal("变量名不合法")
            return false;
        }
        tmparray[1] = $('#'+tmpname+'').val();
        tmpname = "env_list_"+ i + "_attr_value";
        if($('#'+tmpname+'').val() == ""){
            swal("变量值不能为空")
            return false;
        }
        tmparray[2] = $('#'+tmpname+'').val();
        tmpname = "env_list_"+ i + "_scope";
        tmparray[3] = $('#'+tmpname+'').val();
        tmpname = "env_list_"+ i + "_change";
        tmparray[4] = $('#'+tmpname+'').prop("checked") ? 1 : 0;
        envarray.push(tmparray.join(','))
    }
    $("<input/>").attr({"type":"hidden", "name":"env_list"})
            .val(envarray.join(";")).appendTo($("#env_body"));
    //拼接envlist
    num = parseInt($("#port_list_len").val())
    $("input[name='port_list']").remove();
    var portarry = new Array()
    for (var i = 1; i <= num; i++) {
        var tmparray = new Array(5)
        var tmpname = "port_list_"+ i + "_container_port";
        if (typeof($('#'+tmpname+'')) === 'undefined') {
            continue;
        }
        if(!PORT_REG.test($('#'+tmpname+'').val())){
            swal("端口不合法")
            return false;
        }
        tmparray[0] = $('#'+tmpname+'').val();
        tmpname = "port_list_"+ i + "_protocol";
        tmparray[1] = $('#'+tmpname+'').val();
        tmpname = "port_list_"+ i + "_port_alias";
        if(!ENV_NAME_REG.test($('#'+tmpname+'').val())){
            swal("端口别名不合法")
            return false;
        }
        tmparray[2] = $('#'+tmpname+'').val();
        tmpname = "port_list_"+ i + "_is_inner_service";
        tmparray[3] = $('#'+tmpname+'').prop("checked") ? 1 : 0;
        tmpname = "port_list_"+ i + "_is_outer_service";
        tmparray[4] = $('#'+tmpname+'').prop("checked") ? 1 : 0;
        portarry.push(tmparray.join(','));
    }
    $("<input/>").attr({"type":"hidden", "name":"port_list"})
            .val(portarry.join(";")).appendTo($("#port_body"));
    return true;
}



