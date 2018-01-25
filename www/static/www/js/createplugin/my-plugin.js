$(function(){

	var Msg = window.gWidget;
	var statusMap = {
		'building' : {
			text: '构建中'
		},
		'build_fail': {
			text: '构建失败'
		},
		'build_success': {
			text: '构建成功'
		},
		'unbuild': {
			text: '未构建'
		},
		'time_out': {
			text: '构建超时'
		}
	}

    var controller = {
    	init:function(){
    		var self = this;
    		this.bind();
    		//this.checkStatus()
    	},
    	buildPlugin: function(plugin_id){
    		var self = this;
    		var tenantName = $('[name=tenantName]').val();
			return http({
	            url: '/plugins/'+tenantName+'/'+plugin_id+'/build',
	            type: 'post'
	        }).done(function(data){
	            Msg.success("操作成功");
	            //self.checkStatus(false);
	        })
		},
    	//轮询检测状态
		checkStatus: function (loop=true){
			var self = this;
			var tenantName = $('[name=tenantName]').val();
			return http({
				url: '/ajax/'+tenantName+'/plugin/status',
				type: 'get',
				isTipError: false,
				showLoading: false
			}).done(function(data){
				var list = data.list || [];
				for(var i=0;i<list.length;i++){
					var plugin = list[i];
					var $plugin = $('[data-id='+plugin.plugin_id+']');
					if(plugin.build_version){
						$plugin.find('.js-build-version').html(plugin.build_version);
					}
					
				}
			}).always(function(){
				if(loop){
					setTimeout(function(){
						self.checkStatus();
					}, 6000)
				}
				
			})
		},
    	bind:function(){
    		var self = this;
    		$('body').delegate('.js-build-plugin', 'click', function(e){
    			var plugin_id = $(this).parents('tr').attr('data-id');
    			if(plugin_id){
    				self.buildPlugin(plugin_id)
    			}else{
    				Msg.warning("数据异常")
    			}
    		})
    	}
    }

    controller.init();

    $("#install_market_plugin").click(function () {
        var tenantName = $('[name=tenantName]').val();
        var data_map = [
            {
                "share_id": "e003ce85b65d477896ee99798c3d8a54",
                "share_version": "20180117175939"
            },
			{
                "share_id": "82ce36bfd4044931adaa484ed8e75c12",
                "share_version": "20180117184912"
            }
        ]

        for (i = 0; i < data_map.length; i++) {
            var kv = data_map[i];
            install_plugin(tenantName, kv["share_id"], kv["share_version"])
        }
    });

});

function install_plugin(tenant_name,share_id, share_version) {
    var query_data = {
            "share_id": share_id,
			"share_version":share_version
        }

	$.ajax({
        type: "post",
        url: "/ajax/" + tenant_name + "/plugin/install",
        data: JSON.stringify(query_data),
        cache: false,
        beforeSend: function (xhr, settings) {
            var csrftoken = $.cookie('csrftoken');
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function (msg) {
            window.location.href = window.location.href
        },
        error: function () {
            swal("系统异常,请重试");
        }
    });

}