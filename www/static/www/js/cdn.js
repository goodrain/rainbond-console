$(function(){
    $("button.add_domain").click(function(){
        $("p.input_domain").show();
    });
    $("button.add_sure").click(function(){
        swal("系统异常");
        var str = "<tr><td>"+"123"+"</td>";
        str += "<td>"+456+"</td>";
        str += "<td>"+789+"</td>";
        str += "<td><a class='del_domain'>删除</a></td></tr>";
        $(str).appendTo("tbody.domain-box");
        $("p.input_domain").hide();
        $("input.domain_name").val("");
        del_domain();
    });
    $("button.add_cancel").click(function(){
        $("p.input_domain").hide();
        $("input.domain_name").val("");
    });
    del_domain();
    function del_domain(){
        $("a.del_domain").off('click');
        $("a.del_domain").on('click',function(){
            $(this).parents("tr").remove();
        });
    }
    editPort();
    function editPort(){
        $('.edit-port').editable({
            type: 'text',
            pk: 1,
            success: function (data) {

            },
            error: function (data) {
                msg = data.responseText;
                res = $.parseJSON(msg);
                showMessage(res.info);
            },
            ajaxOptions: {
                beforeSend: function(xhr, settings) {
                    xhr.setRequestHeader("X-CSRFToken", $.cookie('csrftoken'));
                    settings.data += '&action=change_port';
                },
            }
            //validate: function (value) {
            //    if (!$.trim(value)) {
            //        return '不能为空';
            //    }
            //    else if($(this).hasClass("enviromentKey"))
            //    {
            //        var variableReg = /^[A-Z][A-Z0-9_]*$/;
            //        if( !variableReg.test($(".editable-input").find("input").val()) )
            //        {
            //            return '变量名由大写字母与数字组成且大写字母开头';
            //        }
            //    }
            //}
        });
    }
})