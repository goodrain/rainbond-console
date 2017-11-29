(function ($) {
    if (!$.action_report) {
        $.extend({
            action_report: function (jsonlist, fadeout) {
              var alert_class = 'alert-success';
              alert_el = '<div class="alert alert-dismissible" role="alert" align="center"><button type="button" class="close" data-dismiss="alert"><span aria-hidden="true">x</span><span class="sr-only">Close</span></button><strong>'+jsonlist.desc+'</strong>';
              if (!jsonlist.ok) {
                /*
                alert_el = alert_el + '<a class="alert-link collapsed" data-toggle="collapse" data-parent="#accordion" href="#collapseOne" aria-expanded="false" aria-controls="collapseOne"> 点击查看错误报告</a>';
                click_report = '<div id="collapseOne" class="panel-collapse collapse" role="tabpanel" style="height: 0px;"><div class="panel-body">'+jsonlist.reason+'</div></div>';
                alert_el = alert_el + click_report;
                */
                alert_class = 'alert-danger';
              }

              alert_el = alert_el + '</div>';
              $('#action_report').html(alert_el);
              $('#action_report >div.alert').addClass(alert_class);
              if (fadeout >0) {
                $('#action_report >div.alert-success').fadeOut(fadeout);
              }
            }
        });
    }

    if (!$.stringify) {
        $.extend({
            stringify  : function stringify(obj) {
                var t = typeof (obj);
                if (t != "object" || obj === null) {
                    // simple data type
                    if (t == "string") obj = '"' + obj + '"';
                    return String(obj);
                } else {
                    // recurse array or object
                    var n, v, json = [], arr = (obj && obj.constructor == Array);

                    for (n in obj) {
                        v = obj[n];
                        t = typeof(v);
                        if (obj.hasOwnProperty(n)) {
                            if (t == "string") v = '"' + v + '"'; else if (t == "object" && v !== null) v = jQuery.stringify(v);
                            json.push((arr ? "" : '"' + n + '":') + String(v));
                        }
                    }
                    return (arr ? "[" : "{") + String(json) + (arr ? "]" : "}");
                }
            }
        });
    }
})(jQuery);