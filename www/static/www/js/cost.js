$(function(){
    $('.change').on('click',function(){
        if($(this).parent().find('span').html() == "预付费")
        {
            $(this).parent().find('span').html("后付费");
//				弹出层，告知修改成功
            alert("修改成功");
        }
        else{
            $(this).parent().find('span').html("预付费");
//				弹出层，选择购买配置，付费
            alert("请选择购买的配置");
        }
    })
});