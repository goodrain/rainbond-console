$(function(){
	//提交信息
    $("#nextstep").click(function(){
    	var oVal = $("#mirror-address").val();
    	///
    	$.ajax({
            type: "post",
            url: "",
            data: {
            	"mirror_Address" : oVal
            },
            catch: false,
            beforeSend: function (xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function (msg) {
                var result = msg;
                
            },
            error: function () {
                console.log("提交失败！");
            }
        })
        ///
    });
 	//提交文件
 	$("#nextcomposestep").click(function(){
 		var formData = new FormData($("#myForm")[0]);
 		$.ajax({  
                url : url,  
                type : 'POST',  
                data : formData,  
                processData : false,  
                contentType : false,  
                beforeSend: function (xhr, settings) {
                    var csrftoken = $.cookie('csrftoken');
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                },
                success : function(responseStr) {  
                                     
                },  
                error : function(responseStr) {  
                   
                }  
            });  
 	});
});










