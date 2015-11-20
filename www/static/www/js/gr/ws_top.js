(function ($) {
    $(document).ready(function () {
        var region = $.cookie('region');
        var tenantName = $('#mytags').attr('tenant');
        var serviceAlias = $('#mytags').attr('service');
        var topic = tenantName + "." + serviceAlias + '.statistic';

        extPushWebSocketClient.prototype = {
            onMessage : function(msg) {
                event = $.parseJSON(msg);
                console.log(event);
                update_table(event);
            }
        }

        var connect = new extPushWebSocketConnect('wss://mpush-' + region + '.goodrain.com:6060/websocket');
        connect.init(new extPushWebSocketClient(), topic, "submsg", "submsg","123456789","987654321");

        function update_table (event) {
          var columns = [];
          $('#rtm-' + event.name + ' thead th').each(function() {
                var name = $(this).attr("name");
                columns.push(name);
            }
          )
          
          var table_body = []
          for (var o in event.data) {
            table_body.push('<tr>');
            for (var n in columns) {
              value = event.data[o][columns[n]];
              table_body.push('<td>' + value + '</td>')
            }    
            table_body.push('</tr>');
          }
          
          var tbody = table_body.join("");
          $('#rtm-' + event.name + ' tbody').html(tbody);
        }
    });
})(jQuery);