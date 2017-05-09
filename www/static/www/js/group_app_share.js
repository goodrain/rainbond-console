/**
 * Created by lsy on 2017/4/26.
 */
$(function(){
    $(".tablink a").click(function(){
        var num = $(this).index();
        $(".tablink a").removeClass("sed");
        $(this).addClass("sed");
        $("section.fn-app-box").hide();
        $("section.fn-app-box").eq(num).show();
    });

    FnRange("DiskNum","DiskText","DiskWid",128);
    FnRange("NodeNum","NodeText","NodeWid",1);
    function FnRange(inputid,textid,widid,num){
        var range= document.getElementById(inputid);
        var result = document.getElementById(textid);
        var wid = document.getElementById(widid);
        var maxnum = range.getAttribute("max");
        cachedRangeValue = /*localStorage.rangeValue ? localStorage.rangeValue :*/ num;
        // 检测浏览器
        var o = document.createElement('input');
        o.type = 'range';
        if ( o.type === 'text' ) alert('不好意思，你的浏览器还不够酷，试试最新的浏览器吧。');
        range.value = cachedRangeValue;
        wid.style.width = (range.value-num)/(maxnum-num)*100 + "%";
        var arr = [];
        var value_min = $("#DiskNum").attr("min");
        var value_max = $("#DiskNum").attr("max");
        var next = value_min;
        var num = 0;
        while(next<=value_max){
            next = value_min * Math.pow(2,num);
            arr.push(next);
            num++;
        }
        range.addEventListener("mouseup", function() {
            if(inputid == "DiskNum"){
                for( var i = 0;i<arr.length-1;i++ )
                {
                    if( range.value >= arr[i] && range.value < arr[i+1] )
                    {
                        var size = arr[i];
                        //$("#OneMemoryWid").attr("data-size",size);
                        if( size < 1024 )
                        {
                            result.innerHTML = size + "M";
                        }
                        else{
                            result.innerHTML = parseInt(size/1024) + "G";
                        }
                    }
                }
            }else{
                result.innerHTML = range.value;
            }
            wid.style.width = (range.value-num)/(maxnum-num)*100 + "%";
            //alert("你选择的值是：" + range.value + ". 我现在正在用本地存储保存此值。在现代浏览器上刷新并检测。");
            //localStorage ? (localStorage.rangeValue = range.value) : alert("数据保存到了数据库或是其他什么地方。");
            //result.innerHTML = range.value;
        }, false);
        // 滑动时显示选择的值
        range.addEventListener("input", function() {
            if(inputid == "DiskNum"){
                for( var i = 0;i<arr.length-1;i++ )
                {
                    if( range.value >= arr[i] && range.value < arr[i+1] )
                    {
                        var size = arr[i];
                        //result.setAttribute("data-size",size);
                        if( size < 1024 )
                        {
                            result.innerHTML = size + "M";
                        }
                        else{
                            result.innerHTML = parseInt(size/1024) + "G";
                        }
                    }
                }
            }else{
                result.innerHTML = range.value;
            }
            wid.style.width = (range.value-num)/(maxnum-num)*100 + "%";

        }, false);
    }
});