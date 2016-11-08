(function ($) {
      //加载显示 隐藏绑定域名
      $(".fn-outInput").each(function(){
         var inputPort = $(this).closest('tr').attr('port');
         console.log(inputPort);
         if(typeof($(this).attr("checked")) == undefined){
              $("#showLink"+inputPort).hide();
              console.log(inputPort);
         }else{
             $("#showLink"+inputPort).show();
             console.log(inputPort);
         }
      });

      var tenantName = $("#tenant-name").html();
      var serviceAlias = $("#service-alias").html();
      //设定端口对内服务和对外服务的开关
      $('.switch-box').bootstrapSwitch();
      $('.switch-box').on('switchChange.bootstrapSwitch', function(event, state) {
        var port_switch = $(this);
          port = $(this).closest('tr').attr('port');
          port_type = $(this).attr('name'); //inner outer
          alert(state);
          if (state) {
            action = "open_" + port_type;
          } else {
            action = 'close_' + port_type;
          }

            url = '/ajax/' + tenantName + '/' + serviceAlias + '/ports/' + port;
            $.post(url, {csrfmiddlewaretoken: $.cookie('csrftoken'), "action": action}, function (res) {
                if(res.success) {
                    /*
                    //var outer_port_type = $("#outer_port_setting").val();
                    if (state) {
                        if (port_switch.attr("name") == "inner") {
                            return;
                        }
                        if (outer_port_type == "one_outer") {
                            // 其他的open全部设置为disabled
                            
                            port_switch.bootstrapSwitch('disabled', false);
                        }
                        else {
                            $('.switch-box[name="outer"]').each(function () {
                                $(this).bootstrapSwitch('disabled', false);
                            });
                        }
                    } else {
                        if (port_switch.attr("name") == "inner") {
                            return;
                        }
                        // 全部取消disabled
                        $('.switch-box[name="outer"]').each(function () {
                            $(this).bootstrapSwitch('disabled', false);
                        });
                    }
                    */
                    if(state){
                        if (port_switch.attr("name") == "outer"){
                            $("#showLink"+port).show();
                            alert(port);
                        }
                    }else{
                       if (port_switch.attr("name") == "outer"){
                           $("#showLink"+port).hide();
                           alert(port);
                       }
                    }
                } else {
                    showMessage(res.info);
                    port_switch.bootstrapSwitch('state', !state, true);
                }
            }, 'json');
        }
    );
      
      //显示端口明细
      
      // 显示网址 -- ww start
      
      $(".fn-sever-link").each(function(){
           this_port_show = $(this).attr('port');
           Fn_make_port_detail (this_port_show);
           Fn_make_envs_html(this_port_show);
      });
       
     function Fn_make_envs_html(port_show) {
        url = '/ajax/' + tenantName + '/' + serviceAlias + '/ports/' + port_show;
        var serlink = '';
        $.get(url, function (event) {
            if(event.environment.length != 0){
               console.log(event.environment);
               console.log(event.environment[0]);
               console.log(event.environment[0].value); 
               serlink = event.environment[0].value + ':' + event.environment[1].value;
            }
            $("#sever_show_" + port_show).find("a").html(serlink).attr("href",serlink);
        });
      }

      function Fn_make_port_detail (port_show) {
        url = '/ajax/' + tenantName + '/' + serviceAlias + '/ports/' + port_show;
        $.get(url, function (event) {
          if (event.outer_service) {
            var next_tr = event.outer_service.domain + ':' + event.outer_service.port;
          }
          $("#port_show_" + port_show).find("a").html(next_tr).attr("href",next_tr);
        });
      }

      /*
      function Fn_make_outer_html(data) {
        var body =  data.domain;
        return body;
      }
      */
      // 显示网址 -- ww end 

      //即时修改端口别名和协议类型
      $(document).ready(function() {
        $('.edit-port-alias').editable({
          type: 'text',
          pk: 1,
          error: function (data) {
            msg = data.responseText;
            res = $.parseJSON(msg);
            showMessage(res.info);
          },  
          ajaxOptions: {
              beforeSend: function(xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", $.cookie('csrftoken'));
                settings.data += '&action=change_port_alias';
              },
          }
        });
        $('.edit-protocol').editable({
          type: 'select',
          source: [{value: "http", text: 'http'}, {value: "stream", text: 'stream'}],
          pk: 1,
          error: function (data) {
            msg = data.responseText;
            res = $.parseJSON(msg);
            showMessage(res.info);
          },
          ajaxOptions: {
              beforeSend: function(xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", $.cookie('csrftoken'));
                settings.data += '&action=change_protocol';
              },
          }
        });
        $('.edit-port').editable({
          type: 'text',
          pk: 1,
          success: function (data) {
            window.location.reload();
          },
          error: function (data) {
            msg = data.responseText;
            res = $.parseJSON(msg);
            showMessage(res.info);
          },  
          ajaxOptions: {
              beforeSend: function(xhr, settings) {
                xhr.setRequestHeader("X-CSRFToken", $.cookie('csrftoken'));
                settings.data += '&action=change_port';
              },
          }
        });
      });

      //自定义环境变量
      $('#add_service_attr').click(function(event) {
        var msg = '<tr>'
        msg = msg + '<input type="hidden" name="attr_id" value="0">'
        msg = msg + '<td><input name="attr_name" type="text" value=""></td>'
        msg = msg + '<td><input name="attr_value" type="text" value=""></td>'
        msg = msg + '<td><input name="name" type="text" placeholder="可以不填写" value=""></td>' +
        '<td><div class="btn-toolbar" role="toolbar">' + 
          '<div class="btn-group" role="group">' + 
            '<button type="button" class="attr-save btn btn-success btn-xs" "><i class="fa fa-check"></i></button>' +
          '</div>' + 
          '<div class="btn-group" role="group">' + 
            '<button type="button" class="attr-cancel btn btn-danger btn-xs" "><i class="fa fa-times"></i></button></td>' +
          '</div>' + 
        '</div></td>'
        msg = msg + '</tr>'
        $("#envVartable tr:last").after(msg);
        $('.attr-cancel').unbind('click').bind('click', attr_cancel);
        $('.attr-save').unbind('click').bind('click', attr_save);
      });

      $('.attr-cancel').click(attr_cancel);

      $('.attr-delete').click(attr_delete);

      $('.attr-save').click(attr_save);

      function attr_cancel(event) {
        var cancel_tr = $(this).closest('tr');
        cancel_tr.remove();
      }

      function attr_delete(event) {
        var dict = {csrfmiddlewaretoken: $.cookie('csrftoken'), "action": "del_attr"};
        var del_tr = $(this).closest('tr');
        attr_name = del_tr.find('.attr_name_field').html();
        dict["attr_name"] = attr_name;

        url = '/ajax/' + tenantName + '/' + serviceAlias + '/custom-env';
        $.post(url, dict, function(res) {
          if (res.success) {
            del_tr.remove();
          }
        });
      }

      function attr_save(event) {
        var dict = {csrfmiddlewaretoken: $.cookie('csrftoken'), "action": "add_attr"};
        var add_tr = $(this).closest('tr');
        add_tr.find('input').each(function() {
          name = $(this).attr("name");
          value = $(this).val();
          dict[name] = value;
        });

        url = '/ajax/' + tenantName + '/' + serviceAlias + '/custom-env';
        $.post(url, dict, function(res) {
          if (res.success) {
            add_tr.find('.btn-toolbar').remove();
          } else {
            showMessage(res.info);
          }
        });
      }
      
      //服务端口新建
      $('#add_service_port').click(function(event) {
        
        var msg = '<table class="addtab"><tr>'
        msg = msg + '<td><span>端口号:</span><input name="port_port" value="" class="tab-port"></td>'
        msg = msg + '<td><span>协议类型:</span><select name="port_protocol"><option value="http">http</option><option value="stream">stream</option></select></td>'
        msg = msg + '<td style="display:none;"><input name ="port_alias" value="" class="tab-alias"></td>'
        msg = msg + '<td><div class="btn-toolbar" role="toolbar">' + 
              '<div class="btn-group" role="group">' + 
                '<button type="button" class="port-save btn btn-success btn-xs" "><i class="fa fa-check"></i></button>' +
              '</div>' + 
              '<div class="btn-group" role="group">' + 
                '<button type="button" class="port-cancel btn btn-danger btn-xs" "><i class="fa fa-times"></i></button></td>' +
              '</div>' + 
            '</div></td>'
        msg = msg + '</tr></table>'
        $("#port_open").append(msg);
        $('.port-cancel').unbind('click').bind('click', port_cancel);
        $('.port-save').unbind('click').bind('click', port_save);
      });

      $('.port-cancel').click(port_cancel);

      $('.port-delete').click(port_delete);

      $('.port-save').click(port_save);

      function port_cancel(event) {
        var cancel_tr = $(this).closest('table');
        cancel_tr.remove();
      }

      function port_delete(event) {
            var dict = {csrfmiddlewaretoken: $.cookie('csrftoken'), "action": "del_port"};
            var del_tr = $(this).closest('tr');
            port = del_tr.attr('port');
            dict["port_port"] = port;
            url = '/ajax/' + tenantName + '/' + serviceAlias + '/custom-port';
            $.post(url, dict, function(res) {
              if (res.success) {
                window.location.href = window.location.href;
              } else {
                showMessage(res.info);
              }
            });
       }

      function port_save(event) {
        var dict = {csrfmiddlewaretoken: $.cookie('csrftoken'), "action": "add_port"};
        var add_tr = $(this).closest('table');
        add_tr.find('input.tab-alias').val('S' + add_tr.find('input.tab-port').val());
        add_tr.find('input').each(function() {
          name = $(this).attr("name");
          value = $(this).val();
          dict[name] = value;
        });

        add_tr.find('select').each(function() {
          name = $(this).attr("name");
          value = $(this).val();
          dict[name] = value;
        });
        
        url = '/ajax/' + tenantName + '/' + serviceAlias + '/custom-port';
        $.post(url, dict, function(res) {
          if (res.success) {
            add_tr.find('.btn-toolbar').remove();
            window.location.href = window.location.href;
          } else {
            showMessage(res.info);
          }
        });
      }
      
   

})(jQuery);

/*
//端口
$(function(){
   //多端口支持
    function muti_outer_port() {
        //var port_type = $("#outer_port_setting").val();
        var tenantName = $("#tenant-name").html();

        var service_alias = $("#service-alias").html();
        var port_type = "";
        if($(".newtab").length == 1){
            port_type = "one_outer";
        }else{
            port_type = "multi_outer";
        }
        $.ajax({
            type: "post",
            url: "/ajax/" + tenantName + "/" + service_alias + "/service-outer-port-type",
            data: "action=change_port_type&port_type=" + port_type,
            catch: false,
            beforeSend: function (xhr, settings) {
                var csrftoken = $.cookie('csrftoken');
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            },
            success: function (msg) {
                var result = msg;
                if (result["status"] == "ok") {
                    console.log("设置成功");
                }else if(result["status"] == "mult_port"){
                    console.log(result["info"]);
                }
                else {
                    console.log("设置失败");
                }
            },
            error: function () {
                console.log("对外端口设置异常,请重试");
            }


        })
    };
    //muti_outer_port();
    
});*/
