import React, {PureComponent, Fragment} from 'react';
import moment from 'moment';
import {connect} from 'dva';
import {Link} from 'dva/router';
import {Card, Button, Table, notification, Badge} from 'antd';
import styles from './AppList.less';
import globalUtil from '../../utils/global';
import {
		restart,
		start,
		stop,
		batchStop,
		batchStart,
		batchReStart
} from '../../services/app';
import appUtil from '../../utils/app';
import appStatusUtil from '../../utils/appStatus-util';
import ScrollerX from '../../components/ScrollerX';

@connect(({groupControl}) => ({}), null, null, {pure: false})
export default class AppList extends PureComponent {
	constructor(props) {
		super(props);
		this.state = {
			selectedRowKeys: [],
			apps: [],
			teamAction: {},
			current: 1,
			total: 0,
			pageSize: 10
		}
	}
	componentDidMount() {
		this.loadApps();
		this.timer = setInterval(() => {
			this.loadApps();
		}, 5000)
	}
	componentWillUnmount() {
		clearInterval(this.timer);
		this
			.props
			.dispatch({type: 'groupControl/clearApps'})
	}
	loadApps = () => {

		const {dispatch, form, index} = this.props;
		const team_name = globalUtil.getCurrTeamName();
		const region_name = globalUtil.getCurrRegionName();

		dispatch({
			type: 'groupControl/fetchApps',
			payload: {
				team_name: team_name,
				region_name: region_name,
				group_id: this.props.groupId,
				page:this.state.current,
				page_size:10,

			},
			callback: ((data) => {
				this.setState({
					apps: data.list || [],
					teamAction: data.bean || {},
					total: data.total
				})
			})
		})
	}
	onSelectChange = (selectedRowKeys, selectedRow) => {
		this.setState({selectedRowKeys: selectedRowKeys});
	}
	handleReStart = (data) => {
		restart({
			team_name: globalUtil.getCurrTeamName(),
			app_alias: data.service_alias
		}).then((data) => {
			if (data) {
				notification.success({message: `操作成功，重启中`});
			}
		})
	}
	handleStart = (data) => {
		start({
			team_name: globalUtil.getCurrTeamName(),
			app_alias: data.service_alias
		}).then((data) => {
			if (data) {
				notification.success({message: `操作成功，启动中`});
			}
		})
	}
	handleStop = (data) => {
		stop({
			team_name: globalUtil.getCurrTeamName(),
			app_alias: data.service_alias
		}).then((data) => {
			if (data) {
				notification.success({message: `操作成功，关闭中`});
			}
		})
	}
	getSelected() {
		var key = this.state.selectedRowKeys;
		var res = key.map((item) => {
			return this.state.apps[item];
		})
		return res;
	}
	getSelectedKeys() {
		var selected = this.getSelected();
		return selected.map((item) => {
			return item.service_id;
		})
	}
	handleBatchRestart = () => {
		const ids = this.getSelectedKeys();
		batchReStart({
			team_name: globalUtil.getCurrTeamName(),
			serviceIds: ids.join(',')
		}).then((data) => {
			if (data) {
				notification.success({message: `批量重启中`});
			}
		})
	}
	handleBatchStart = () => {
		const ids = this.getSelectedKeys();
		batchStart({
			team_name: globalUtil.getCurrTeamName(),
			serviceIds: ids.join(',')
		}).then((data) => {
			if (data) {
				notification.success({message: `批量启动中`});
			}
		})
	}
	handleBatchStop = () => {
		const ids = this.getSelectedKeys();
		batchStop({
			team_name: globalUtil.getCurrTeamName(),
			serviceIds: ids.join(',')
		}).then((data) => {
			if (data) {
				notification.success({message: `批量关闭中`});
			}
		})
	}
	//是否可以批量重启
	canBatchRestart = () => {
		const selectedRowKeys = this.getSelected();
		const hasSelected = selectedRowKeys.length > 0;
		const canotRestart = selectedRowKeys.filter((item) => {
			return !appStatusUtil.canRestart(item)
		})
		return hasSelected;
	}
	//是否可以批量启动
	canBatchStart = () => {
		const selectedRowKeys = this.getSelected();
		const hasSelected = selectedRowKeys.length > 0;
		const canotStart = selectedRowKeys.filter((item) => {
			return !appStatusUtil.canStart(item)
		})
		return hasSelected;
	}
	//是否可以批量关闭
	canBatchStop = () => {
		const selectedRowKeys = this.getSelected();
		const hasSelected = selectedRowKeys.length > 0;
		const canotStop = selectedRowKeys.filter((item) => {
			return !appStatusUtil.canStop(item);
		})
		return hasSelected;
	}
	render() {
		   
			const {apps, teamAction} = this.state;
			const {selectedRowKeys} = this.state;
			const rowSelection = {
					selectedRowKeys: selectedRowKeys,
					onChange: this.onSelectChange
			};
			const hasSelected = selectedRowKeys.length > 0;
			const pagination = {
				current: this.state.current,
				total: this.state.total,
				onChange: (page) => {
					this.setState({current: page,selectedRowKeys:[]}, () => {
						this.loadApps();
					})
				 }
			}
			const columns = [
				{
						title: '应用名称',
						dataIndex: 'service_cname',
						render: (val, data) => {
								return <Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/app/${data.service_alias}/overview`}>{val}</Link>
						}
				}, {
						title: '应用类型',
						dataIndex: 'service_type'
				}, {
						title: '内存',
						dataIndex: 'min_memory',
						render: (val, data) => {
								return val + 'MB'
						}
				}, {
						title: '状态',
						dataIndex: 'status_cn',
						render: (val, data) => {
								return <Badge status={appUtil.appStatusToBadgeStatus(data.status)} text={val}/>
						}
				}, {
						title: '更新时间',
						dataIndex: 'update_time',
						render: (val) => {
								return moment(val).format("YYYY-MM-DD HH:mm:ss")
						}
				}, {
						title: '操作',
						dataIndex: 'action',
						render: (val, data) => {
							return (
								<Fragment>
									{appStatusUtil.canRestart(data)
										? <a
													onClick={() => {
													this.handleReStart(data)
											}}
													href="javascript:;"
													style={{
													marginRight: 10
											}}>重启</a>
										: null
}
									{appStatusUtil.canStart(data)
											? <a
															onClick={() => {
															this.handleStart(data)
													}}
															href="javascript:;"
															style={{
															marginRight: 10
													}}>启动</a>
											: null
}
									{appStatusUtil.canStop(data)
											? <a
															onClick={() => {
															this.handleStop(data)
													}}
															href="javascript:;">关闭</a>
											: null
}

								</Fragment>
							)
						}
				}
			];

			return (
					<Card style={{
							minHeight: 400
					}} bordered={false}>
						
							<div
									className={styles.tableList}>
									<div className={styles.tableListOperator}>
										<Button disabled={!this.canBatchRestart()} onClick={this.handleBatchRestart}>
												批量重启
										</Button>
										<Button disabled={!this.canBatchStop()} onClick={this.handleBatchStop}>
												批量关闭
										</Button>
										<Button disabled={!this.canBatchStart()} onClick={this.handleBatchStart}>
												批量启动
										</Button>
									</div>
							</div>
						<ScrollerX sm={750}>
							<Table pagination={pagination}  rowSelection={rowSelection} columns={columns} dataSource={apps || []}/>
						</ScrollerX>
					</Card>
			)
	}
}