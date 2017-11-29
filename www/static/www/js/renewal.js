function toDecimal2(x){
    var f = parseFloat(x);
    if (isNaN(f)) {
        return false;
    }
    var f = Math.round(x * 100) / 100;
    var s = f.toString();
    var rs = s.indexOf('.');
    if (rs < 0) {
        rs = s.length;
        s += '.';
    }
    while (s.length <= rs + 2) {
        s += '0';
    }
    return s;
}
$(function(){
    $("input.fn-range").bind("input propertychange", function() { 
        var thisInput = $(this);
        var thisVal = $(this).val();
        var thisMoney = $(this).attr("data-money");
        var monString = "";
        var moneyMouth =  0;
        var yearnum,monthnum,monthmid;
        var timesbox =$(this).attr("data-times");
        var timesArr = timesbox.split(" ");
        var timesArrOne = timesArr[0].split("-");
        if(Number(thisVal) >=12 && Number(thisVal) < 24){
        	moneyMouth = 12;
        	monString = "1年";
        	yearnum = Number(timesArrOne[0])+1;
        	monthnum = Number(timesArrOne[1]);
        }else if(Number(thisVal) >= 24){
        	moneyMouth = 24;
        	monString = "2年";
        	yearnum = Number(timesArrOne[0])+ 2;
        	monthnum = Number(timesArrOne[1]);
        }else{
        	moneyMouth = Number(thisVal);
        	monString = thisVal + "月";
        	monthmid = Number(thisVal) + Number(timesArrOne[1]);
        	if(monthmid>12){
        		yearnum = Number(timesArrOne[0])+1;
        		monthnum = monthmid -12;
        	}else{
        		yearnum = Number(timesArrOne[0]);
        		monthnum = monthmid;
        	}
        }
        var mainMoney = (thisMoney*moneyMouth*24*30).toFixed(2);
        var timeStr = String(yearnum) + "-" + String(monthnum) + "-" + timesArrOne[2] + " " + timesArr[1];
        $(thisInput).css( 'background-size', thisVal/24*100 + '% 100%' ); 
        $(thisInput).parent().next("span").html(monString);
        $(thisInput).parent().parent(".input-range-box").next("p.fn-app-pay").find("cite").html(toDecimal2(mainMoney));
        $(thisInput).parent().parent(".input-range-box").parent(".content-tab").find("em.fn-times").html(timeStr);
        var mainnum = 0;
        $(".fn-app-pay").each(function(){
            var thisNum = Number($(this).find("cite").html());
            mainnum = mainnum + thisNum;
        }); 
        $("#main-pay").find("cite").html(toDecimal2(mainnum));
    });

    //分页
    var paynum = $("#page-box").find(".fn-pages").length;
    var pagenum = Math.ceil(paynum/10);
    var pagestr = "";
    for(var i=1;i<=pagenum;i++){
    	pagestr += '<a>' + i + '</a>';
    }
    $("#disguise-pages").html(pagestr);
    $("#disguise-pages").find("a").eq(0).addClass("active");
    if(pagenum == 0){
    	$("#pagetips").show();
    	$("#main-pay").hide();
    	$("#paybtn").hide();
    }else{
    	$("#pagetips").hide();
    	$("#main-pay").show();
    	$("#paybtn").show()
    }
    if(paynum > 10){
    	$("#page-box").find(".fn-pages").each(function(i){
    		if(i>9){
    			$(this).hide();
    		}
    	});
    }
    $("#disguise-pages a").click(function(){
    	var index = $(this).index();
    	$("#disguise-pages a").removeClass("active");
    	$(this).addClass("active");
    	var minindex = index*10;
    	var maxindex = (index+1)*10;
    	$(".fn-pages").hide();
    	$("#page-box").find(".fn-pages").each(function(i){
    		if( i < maxindex && i>= minindex){
    			$(this).show();
    		}
    	});
    });
    //分页
	$("#paybtn").click(function(){
		var jsonArr = [];
		$("input.fn-range").each(function(){
			var jsonbox = {};
			var id = $(this).attr("data-id");
			var monthnum = $(this).val();
			if(Number(monthnum) != 0 ){
				if(Number(monthnum) >=12 && Number(monthnum) < 24){
					monthnum = "12";
				}
				if(Number(monthnum) >= 24){
					monthnum = "24";
				}
				jsonbox["service_id"] = id;
				jsonbox["month_num"] = monthnum;
				jsonArr.push(jsonbox);
			}
		});
		if(jsonArr.length == 0){
			swal("请选择包月时长");
		}else{
			console.log(jsonArr);
			var totalMoney = $("#main-pay").find("cite").html();
			console.log(totalMoney);
			swal({
				title: "是否从账户中扣除"+totalMoney+"元",
				type: "warning",
				showCancelButton: true,
				confirmButtonColor: "#DD6B55",
				confirmButtonText: "确定",
				cancelButtonText: "取消",
				closeOnConfirm: false,
				closeOnCancel: false
			}, function (isConfirm) {
				if (isConfirm) {
					var tenantName = $("#tenantName").val();
					//ajax
					$.ajax({
						type: "POST",
						url: "/apps/"+tenantName+"/batch-renew/",
						data: {
							"data": JSON.stringify(jsonArr)
						},
						cache: false,
						beforeSend: function (xhr, settings) {
							var csrftoken = $.cookie('csrftoken');
							xhr.setRequestHeader("X-CSRFToken", csrftoken);
						},
						success: function (data) {
							if (data["ok"]){
								swal("操作成功");
								window.location.href = window.location.href;
							}else{
								swal(data['msg']);
							}

						},
						error: function () {
							swal("系统异常");
						}
					});
					//ajax
				} else {
					swal.close();
				}
			});


		}
	});
});