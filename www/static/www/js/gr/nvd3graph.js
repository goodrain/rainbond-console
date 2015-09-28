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
        "values": [[1443431546000, 852], [1443431576000, 109], [1443431606000, 225], [1443431636000, 485], [1443431666000, 830], [1443431696000, 246], [1443431726000, 931], [1443431756000, 724], [1443431786000, 264], [1443431816000, 901], [1443431846000, 418], [1443431876000, 877], [1443431906000, 453], [1443431936000, 127], [1443431966000, 137], [1443431996000, 440], [1443432026000, 595], [1443432056000, 184], [1443432086000, 945], [1443432116000, 300], [1443432146000, 111], [1443432176000, 882], [1443432206000, 232], [1443432236000, 184], [1443432266000, 664], [1443432296000, 327], [1443432326000, 272], [1443432356000, 728], [1443432386000, 408], [1443432416000, 358]]
      }
    ]

    var data2 = [
      {
        "key": "disk",
        "values": [[1443431546000, 142], [1443431576000, 120], [1443431606000, 104], [1443431636000, 104], [1443431666000, 101], [1443431696000, 139], [1443431726000, 111], [1443431756000, 127], [1443431786000, 145], [1443431816000, 108], [1443431846000, 119], [1443431876000, 144], [1443431906000, 106], [1443431936000, 146], [1443431966000, 143], [1443431996000, 111], [1443432026000, 142], [1443432056000, 149], [1443432086000, 114], [1443432116000, 145], [1443432146000, 132], [1443432176000, 128], [1443432206000, 108], [1443432236000, 121], [1443432266000, 110], [1443432296000, 113], [1443432326000, 111], [1443432356000, 112], [1443432386000, 132], [1443432416000, 140]]
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
        .axisLabel('')
        .tickFormat(function(d) {
          return d3.time.format('%X')(new Date(d))
        });
    
      chart.yAxis
        .axisLabel('unit: MB')
        .tickFormat(d3.format(',.2f'))
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
        .useInteractiveGuideline(false)
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

})(jQuery);