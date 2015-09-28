(function($){

    /*
    nv.addGraph(function() {
      var chart = nv.models.lineChart()
        .useInteractiveGuideline(true)
        ;
    
      chart.xAxis
        .axisLabel('时间线')
        .tickFormat(d3.format(',r'))
        ;
    
      chart.yAxis
        .axisLabel('')
        .tickFormat(d3.format('.02f'))
        ;
    
      d3.select('#memory-stat svg')
        .datum(data())
        .transition().duration(500)
        .call(chart)
        ;
    
      nv.utils.windowResize(chart.update);
    
      return chart;
    });

    function data() {
      var sin = [],
          cos = [];
    
      for (var i = 0; i < 100; i++) {
        sin.push({x: i, y: Math.sin(i/10)});
        cos.push({x: i, y: .5 * Math.cos(i/10)});
      }
    
      return [
        {
          values: sin,
          key: 'Sine Wave',
          color: '#ff7f0e'
        },
        {
          values: cos,
          key: 'Cosine Wave',
          color: '#2ca02c'
        }
      ];
    }
    */

    var data1 = [
      {
        "key": "memory",
        "values": [[1443431546, 852], [1443431576, 109], [1443431606, 225], [1443431636, 485], [1443431666, 830], [1443431696, 246], [1443431726, 931], [1443431756, 724], [1443431786, 264], [1443431816, 901], [1443431846, 418], [1443431876, 877], [1443431906, 453], [1443431936, 127], [1443431966, 137], [1443431996, 440], [1443432026, 595], [1443432056, 184], [1443432086, 945], [1443432116, 300], [1443432146, 111], [1443432176, 882], [1443432206, 232], [1443432236, 184], [1443432266, 664], [1443432296, 327], [1443432326, 272], [1443432356, 728], [1443432386, 408], [1443432416, 358]]
      }
    ]

    var data2 = [
      {
        "key": "disk",
        "values": [[1443431546, 142], [1443431576, 120], [1443431606, 104], [1443431636, 104], [1443431666, 101], [1443431696, 139], [1443431726, 111], [1443431756, 127], [1443431786, 145], [1443431816, 108], [1443431846, 119], [1443431876, 144], [1443431906, 106], [1443431936, 146], [1443431966, 143], [1443431996, 111], [1443432026, 142], [1443432056, 149], [1443432086, 114], [1443432116, 145], [1443432146, 132], [1443432176, 128], [1443432206, 108], [1443432236, 121], [1443432266, 110], [1443432296, 113], [1443432326, 111], [1443432356, 112], [1443432386, 132], [1443432416, 140]]
      },
    ]


    nv.addGraph(function() {
      var chart = nv.models.cumulativeLineChart()
        .x(function(d) { return d[0] })
        //adjusting, 100% is 1.00, not 100 as it is in the data
        .y(function(d) { return d[1] })
        .color(d3.scale.category10().range())
        .useInteractiveGuideline(true)
        ;
    
      chart.xAxis
        .axisLabel('时间线')
        .tickFormat(function(d) {
          return d3.time.format('%X')(new Date(d))
        });
    
      chart.yAxis
        .axisLabel('unit: MB')
        .tickFormat(d3.format(',r'))
        ;
    
      d3.select('#memory-stat svg')
        .datum(data1)
        .transition().duration(500)
        .call(chart)
        ;

      nv.utils.windowResize(chart.update);
    
      return chart;
    });

    nv.addGraph(function() {
      var chart = nv.models.cumulativeLineChart()
        .x(function(d) { return d[0] })
        //adjusting, 100% is 1.00, not 100 as it is in the data
        .y(function(d) { return d[1] })
        .color(d3.scale.category10().range())
        .useInteractiveGuideline(true)
        ;
    
      chart.xAxis
        .axisLabel('时间线')
        .tickFormat(function(d) {
          return d3.time.format('%X')(new Date(d))
        });
    
      chart.yAxis
        .axisLabel('unit: MB')
        .tickFormat(d3.format(',r'))
        ;

      d3.select('#disk-stat svg')
        .datum(data2)
        .transition().duration(500)
        .call(chart)
        ;
    
      nv.utils.windowResize(chart.update);
    
      return chart;
    });

})(jQuery);