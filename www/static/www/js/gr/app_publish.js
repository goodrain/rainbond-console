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
    });});

$(document).ready(
  function () {
      $('.select-all-envs').prop('checked', true);
      $('.env-select').prop('checked', true);
      $('.env-select').closest('tr').addClass('warning');
  }
);
