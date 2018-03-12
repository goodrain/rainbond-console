import React, { PureComponent, Fragment } from 'react';  
import moment from 'moment';
import { connect } from 'dva';
import { Link } from 'dva/router';
import { Card, Button, Table, notification, Badge } from 'antd';
import styles from './AppList.less';
import globalUtil from '../../utils/global';
import { restart, start, stop, batchStop, batchStart, batchReStart  } from '../../services/app';
import appUtil from '../../utils/app';
import appStatusUtil from '../../utils/appStatus-util';

@connect(({ groupControl }) => ({
  apps: groupControl.apps
}), null, null, {pure:false})
export default class AppList extends PureComponent {
	constructor(props){
		super(props);
		this.state = {
			selectedRowKeys: []
		}
	}
	componentDidMount(){
		 this.loadApps();
		 this.timer = setInterval(()=>{
		 	this.loadApps();
		 }, 5000)
	}
	componentWillUnmount(){
		clearInterval(this.timer);
		this.props.dispatch({
	        type: 'groupControl/clearApps'
	      })
	}
	loadApps = () => {

      const { dispatch, form, index } = this.props;
      const team_name = globalUtil.getCurrTeamName();
      const region_name = globalUtil.getCurrRegionName();
    
      dispatch({
        type: 'groupControl/fetchApps',
        payload: {
          team_name: team_name,
          region_name: region_name,
          group_id: this.props.groupId
        }
      })
  	}
	onSelectChange = (selectedRowKeys, selectedRow) => {

	    this.setState({ selectedRowKeys });
	}
	handleReStart = (data) => {
		restart({
			team_name: globalUtil.getCurrTeamName(),
			app_alias: data.service_alias
		}).then((data)=>{
			if(data){
				notification.success({
				    message: `操作成功，重启中`
				});
			}
		})
	}
	handleStart = (data) => {
		start({
			team_name: globalUtil.getCurrTeamName(),
			app_alias: data.service_alias
		}).then((data)=>{
			if(data){
				notification.success({
				    message: `操作成功，启动中`
				});
			}
		})
	}
	handleStop = (data) => {
		stop({
			team_name: globalUtil.getCurrTeamName(),
			app_alias: data.service_alias
		}).then((data)=>{
			if(data){
				notification.success({
				    message: `操作成功，关闭中`
				});
			}
		})
	}
	getSelected(){
		var res = this.state.selectedRowKeys;
		res = this.state.selectedRowKeys.map((item)=>{
			return this.props.apps[item].service_id;
		})
		return res;
	}
	handleBatchRestart = () => {
		const ids = this.getSelected();
		batchReStart({
			team_name: globalUtil.getCurrTeamName(),
			serviceIds: ids.join(',')
		}).then((data)=>{
			if(data){
				notification.success({
				    message: `批量重启中`
				});
			}
		})
	}
	handleBatchStart = () => {
		const ids = this.getSelected();
		batchStart({
			team_name: globalUtil.getCurrTeamName(),
			serviceIds: ids.join(',')
		}).then((data)=>{
			if(data){
				notification.success({
				    message: `批量启动中`
				});
			}
		})
	}
	handleBatchStop = () => {
		const ids = this.getSelected();
		batchStop({
			team_name: globalUtil.getCurrTeamName(),
			serviceIds: ids.join(',')
		}).then((data)=>{
			if(data){
				notification.success({
				    message: `批量关闭中`
				});
			}
		})
	}
	render(){
		const columns = [{
		  title: '应用名称',
		  dataIndex: 'service_cname',
		  render: (val, data) => {
		  	  return <Link to={'/app/'+data.service_alias+ '/overview'}>{val}</Link>
		  }
		}, {
		  title: '应用类型',
		  dataIndex: 'service_type',
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
		  	return <Badge status={appUtil.appStatusToBadgeStatus(data.status)} text={val} />
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
		  	 	    <a onClick={()=>{this.handleReStart(data)}} href="javascript:;" style={{marginRight: 10}}>重启</a>
		  	 		<a  onClick={()=>{this.handleStart(data)}} href="javascript:;" style={{marginRight: 10}}>启动</a>
		  	 		<a onClick={()=>{this.handleStop(data)}} href="javascript:;">关闭</a>

		  	 	</Fragment>
		  	 )
		  }
		}];
		const { apps }  = this.props;
		const { selectedRowKeys } = this.state;
	    const rowSelection = {
	      selectedRowKeys,
	      onChange: this.onSelectChange,
	    };
	    const hasSelected = selectedRowKeys.length > 0;

		return (
			<Card style={{minHeight: 400}} bordered={false}>
				<div className={styles.tableList}>
					<div className={styles.tableListOperator}>
					  <Button disabled={!hasSelected} onClick={this.handleBatchRestart}>
		                批量重启
		              </Button>
		              <Button disabled={!hasSelected} onClick={this.handleBatchStop}>
		                批量关闭
		              </Button>
		              <Button disabled={!hasSelected} onClick={this.handleBatchStart}>
		                批量启动
		              </Button>
		            </div>
		        </div>
		        <Table rowSelection={rowSelection} columns={columns} dataSource={apps || []} />
			</Card>
		)
	}
}