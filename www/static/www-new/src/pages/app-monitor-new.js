import createPageController from '../utils/page-controller';
import http from '../utils/http';
import { 
	getAppInfo
} from '../comms/app-apiCenter';

import {
	getPageMonitorAppData
} from '../comms/page-app-apiCenter';
var  template = require('./app-monitor-new-tpl.html');
var echarts = require('echarts');



function beforeDays(days=0, date = new Date()){
	var t = 60 * 60 * 24 * 1000 * days;
	var before = date.getTime() - t;
	var d = new Date();
	d.setTime(before);
	return d;
}


function createChar(ele, data){
	var option = {
	    animation: true,
	    xAxis: {
	        show:false,
	        type: 'time'
	    },
	    yAxis: {
	        show:false
	    },
	    grid: {
	    	left:0,
	    	bottom:0,
	    	right: 0,
	    	top: 75,
	        height: 80
	    },
	    series: [
	        {
	            name:'模拟数据',
	            type:'line',

	            symbol: 'none',
	            symbolSize: 0,
	            sampling: 'none',
	            itemStyle: {
	                
	                normal: {
	                    show:false,
	                    color: '#000'
	                }
	            },
	            stack: 'a',
	            areaStyle: {
	                normal: {
	                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
	                        offset: 0,
	                        color: '#000'
	                    }, {
	                        offset: 1,
	                        color: '#fff'
	                    }, {
	                        offset: 1,
	                        color: '#fff'
	                    }])
	                }
	            },
	            data: data
	        }
	    ]
	};

	var myChart = null;
	if(ele.char){
		myChart = ele.char
	}else{
		myChart = echarts.init(ele)
	}
	myChart.setOption(option);
}

function createCharWithAxis(ele, title ,datas){

	var date = [];
	var data = [];

	for (var i = 1; i < datas.length; i++) {
	    var now = new Date(datas[i][0]*1000);
	    date.push([now.getDate()].join('/') + '日 ' +now.getHours()+':'+now.getMinutes());
	    data.push(Number(datas[i][1]));
	}


	var option = {
    tooltip: {
        trigger: 'axis',
        position: function (pt) {
            return [pt[0], '10%'];
        }
    },
    xAxis: {
        type: 'category',
        boundaryGap: false,
        data: date
    },
    yAxis: {
        type: 'value',
        boundaryGap: [0, '100%']
    },
    dataZoom: [{
        type: 'inside',
        start: 0,
        end: 100
    }, {
        start: 0,
        end: 10,
        handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
        handleSize: '80%',
        handleStyle: {
            color: '#fff',
            shadowBlur: 3,
            shadowColor: 'rgba(0, 0, 0, 0.6)',
            shadowOffsetX: 2,
            shadowOffsetY: 2
        }
    }],
    series: [
        {
            name:title || '',
            type:'line',
            smooth:true,
            symbol: 'none',
            sampling: 'average',
            itemStyle: {
                normal: {
                    color: 'rgb(197,233,155)'
                }
            },
            areaStyle: {
                normal: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
                        offset: 0,
                        color: 'rgb(143,188,148)'
                    }, {
                        offset: 1,
                        color: 'rgb(84,134,135)'
                    }])
                }
            },
            data: data
        }
    ]
};

	var myChart = null;
	if(ele.char){
		myChart = ele.char
	}else{
		myChart = echarts.init(ele)
	}
	myChart.setOption(option);
}


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
		    }, 5000);
		},
		getGraphs: function() {
			var self = this;
			var start = Number($('#graph-period').val());
			if(start === 0 ){
	        	$('.js-time-history').hide();
	        	$('.js-time-now').show();

	        	$('.js-time-now .graph').each(function() {
	        		var $self = $(this)
			        var graph_id = $(this).attr('id');
			        var data = {"query":''};
			        var rangeData = {"query":'', start:beforeDays(0.5/24)/1000, end:(new Date().getTime()/1000), step: '7'};
			        if(graph_id === 'app_requesttime'){
			        	data.query = 'sum(app_requesttime{service_id="{id}",mode="avg"})'.replace("{id}", self.serviceId)
			        	rangeData.query = 'sum(app_requesttime{service_id="{id}",mode="avg"})'.replace("{id}", self.serviceId)
			        }
			        if(graph_id === 'app_request'){
			        	data.query = 'sum(rate(app_request{service_id="{id}"}[15s]))'.replace("{id}", self.serviceId)
			        	rangeData.query = 'sum(rate(app_request{method="total",service_id="{id}"}[30s]))'.replace("{id}", self.serviceId)
			        }
			        if(graph_id === 'app_requestclien'){
			        	data.query = 'sum(app_requestclient{service_id="{id}"})'.replace("{id}", self.serviceId)
			        	rangeData.query = 'sum(app_requestclient{service_id="{id}"})'.replace("{id}", self.serviceId)
			        }


			        http({
			          	showLoading:false,
			          	isTipError:false,
			            url: '/ajax/' + self.tenantName + '/' + self.serviceAlias + '/query',
			            type: "get",
			            data: data
			        }).done((res) => {
			        	var result = res.bean.result;
			        	if(result && result.length){
			        		var res = Number(result[0].value[1]) || 0;
			        		if(graph_id === 'app_requesttime'){
			        			$self.find('.val').html(res.toFixed(2));
			        		}else{
			        			$self.find('.val').html(res.toFixed(0));
			        		}
			        	}
			        })

			        http({
			          	showLoading:false,
			          	isTipError:false,
			            url: '/ajax/' + self.tenantName + '/' + self.serviceAlias + '/query_range',
			            type: "get",
			            data: rangeData
			        }).done((res) => {

			        	var result = res.bean.result;
			        	if(result && result.length){
			        		createChar($self.parents('.flex-singe').find('.absolute')[0], result[0].values||[])
			        		
			        	}
				        
			        })

			    });

	        }else{
	        	$('.js-time-history').show();
	        	$('.js-time-now').hide();

	        	$('.js-time-history .graph').each(function() {
	        		var $self = $(this)
			        var graph_id = $(this).attr('id');
			        var rangeData = {"query":'', start:beforeDays(start/24)/1000, end:(new Date().getTime()/1000), step: start*600/100};
			        var title = '';
			        if(graph_id === 'app_requesttime'){
			        	rangeData.query = 'sum(app_requesttime{service_id="{id}",mode="avg"})'.replace("{id}", self.serviceId)
			        
			        }
			        if(graph_id === 'app_request'){
			        	rangeData.query = 'sum(rate(app_request{method="total",service_id="{id}"}[30s]))'.replace("{id}", self.serviceId)
			        }
			        if(graph_id === 'app_requestclien'){
			            rangeData.query = 'sum(app_requestclient{service_id="{id}"})'.replace("{id}", self.serviceId)
			        }

			        http({
			          	showLoading:false,
			          	isTipError:false,
			            url: '/ajax/' + self.tenantName + '/' + self.serviceAlias + '/query_range',
			            type: "get",
			            data: rangeData
			        }).done((res) => {
			        	var result = res.bean.result;
			        	if(result && result.length){
			        		createCharWithAxis($self[0],title ,result[0].values||[])
			        		
			        	}
			        })
			    });

	        }
		},
	    //创建socket, 更新表格
	    createSocket: function(){
	    	var self = this;
	    	this.webSocket = new WebSocket(this.renderData.pageData.monitor_websocket_uri);
	    	this.webSocket.onopen = function(){
	    		//self.webSocket.send("topic="+self.renderData.pageData.ws_topic);
	    		self.webSocket.send("topic="+self.serviceId);
	    	}
	    	this.webSocket.onmessage = function(e){
	    		if(e.data && e.data !== 'ok'){
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
          $('#rtm-SumTimeByUrl thead th').each(function() {
                var name = $(this).attr("name");
                var align = $(this).attr("class");
                var item = {"name": name, "align": align};
                columns.push(item);
            }
          )
          
          var table_body = [];
          for (var i=0;i<event.length;i++) {
            table_body.push('<tr style="word-break: break-all;">');
            for (var n in columns) {
              var value = event[i][columns[n].name];
              table_body.push('<td class="' + columns[n].align + '">' + value + '</td>')
            }    
            table_body.push('</tr>');
          }
          

          var tbody = table_body.join("");
          $('#rtm-SumTimeByUrl tbody').html(tbody);
          //$('#rtm-SumTimeByUrl').closest('section').find('span.rtm-update-time').html("更新时间: " + event.update_time);
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