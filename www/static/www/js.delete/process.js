$(function(){
	/*  正则表达式 */

	//01
	var onoff = true;
    $("#infor").click(function(){
    	if(onoff){
    		$(this).next('div.show-box').hide();
    		$(this).find('em').addClass('glyphicon-triangle-bottom').removeClass('glyphicon-triangle-top');
    		onoff = false;
    	}else{
    		$(this).next('div.show-box').show();
    		$(this).find('em').addClass('glyphicon-triangle-top').removeClass('glyphicon-triangle-bottom');
    		onoff = true;
    	}
    });

    //02
	var oonooff = true;
    $("#renew").click(function(){
    	if(oonooff){
    		$(this).next('div.show-box').hide();
    		$(this).find('em').addClass('glyphicon-triangle-bottom').removeClass('glyphicon-triangle-top');
    		oonooff = false;
    	}else{
    		$(this).next('div.show-box').show();
    		$(this).find('em').addClass('glyphicon-triangle-top').removeClass('glyphicon-triangle-bottom');
    		oonooff = true;
    	}
    });


});