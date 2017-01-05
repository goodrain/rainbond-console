$(function(){
    // // //上传compose文件 start
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

    $("#nextcomposestep").click(function(){
        var formData = new FormData($("#myForm")[0]);
		var tenantName = $("#tenantNameValue").val();
		var appname = $("#create_name").val();
		if(appName == ""){
            $('#create_name_notice').slideDown();
            return;
        }else{
            $('#create_name_notice').slideUp();
        }
		upload_url = "/apps/"+tenantName+"/compose-create/"
        $.ajax({  
                url : upload_url,  
                type : 'POST',  
                data : formData,  
                processData : false,  
                contentType : false,
				xhr: function() {
					myXhr = $.ajaxSettings.xhr();
					if(myXhr.upload){
						myXhr.upload.addEventListener('progress', progressHandling, false);
					}
					return myXhr;
				},
                beforeSend: function (xhr, settings) {
                    var csrftoken = $.cookie('csrftoken');
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                },
                success : function(responseStr) { 
					if(responseStr.success){
						window.location.href = "/apps/"+tenantName+"/compose-params?id="+responseStr.compose_file_id

					}else{
						swal("文件上传异常")
					}
                },  
                error : function(responseStr) {  
                   
                }  
            });  
    });
    //
    $("#compose_file").on("change",function(){
        var filePath=$(this).val();
        if(filePath.indexOf("yml")!=-1){
            var arr=filePath.split('\\');
            var fileName=arr[arr.length-1];
            console.log(fileName)
            $(this).next("span").html(fileName);
        }else{
            $(this).next("span").html("请重新上传！");
            return false;
        }
    });
    // // //上传compose文件 end

    // // // 第二步 基本设置 start
    $(".fn-circle").each(function(){
        var this_id= $(this).attr("id");
        $("#"+ this_id +"_MoneyBefore").change(function(){
            var onoff = $("#"+ this_id +"_MoneyBefore").prop("checked");
            if(onoff == true){
                // $(".fn-memory-node").show();
                $("#"+ this_id + "_aft-memory-box").hide();
            }else{
                //$(".fn-memory-node").hide();
                $("#"+ this_id + "_aft-memory-box").show();
            }
            // FnPrice(this_id);
        });
        $("#"+ this_id +"_MoneyAfter").change(function(){
            
            var onoff = $("#"+ this_id +"_MoneyAfter").prop("checked");
            if(onoff == false){
                //$(".fn-memory-node").show();
                $("#"+ this_id +"_aft-memory-box").hide();
            }else{
                //$(".fn-memory-node").hide();
                $("#"+ this_id +"_aft-memory-box").show();
            }
            //FnPrice(this_id);
        });
        $("#"+ this_id +"DiskBefore").change(function(){
            var onoff = $("#"+ this_id +"_DiskBefore").prop("checked");
            if(onoff == true){
                $("#"+ this_id + "_disk_box").show();
                $("#"+ this_id +"_aft-disk-box").hide();
            }else{
                $("#"+ this_id + "_disk_box").hide();
                $("#"+ this_id +"_aft-disk-box").show();
            }
            //FnPrice(this_id);
        });
        $("#"+ this_id +"_DiskAfter").change(function(){
            var onoff = $("#"+ this_id +"_After").prop("checked");
            if(onoff == false){
                $("#"+this_id +"_disk_box").show();
                $("#"+ this_id +"_aft-disk-box").hide();
            }else{
                $("#"+this_id +"_disk_box").hide();
                $("#"+ this_id +"_aft-disk-box").show();
            }
           // FnPrice(this_id);
        });
     });
    
    // // // 第二步 基本设置 end
});
