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
})