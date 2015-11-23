(function ($) {
    $(document).ready(function () {
        var region = $.cookie('region');
        var tenantName = $('#mytags').attr('tenant');
        var serviceAlias = $('#mytags').attr('service');
        var topic = tenantName + "." + serviceAlias + '.statistic';

        extPushWebSocketClient.prototype = {
            onMessage : function(msg) {
                event = $.parseJSON(msg);
                update_table(event);
            }
        }

        var connect = new extPushWebSocketConnect('wss://mpush-' + region + '.goodrain.com:6060/websocket');
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
            table_body.push('<tr>');
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
    });
})(jQuery);