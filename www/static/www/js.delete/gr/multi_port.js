(function ($) {
      //加载显示 隐藏绑定域名
      var tenantName = $("#tenant-name").html();
      var serviceAlias = $("#service-alias").html();
      var code_from = $("#code_from").html();
      //设定端口对内服务和对外服务的开关
      $('.switch-box').bootstrapSwitch();
      $('.switch-box').on('switchChange.bootstrapSwitch', function(event, state) {
        var port_switch = $(this);
          port = $(this).closest('tr').attr('port');
          port_type = $(this).attr('name'); //inner outer
          if (state) {
            action = "open_" + port_type;
          } else {
            action = 'close_' + port_type;
          }

            url = '/ajax/' + tenantName + '/' + serviceAlias + '/ports/' + port;
            $.post(url, {csrfmiddlewaretoken: $.cookie('csrftoken'), "action": action}, function (res) {
                if(res.success) {
                    window.location.reload();
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
               serlink = event.environment[0].value + ':' + event.environment[1].value;
            }
            $("#sever_show_" + port_show).find("span").html(serlink);
        });
      }

      function Fn_make_port_detail (port_show) {
        url = '/ajax/' + tenantName + '/' + serviceAlias + '/ports/' + port_show;
        $.get(url, function (event) {
           var port_type = $("#service_port_type").val()
           var Protocol_type = $("#edit_protocol_" + port_show).attr("data-value");

          // if($(".fn-out-servce input:checked").length > 1){
            if(port_type == "multi_outer"){
              if(Protocol_type == "http"){
                 var next_tr = port_show + "." + event.outer_service.domain + ':' + event.outer_service.port;
              }else{
                 var next_tr = event.outer_service.domain + ':' + event.outer_service.port;
              }
               var next_tr_href = "http://" + next_tr;
            }else{
               var next_tr = event.outer_service.domain + ':' + event.outer_service.port;
               var next_tr_href = "http://" + next_tr;
            }

            $("#port_show_" + port_show).find("a").html(next_tr).attr("href",next_tr_href);
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
          success: function(data){
              var res = eval(data);
              showMessage(res.info);
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
      // $('.attr-delete').on("click",attr_delete);

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
            // add_tr.find('.btn-toolbar').remove();
              var pk = res.pk;
              var attr_name = res.attr_name;
              var attr_value = res.attr_value;
              var name = res.name;
              var msg = '<tr>';
              msg = msg + '<input type="hidden" name="attr_id" value='+pk+'>';
              msg = msg + '<td class="attr_name_field">'+attr_name+'</td>';
              msg = msg + '<td>'+attr_value+'</td>';
              msg = msg + '<td>'+name+'</td>';
              msg = msg + '<td><button type="button" class="attr-delete btn redbtn btn-xs" >删除</button></td>';
              msg = msg+ '<tr>';
              $("#envVartable tr:last").remove();
              $("#envVartable tr:last").after(msg);
              $('.attr-delete').unbind('click').bind('click', attr_delete);

            // window.location.href = window.location.href;
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
        var prefix = serviceAlias.toUpperCase();
        var language = $("#language").val();
        add_tr.find('input.tab-alias').val(prefix + add_tr.find('input.tab-port').val());
          var flag = true;
        add_tr.find('input').each(function() {
          name = $(this).attr("name");
          value = $(this).val();
          dict[name] = value;
          if(!isNaN(value)){
              if (code_from=="image_manual"){
                  if(value>=1 && value<=65535){
                  }else{
                      showMessage("端口号必须在1~65535之间！");
                      flag = false;
                      return false;
                  }
              }else{
                  // Dockerfile应用端口号
                  if((value>=1025 && value<=65535) || (language == "docker")){
                      
                  }else{
                      showMessage("端口号必须在1025~65535之间！");
                        flag = false;
                      return false;
                  }
              }
          }
          //dict[name] = value;
        });

          if(!flag){
              return false;
          }

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

      /// ww-2016-12-06 多域名绑定 start
      // $(".fn-bind-domain").click(function(){
      //     var protocol = $(this).closest('table');
      //     $(this).next("div.fn-domain-layer").show();
      // });
      // $(".fn-delete-domain").click(function(){
      //     $(this).parent("div.fn-domain-layer").hide();
      //     $(this).parent("div.fn-domain-layer").children("input").prop("value","");
      // });
      /// ww-2016-12-06 多域名绑定 end
})(jQuery);



