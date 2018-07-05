import React, {PureComponent} from 'react';
import {connect} from 'dva';
import {Link, Switch, Route, routerRedux} from 'dva/router';
import {
		Row,
		Col,
		Card,
		Form,
		Button,
		Icon,
		Menu,
		Dropdown,
		notification,
		Select,
		Input,
		Modal,
		message,
		Divider
} from 'antd';
import globalUtil from '../../utils/global';

var echarts = require('echarts');

@connect(({user, global}) => ({groups: global.groups}), null, null, {withRef: true})
@Form.create()
export default class Index extends PureComponent {
		constructor(props) {
			super(props);
			this.state = {
				datalist:[]
			}
		}
		componentDidMount() {
			this.getRegionResource();
			// this.chartMap(datalist);
		}
		// 获取某个数据中心的资源详情  // 新-- 数据中心列表
		getRegionResource(){
			this.props.dispatch({
			type: 'global/getRegionSource',
			payload:{
				team_name: globalUtil.getCurrTeamName(),
				enterprise_id: this.props.enterprise_id,
				region: globalUtil.getCurrRegionName()
			},
			callback: (data) => {
				this.setState({datalist:data.list},()=>{
					const datalist = this.state.datalist
					this.chartMap(datalist);
				})
			}
			})
		}
		  //调用图表
		  chartMap(datalist){
			datalist.map((region) => {
			  var id = region.name;
			  var limit_disk = region.disk.limit   // 磁盘最大值  
			  var limit_memory = region.memory.limit  // 内存最大值最大值 
			  
			  var memoryStock = Number(region.memory.limit) - Number(region.memory.used) // 内存剩余
			  var diskStock = Number(region.disk.limit)-  Number(region.disk.used)// 磁盘剩余
		
			  var memoryUsed = region.memory.used  // 内存已使用
			  var diskUsed = region.disk.used  // 磁盘已使用
		
			 
		
		
			   var diskdata = {
			     name:'磁盘(单位:GB)',
			     usedname:'已使用磁盘',
			     nousedname:'未使用磁盘',
			     id: id + '-disk',
			     Maxamount: limit_disk,
			     Usedamount : diskUsed,
			     noUsedamount :diskStock,
			     dataname:['已使用磁盘','未使用磁盘'],
			     data:[
			       {value:diskUsed, name:'已使用磁盘'},
			       {value:diskStock, name:'未使用磁盘'}
			     ]
			   }
			   var memorydata = {
			     name:'内存(单位:MB)',
			     usedname:'已使用内存',
			     nousedname:'未使用内存',
			     id: id + '-memory',
			     Maxamount: limit_memory,
			     Usedamount : memoryUsed,
			     noUsedamount :memoryStock,
			     dataname:['已使用内存','未使用内存'],
			     data:[
			              {value:memoryUsed, name:'已使用内存'},
			              {value:memoryStock, name:'未使用内存'}
			          ]
			   }
		
			  if(datalist.length !=0 ){
			    if(diskStock == 0){
			      diskdata.dataname = ['已使用磁盘']
			      diskdata.data = [{value:memoryUsed, name:'已使用磁盘'}]
			      
			    }
			    if(memoryStock == 0){
			      memorydata.dataname = ['已使用内存']
			      memorydata.data = [{value:diskUsed, name:'已使用内存'}]
				}
			    this.showChart(diskdata);
			    this.showChart(memorydata);
		
			  }
			})
		  }
		  //绘制图表
		  showChart(chartdata){
				var myChart = echarts.init(document.getElementById(chartdata.id));
				// 绘制图表
				myChart.setOption({
					tooltip: {
						trigger: 'item',
						formatter: "{a} <br/>{b}: {c} ({d}%)"
					},
					legend: {
						orient: 'horizontal',
						x: 'center',
						inactiveColor: '#999',
						data:chartdata.dataname
					},
					color:['#bd0233','#2788b9'],
					grid: {
						left: '0%',
						right: '0%',
						bottom: '0%',
						containLabel: true
					},
					series: [
						{
							name:chartdata.name,
							type:'pie',
							radius: ['50%', '40%'],
							hoverAnimation:false,
							avoidLabelOverlap: false,
							legendHoverLink:true,
							label: {
								normal: {
									show: false,
									position: 'center'
								},
								emphasis: {
									show: true,
									textStyle: {
										fontSize: '14',
										fontWeight: 'bold'
									}
								}
							},
							labelLine: {
								normal: {
									show: false
								}
							},
							data:chartdata.data
						}
					]
				});
			}
		  //
		render() {
			const datalist = this.state.datalist || [];
			return (
				<div>
					{
						datalist.map((order)=>{
							return(
								<div  style={{textAlign:'center'}}>
									<p style={{fontSize:'16px',lineHeight:'30px'}}>{order.alias}</p>
									<Row>
										<Col span={12}>
											<div id={order.name + '-memory'} style={{width:'100%',height:'250px'}}>图表加载中...</div>
											<p>内存({order.memory.used}M/{order.memory.limit}M)</p>
											<p style={{color:'#f5222d'}}>
											{
												order.memory.expire_date == "" ?
												'包月资源已过期或暂未包月'
												:
												<span>包月到期时间:{order.memory.expire_date}</span>
											}
											</p>
										</Col>
										<Col span={12}>
											<div id={order.name + '-disk'}  style={{width:'90%',height:'250px'}}>图表加载中...</div>
											<p>磁盘({order.disk.used}G/{order.disk.limit}G)</p>
											<p style={{color:'#f5222d'}}>
											{
												order.disk.expire_date == "" ?
												'包月资源已过期或暂未包月'
												:
												<span>包月到期时间:{order.disk.expire_date}</span>
											}
											</p>
										</Col>
									</Row>
									<p>
										<Button type='primary'><Link to={`/team/${globalUtil.getCurrTeamName()}/region/${order.name}/resources`}>购买资源</Link></Button>
									</p>
									<Divider />
								</div>
							)
						})
					}
				</div>
			)
		}
}