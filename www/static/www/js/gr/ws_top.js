(function ($) {
    $(document).ready(function () {
        var region = $.cookie('region');
        var tenantName = $('#mytags').attr('tenant');
        var serviceAlias = $('#mytags').attr('service');
        var topic = tenantName + "." + serviceAlias

        extPushWebSocketClient.prototype = {
            onMessage : function(msg) {
                console.log(msg)
            }
        }
        var connect = new extPushWebSocketConnect('wss://mpush.' + region + '.goodrain.com:6060/websocket');
        connect.init(new extPushWebSocketClient(), topic, "submsg", "submsg","123456789","987654321");
    });
})(jQuery);