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
