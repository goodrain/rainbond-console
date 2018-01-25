import createPageController from '../utils/page-controller';
import http from '../utils/http';
import { getAppInfo } from '../comms/app-apiCenter';

import {
	getPageMonitorAppData
} from '../comms/page-app-apiCenter';
var  template = require('./app-monitor-tpl.html');


/* 业务逻辑控制器 */
const AppMonitor = createPageController({
	template: template,
	property: {
		//租户名
		tenantName: '',
		serviceAlias: '',
		servicecName: '',
		//当前应用语言类型
		language:'',
		code_from:'',
		serviceId:'',
		renderData:{
			pageData:null,
			appInfo: null,
			tenantName:'',
			serviceAlias:''
		}
	},
	method: {
		//获取页面初始化数据
		getInitData: function(){

			getAppInfo(
				this.tenantName,
				this.serviceAlias
			).done((appInfo) => {
				this.renderData.appInfo = appInfo;
				getPageMonitorAppData(
					this.tenantName,
					this.serviceAlias
				).done((pageData) => {
					this.renderData.pageData = pageData;
					this.render();
					setTimeout(() => {
						this.createCharts();
						this.createSocket();
					})
				})
			})
		},
		//创建图表
		createCharts: function(){
		    this.getGraphs();
		    setInterval(() => {
		        this.getGraphs();
		    }, 60000);
		},
		getGraphs: function() {
			var self = this;
			var start = $('#graph-period').val();
			if(start == '3m-ago'){
	        	$('.js-time-history').hide();
	        	$('.js-time-now').show();

	        	$('.js-time-now .graph').each(function() {
			        var graph_id = $(this).attr('id');
			        var data = {"graph_id":graph_id, "start": start, last: true};

			        http({
			          	showLoading:false,
			          	isTipError:false,
			            url: '/ajax/' + self.tenantName + '/' + self.serviceAlias + '/graph',
			            type: "POST",
			            data: data
			        }).done((res) => {
				        $('#'+graph_id).find('.val').html(res.value || 0);
			        })
			    });

	        }else{
	        	$('.js-time-history').show();
	        	$('.js-time-now').hide();

	        	$('.js-time-history .graph').each(function() {
			        var graph_id = $(this).attr('id');
			        var data = {"graph_id":graph_id, "start": start};

			        http({
			          	showLoading:false,
			          	isTipError:false,
			            url: '/ajax/' + self.tenantName + '/' + self.serviceAlias + '/graph',
			            type: "POST",
			            data: data
			        }).done((res) => {

			        	if(res.data){
			        		for(var i=0;i<res.data.length;i++){
			        			delete res.data[i].key;
			        		}
			        	}
				        self.makeChart(graph_id, res, start);
			        })
			    });

	        }
		},
		makeChart: function(graph_id, event, start) {
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
		          //.axisLabel(event.yAxisLabel)
		          .tickFormat(d3.format(event.yAxisFormat))
		          ;

		        chart.noData("没有可展示的数据");
		        chart.showLegend(false);

		        $('#' + graph_id + ' svg').empty();

		        var svgElem = d3.select('#' + graph_id + ' svg');
		        svgElem.datum(event.data).transition().call(chart);

		        var tsFormat = d3.time.format('%m/%d %H:%M');
		        var contentGenerator = chart.interactiveLayer.tooltip.contentGenerator();
		        var tooltip = chart.interactiveLayer.tooltip;
		        tooltip.contentGenerator(function (d) { d.value = d.initial; return contentGenerator(d); });
		        tooltip.headerFormatter(function (d) { return tsFormat(new Date(d)); });

		        nv.utils.windowResize(chart.update);

		        return chart;
		    });
	    },
	    //创建socket, 更新表格
	    createSocket: function(){
	    	var self = this;
	    	this.webSocket = new WebSocket(this.renderData.pageData.monitor_websocket_uri);
	    	this.webSocket.onopen = function(){
	    		self.webSocket.send("topic="+self.renderData.pageData.ws_topic);
	    	}
	    	this.webSocket.onmessage = function(e){
	    		if(e.data){
	    			self.updateTable(e.data);
	    		}
	    	};
	    	this.webSocket.onclose = function(){
	    		self.createSocket();
	    	}
	    },
	    updateTable: function(event){
	      try{
	      	event = JSON.parse(event);
	      }catch(e){

	      }
          var columns = [];
          $('#rtm-' + event.name + ' thead th').each(function() {
                var name = $(this).attr("name");
                var align = $(this).attr("class");
                var item = {"name": name, "align": align};
                columns.push(item);
            }
          )
          
          var table_body = [];
          event.data = event.data ||[];
          event.data.reverse();
          for (var o in event.data) {
            table_body.push('<tr style="word-break: break-all;">');
            for (var n in columns) {
              var value = event.data[o][columns[n].name];
              table_body.push('<td class="' + columns[n].align + '">' + value + '</td>')
            }    
            table_body.push('</tr>');
          }
          
          var tbody = table_body.join("");
          $('#rtm-' + event.name + ' tbody').html(tbody);
          $('#rtm-' + event.name).closest('section').find('span.rtm-update-time').html("更新时间: " + event.update_time);
        }
	    
	},
	domEvents:{
		'#graph-period change': function(e) {
			this.getGraphs();
		}
	},
	onReady: function(){
		var self = this;
		this.renderData.tenantName = this.tenantName;
		this.renderData.serviceAlias = this.serviceAlias;
		this.getInitData();
	}
})

window.AppMonitorController = AppMonitor;
export default AppMonitor;