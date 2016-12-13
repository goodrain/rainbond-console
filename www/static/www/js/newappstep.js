$(function(){
	// 滑块 开始 
	function FnRange(inputid,textid,widid,num,maxnum){
		var range= document.getElementById(inputid);
		var result = document.getElementById(textid);
		var wid = document.getElementById(widid);
		cachedRangeValue = /*localStorage.rangeValue ? localStorage.rangeValue :*/ num; 
		// 检测浏览器
		var o = document.createElement('input');
	    o.type = 'range';
	    if ( o.type === 'text' ) alert('不好意思，你的浏览器还不够酷，试试最新的浏览器吧。');
	    range.value = cachedRangeValue;
	    result.innerHTML = cachedRangeValue;
	    wid.style.width = range.value/maxnum*100 + "%";
	    range.addEventListener("mouseup", function() {
	    	result.innerHTML = range.value;
	        wid.style.width = range.value/maxnum*100 + "%";
	        //alert("你选择的值是：" + range.value + ". 我现在正在用本地存储保存此值。在现代浏览器上刷新并检测。");
	        //localStorage ? (localStorage.rangeValue = range.value) : alert("数据保存到了数据库或是其他什么地方。");
	        //result.innerHTML = range.value;
	    }, false);

	    // 滑动时显示选择的值
	    range.addEventListener("change", function() {
	        result.innerHTML = range.value;
	        wid.style.width = range.value/maxnum*100 + "%";
	    }, false);
	}
    
    FnRange("OneMemory","OneMemoryText","OneMemoryWid",256,2048);
    FnRange("NodeNum","NodeText","NodeWid",1,10);
    FnRange("TimeLong","TimeLongText","TimeLongWid",9,12);

    // 滑动框 结束

    // 输入框输入样式

    // 01 输入用户名
    $('#create_name').blur(function(){
        var appName = $(this).val();
        //var checkReg = /^[a-z][a-z0-9-]*[a-z0-9]$/;
        //var result = true;
        if(appName == ""){
            $('#create_name_notice').slideDown();
            return;
        }else{
            $('#create_name_notice').slideUp();
        }
    });
    // 01 end 

    //03 公开项目
    $('#service_code_url').blur(function(){
        var appurl= $(this).val();
        if(appurl == ""){
            $('#service_code_url_tips').slideDown();
            return;
        }else{
            $('#service_code_url_tips').slideUp();
        }
    });
    //03 公开项目
    //04 自建Git
    $('#my_git_url').blur(function(){
        var myurl= $(this).val();
        if(myurl == ""){
            $('#my_git_url_tips').slideDown();
            return;
        }else{
            $('#my_git_url_tips').slideUp();
        }
    });
    //04 自建Git
    // github 
});










