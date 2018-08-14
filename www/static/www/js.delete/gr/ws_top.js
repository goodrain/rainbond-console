(function ($) {
    $(document).ready(function () {
        var csrftoken = $.cookie('csrftoken');
        var tenantName = $('#mytags').attr('tenant');
        var serviceAlias = $('#mytags').attr('service');
        var region = $.cookie('region');
        var topic = $('#mytags').attr('ws-topic');
        var websocketUrl = $("#websocketUrl").val()

        extPushWebSocketClient.prototype = {
            onMessage : function(msg) {
                event = $.parseJSON(msg);
                update_table(event);
            }
        }

        var connect = new extPushWebSocketConnect(websocketUrl);
        connect.init(new extPushWebSocketClient(), topic, "submsg", "submsg","123456789","987654321");

        function update_table (event) {
          var columns = [];
          $('#rtm-' + event.name + ' thead th').each(function() {
                var name = $(this).attr("name");
                var align = $(this).attr("class");
                var item = {"name": name, "align": align};
                columns.push(item);
            }
          )
          
          var table_body = []
          for (var o in event.data) {
            table_body.push('<tr style="word-break: break-all;">');
            for (var n in columns) {
              value = event.data[o][columns[n].name];
              table_body.push('<td class="' + columns[n].align + '">' + value + '</td>')
            }    
            table_body.push('</tr>');
          }
          
          var tbody = table_body.join("");
          $('#rtm-' + event.name + ' tbody').html(tbody);
          $('#rtm-' + event.name).closest('section').find('span.rtm-update-time').html("更新时间: " + event.update_time);
        }

        setTimeout(function() {update_stat();}, 200);
        setInterval(function() {update_stat();}, 30000);
        post_url = '/ajax/' + tenantName + '/' + serviceAlias + '/graph';

        function update_stat() {
          $('#realtime-stat .js-realtime-type').each(function() {
            var graph_id = $(this).attr('id');
              $.ajax({
                url: post_url,
                method: "POST",
                data: {"csrfmiddlewaretoken":csrftoken, "graph_id":graph_id, "start": "3m-ago", "last": true},
                success: function (event) {
                    $('#' + graph_id).html(event.value);
                },
                    
                statusCode: {
                  403: function(event) {
                    swal("你没有此权限！");
                  }
                },
                    
              });
          });
        }
    });
})(jQuery);