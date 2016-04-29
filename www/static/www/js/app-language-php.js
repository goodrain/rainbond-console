$(function() {
	$("#service_version").bind("change", function(){
        //获取当前选择的版本
        var version = $(this).val();
        if (version >= "7" || version <= "5.3.29") {//这里为js的string比较
            $("input[php7]").each(function(){
                $(this).attr('disabled', 'disabled');
            });
        } else {
            $("input[php7]").each(function(){
                $(this).removeAttr('disabled');
            });
        }
	});
});




