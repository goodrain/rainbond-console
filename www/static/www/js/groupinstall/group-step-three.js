$(function(){

    $(".tablink a").eq(0).addClass("sed");
    $("section.app-box").eq(0).show();
    $(".tablink a").click(function () {
        $(".tablink a").removeClass("sed");
        $(".tablink a").eq($(this).index()).addClass("sed");
        $("section.app-box").hide();
        $("section.app-box").eq($(this).index()).show();
    });
   
    
});