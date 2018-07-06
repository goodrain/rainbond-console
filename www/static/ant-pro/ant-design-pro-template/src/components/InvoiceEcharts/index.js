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
import Echars from '../Echars';
import styles from './index.less';
console.log(styles)

@connect(({user, global}) => ({groups: global.groups}), null, null, {withRef: true})
export default class Index extends PureComponent {
		constructor(props) {
			super(props);
			this.state = {
				datalist:[]
			}
		}
		componentDidMount() {
			this.getRegionResource();
		}
		// 获取某个数据中心的资源详情  // 新-- 数据中心列表
		getRegionResource(){
			this.props.dispatch({
			type: 'global/getRegionSource',
			payload:{
				team_name: globalUtil.getCurrTeamName(),
				enterprise_id: this.props.enterprise_id,
				region: ''
			},
			callback: (data) => {
				this.setState({datalist:data.list},()=>{
					const datalist = this.state.datalist
				})
			}
			})
		}

		render() {
			const datalist = this.state.datalist || [];
			return (
				<div className={styles.regionList}>
				<Row style={{marginTop: 16, textAlign: 'center'}}  className={styles.regionList}>
					{
						datalist.map((order)=>{
							return(
								<Col span={12}>
								    <Card>
										<h2>{order.alias}</h2>
										<Row>
											<Col span="12">
												<div id={order.name + '-memory'} style={{width:'100%',height:'250px'}}>
													<Echars style={{height: 235, width: 235}} option={{
														
														series: [
															{
																name:'访问来源',
																type:'pie',
																radius: ['50%', '70%'],
																avoidLabelOverlap: false,
																label: {
																	normal: {
																		show: true,
																		position: 'center',
																		formatter:function (argument) {
																			var html;
																			html='本月业绩\r\n\r\n'+'50单';
																			return html;
																		},
																		textStyle:{
																		   fontSize: 15,
																			color:'#39CCCC'
																		}
																	}
																},
																labelLine: {
																	normal: {
																		show: false
																	}
																},
																data:[
																	{value:335, name:'直接访问'},
																	{value:310, name:'邮件营销'}
																]
															}
														]
													}} />
												</div>
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
											<Col span="12">
												<div id={order.name + '-disk'}  style={{width:'90%',height:'250px'}}>
													<Echars option={{}} />
												</div>
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
									</Card>
								</Col>
							)
						})
					}
				</Row>
				</div>
			)
		}
}