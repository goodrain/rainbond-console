(function($){
    var csrftoken = $.cookie('csrftoken');
    var tenantName = $('#mytags').attr('tenant');
    var serviceAlias = $('#mytags').attr('service');
    post_url = '/ajax/' + tenantName + '/' + serviceAlias + '/graph';

    default_start = $('#graph-period').children('option:selected').val();
    getGraphs(default_start);

    $('#graph-period').on('change',function() {
          var start = $(this).children('option:selected').val();
          getGraphs(start);
    });

    function getGraphs(start) {
      $('.graph').each(function() {
        var graph_id = $(this).attr('id');
          $.ajax({
            url: post_url,
            method: "POST",
            data: {"csrfmiddlewaretoken":csrftoken, "graph_id":graph_id, "start": start},
            success: function (event) {
                makeChart(graph_id, event, start);
            },
                
            statusCode: {
              403: function(event) {
                swal("你没有此权限！");
              }
            },
                
          });
      });
    };

    function makeChart(graph_id, event, start) {
      var data = event.data;
      nv.addGraph(function() {
        var chart = nv.models.stackedAreaChart()
          .x(function(d) { return d[0] })
          .y(function(d) { return d[1] })
          .color(d3.scale.category10().range())
          .useInteractiveGuideline(false)
          .showControls(false)
          ;
      
        chart.xAxis
          .axisLabel(event.xAxisLabel)
          .tickFormat(function(d) {
            return d3.time.format('%X')(new Date(d))
          });
      
        chart.yAxis
          .axisLabel(event.yAxisLabel)
          .tickFormat(d3.format(event.yAxisFormat))
          ;

        chart.noData("没有可展示的数据");

        if (start=='15m-ago') {
          chart.showXAxis(false);
        }

        d3.select('#' + graph_id + ' svg')
          .datum(data)
          .transition().duration(500)
          .call(chart)
          ;
  
        //nv.utils.windowResize(chart.update);
        if (start!='realtime') {
          setInterval(function() {
            $.post(
              post_url,
              {"csrfmiddlewaretoken":csrftoken, "graph_id":graph_id, "start": start},
              function (update_event) {
                data = update_event.data;
                chart.update();
              }
            );
          }, 60000);
        }

        return chart;
      });
    }

    /*
    nv.addGraph(function() {
      var chart = nv.models.stackedAreaChart()
        .x(function(d) { return d[0] })
        //adjusting, 100% is 1.00, not 100 as it is in the data
        .y(function(d) { return d[1] })
        .color(d3.scale.category10().range())
        .useInteractiveGuideline(false)
        .showControls(false)
        ;
    
      chart.xAxis
        .axisLabel('')
        .tickFormat(function(d) {
          return d3.time.format('%X')(new Date(d))
        });
    
      chart.yAxis
        .axisLabel('unit: MB')
        .tickFormat(d3.format(',.2f'))
        ;

      d3.select('#disk-stat svg')
        .datum(data2)
        .transition().duration(500)
        .call(chart)
        ;
    
      nv.utils.windowResize(chart.update);
    
      return chart;
    });
    */

})(jQuery);