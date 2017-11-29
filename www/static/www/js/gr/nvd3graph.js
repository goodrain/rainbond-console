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

    setInterval(function() {
        var start = $('#graph-period').children('option:selected').val();
        getGraphs(start);
      }, 60000
    );

    function getGraphs(start) {
      $('.graph').each(function() {
        var graph_id = $(this).attr('id');
          $.ajax({
            url: post_url,
            method: "POST",
            data: {"csrfmiddlewaretoken":csrftoken, "graph_id":graph_id, "start": start},
            success: function (event) {
                console.log(event);
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
      nv.addGraph(function() {
        var chart = nv.models.stackedAreaChart()
          .x(function(d) { return d[0] })
          .y(function(d) { return d[1] })
          .xScale(d3.time.scale())
          .color(d3.scale.category10().range())
          .useInteractiveGuideline(true)
          .showControls(false)
          ;

        var tickMultiFormat = d3.time.format.multi([
            ["%H:%M", function(d) { return d.getMinutes(); }], // not the beginning of the hour
            ["%H:%M", function(d) { return d.getHours(); }], // not midnight
            ["%m/%d", function(d) { return d.getDay() && d.getDate() != 1; }],
            ["%m/%d", function(d) { return d.getDate() != 1; }],
            ["%Y/%m", function(d) { return d.getMonth(); }], // not Jan 1st
            ["%Y", function() { return true; }]
        ]);
      
        chart.xAxis
          //.axisLabel(event.xAxisLabel)
          .tickFormat(function (d) { return tickMultiFormat(new Date(d)); });
      
        chart.yAxis
          .axisLabel(event.yAxisLabel)
          .tickFormat(d3.format(event.yAxisFormat))
          ;

        chart.noData("没有可展示的数据");

        $('#' + graph_id + ' svg').empty();

        var svgElem = d3.select('#' + graph_id + ' svg');
        svgElem
          .datum(event.data)
          .transition()
          .call(chart);

        var tsFormat = d3.time.format('%m/%d %H:%M');
        var contentGenerator = chart.interactiveLayer.tooltip.contentGenerator();
        var tooltip = chart.interactiveLayer.tooltip;
        tooltip.contentGenerator(function (d) { d.value = d.initial; return contentGenerator(d); });
        tooltip.headerFormatter(function (d) { return tsFormat(new Date(d)); });

        nv.utils.windowResize(chart.update);

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