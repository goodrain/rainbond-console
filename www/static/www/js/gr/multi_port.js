(function ($) {
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
                    var outer_port_type = $("#outer_port_setting").val();
                    if (state) {
                        if (port_switch.attr("name") == "inner") {
                            return;
                        }
                        if (outer_port_type == "one_outer") {
                            // 其他的open全部设置为disabled
                            $('.switch-box[name="outer"]').each(function () {
                                $(this).bootstrapSwitchs('disabled', true);
                            });
                            port_switch.bootstrapSwitch('disabled', false);
                        }
                        else {
                            $('.switch-box[name="outer"]').each(function () {
                                $(this).bootstrapSwitchs('disabled', false);
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
                } else {
                    showMessage(res.info);
                    port_switch.bootstrapSwitch('state', !state, true);
                }
            }, 'json');
        }
    );

      //显示端口明细
      $('.port-arrow a').click(function(event) {
        fold = $(this).attr('fold');
        port_show = $(this).attr('port');
        if (fold == 'yes') {
          $(this).attr('fold', 'no');
          $(this).children('i').removeClass('fa-chevron-circle-right').addClass('fa-chevron-circle-down');
          curr_tr =  $(this).closest('tr');
          make_port_detail(curr_tr, port_show);
        } else {
          $(this).attr('fold', 'yes');
          $(this).children('i').removeClass('fa-chevron-circle-down').addClass('fa-chevron-circle-right');
          /*next_tr = $(this).closest('tr').next('tr');
          if (next_tr.hasClass('port-detail')) {
            next_tr.remove();
          }*/
          $("#"+port_show).html("")
          /*var next_table = $(this).closest('tr').parents('table').next();
          if (next_table.hasClass('port-detail')) {
            next_table.remove();
          }*/
        }
      });


      function make_port_detail (curr_tr, port_show) {
        
        url = '/ajax/' + tenantName + '/' + serviceAlias + '/ports/' + curr_tr.attr('port');
        $.get(url, function (event) {
          var next_tr = '<tr class="port-detail">';
          if (event.environment) {
            next_tr = next_tr + make_envs_html(event.environment);
          }
          if (event.outer_service) {
            next_tr = next_tr + make_outer_html(event.outer_service);
          }
          next_tr = next_tr + '</tr>';
          // curr_tr.parents('table').after(next_tr);
          $("#"+port_show).html('<table class="table table-striped table-advance table-hover port-detail">' + next_tr + '</body>')
          //curr_tr.parents('table').after('<table class="table table-striped table-advance table-hover port-detail">' + next_tr + '</body>');
        });
      }

      function make_envs_html(data) {
        var prefix = '<td class="details" colspan="9"><table><thead><tr><th>说明</th><th>变量名</th><th>变量值</th><th></th></tr></thead><tbody>';
        var suffix = '</tbody></table></td>';
        var body = '';
        for (var order in data) {
          body = body + '<tr><td>' + data[order].desc + '</td><td>' + data[order].name + '</td><td>' + data[order].value + '</td></tr>';
        }
        return prefix + body + suffix;
      }

      function make_outer_html(data) {
        var prefix = '<td class="details" colspan="3"><table><tbody>';
        var suffix = '</tbody></table></td>';
        var body = '<tr><td>访问地址</td><td>' + data.domain + '</td><td>' + data.port + '</td></tr>';
        return prefix + body + suffix;
      }


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
        var msg = '<tr colspan=7></tr>'
        msg = msg + '<tr>'
        msg = msg + '<td></td>'
        msg = msg + '<td><input name="port_port" value=""></td>'
        msg = msg + '<td><select name="port_protocol"><option value="http">http</option><option value="stream">stream</option></select></td>'
        msg = msg + '<td><input name ="port_alias" value=""></td>'
        //msg = msg + '<td><select name="port_inner"><option value="0">关闭</option></select></td>'
        //msg = msg + '<td><select name="port_outter"><option value="0">关闭</option></select></td>'
        msg = msg + '<td><div class="btn-toolbar" role="toolbar">' + 
              '<div class="btn-group" role="group">' + 
                '<button type="button" class="port-save btn btn-success btn-xs" "><i class="fa fa-check"></i></button>' +
              '</div>' + 
              '<div class="btn-group" role="group">' + 
                '<button type="button" class="port-cancel btn btn-danger btn-xs" "><i class="fa fa-times"></i></button></td>' +
              '</div>' + 
            '</div></td>'
        msg = msg + '</tr>'
        $("#port_open tr:last").after(msg);
        $('.port-cancel').unbind('click').bind('click', port_cancel);
        $('.port-save').unbind('click').bind('click', port_save);
      });

      $('.port-cancel').click(port_cancel);

      $('.port-delete').click(port_delete);

      $('.port-save').click(port_save);

      function port_cancel(event) {
        var cancel_tr = $(this).closest('tr');
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
        var add_tr = $(this).closest('tr');
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
