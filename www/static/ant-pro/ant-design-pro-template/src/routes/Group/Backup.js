import React, {PureComponent, Fragment} from 'react';
import moment from 'moment';
import {connect} from 'dva';
import {Link} from 'dva/router';
import {Card, Button, Table, notification, Badge, Modal, Radio, Input, Form, Tooltip, Icon} from 'antd';
import styles from './AppList.less';
import pageHeaderLayoutStyle from '../../layouts/PageHeaderLayout.less';
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
import sourceUtil from '../../utils/source-unit';
import ScrollerX from '../../components/ScrollerX';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import userUtil from '../../utils/user';
import logSocket from '../../utils/logSocket';
import ConfirmModal from '../../components/ConfirmModal';
import MigrationBackup from '../../components/MigrationBackup';
import RestoreBackup from '../../components/RestoreBackup';
import ImportBackup from '../../components/ImportBackup';
import config from '../../config/config';
const {TextArea}  = Input
const RadioButton = Radio.Button;
const RadioGroup = Radio.Group;


@connect(({user, appControl}) => ({currUser: user.currentUser}))
class BackupStatus extends PureComponent {
	constructor(props){
		super(props);
		this.state = {
			map: {
				starting: '备份中',
				success: '备份成功',
				failed: '备份失败'
			}
		}
		this.timer = null;
	}
	componentDidMount(){
		const data = this.props.data;
	
		if(data.status === 'starting'){
			this.createSocket();
			this.startLoopStatus();
		}
		
	}
	createSocket(){
		this.logSocket = new logSocket({
			url: this.getSocketUrl(),
			eventId: this.props.data.event_id,
			onMessage: (msg) => {
				console.log(msg)
			}
		})
	}
	componentWillUnmount(){
		this.stopLoopStatus();
		this.logSocket && this.logSocket.destroy();
		this.logSocket = null;
	}
	getSocketUrl = () => {
		return userUtil.getCurrRegionSoketUrl(this.props.currUser);
	}
	startLoopStatus(){
		this.props.dispatch({
			type: 'groupControl/fetchBackupStatus',
			payload: {
				team_name: globalUtil.getCurrTeamName(),
				backup_id: this.props.data.backup_id,
				group_id: this.props.group_id
			},
			callback: (data) => {
				const bean = data.bean;
				if(bean.status === 'starting'){
					this.timer = setTimeout(()=>{
						this.startLoopStatus();
					}, 10000)
				}else{
					this.props.onEnd && this.props.onEnd();
				}
			}
		})
	}
	stopLoopStatus(){
		clearTimeout(this.timer)
	}
	render(){
		const data = this.props.data||{};
		return (
			<span>{this.state.map[data.status]} {data.status === 'starting' && <Icon  style={{marginLeft: 8}} type="loading" spin />}</span>
		)
	}
}


@Form.create()
class Backup extends PureComponent {
	componentDidMount(){
		
	}
	onOk = (e) => {
		e.preventDefault();
		const form = this.props.form;
		form.validateFields((err, fieldsValue) => {
	        if (err) return;
	        this.props.onOk && this.props.onOk(fieldsValue)
	    });
	}
	render(){
		const { getFieldDecorator, getFieldValue } = this.props.form;
		const data  = this.props.data || {};
		
		const formItemLayout = {
			labelCol: {
			  span: 5,
			},
			wrapperCol: {
			  span: 19,
			},
		};
		return	<Modal
			title={"新增备份"}
			visible={true}
			onOk={this.onOk}
			onCancel={this.props.onCancel}
		>
			<Form  layout="horizontal" hideRequiredMark>
				<Form.Item
					{...formItemLayout}
					label={<span>备份方式</span>}
					>
					{getFieldDecorator('mode', {
						initialValue: data.mode || 'full-online',
						rules: [{ required: true, message: '要创建的应用还没有名字' }],
					})(
						<RadioGroup>
							<Tooltip title="备份到Rainbond平台">
							<RadioButton value="full-online">云端备份</RadioButton>
							</Tooltip>
							<Tooltip title="备份到服务器指定目录">
								<RadioButton value="full-offline">本地备份</RadioButton>
							</Tooltip>
						</RadioGroup>
					)}
				</Form.Item>
				<Form.Item
					{...formItemLayout}
					label="备份说明"
					>
					{getFieldDecorator('note', {
						initialValue: data.note || ''
					})(
						<TextArea placeholder="请写入备份说明" />
					)}
				</Form.Item>
			</Form>

		</Modal>
	}
}

// @connect(({ groupControl}) => ({
// 	groupDetail: groupControl.groupDetail || {}
//   }))
  @connect(({user,global,groupControl}) => ({groupDetail: groupControl.groupDetail || {},currUser: user.currentUser,groups: global.groups || []}))
//   @connect(({groupControl}) => ({}), null, null, {pure: false})
export default class AppList extends PureComponent {
	constructor(props) {
		super(props);
		this.state = {
			selectedRowKeys: [],
			list: [],
			teamAction: {},
			page: 1,
			total: 0,
			pageSize: 6,
			showBackup: false,
			showMove:false,
			showDel:false,
			showRecovery:false,
			showExport:false,
			showImport:false,
			backup_id:'',
			groupName:''
		}
	}
	componentDidMount() {
		this.fetchBackup();
		this.getGroupName();
	}
	componentWillUnmount() {

	}
	fetchBackup = () => {
		const team_name = globalUtil.getCurrTeamName();
		this.props.dispatch({
			type: 'groupControl/fetchBackup',
			payload:{
				team_name: team_name,
				group_id: this.getGroupId(),
				page: this.state.page,
				page_size: this.state.pageSize
			},
			callback: (data) => {
				this.setState({list: data.list ||[], total: data.total})
			}
		})
	}
	onBackup = () => {
		this.setState({showBackup: true})
	}
	cancelBackup = () => {
		this.setState({showBackup: false})
	}
	handleBackup = (data) => {
		const team_name = globalUtil.getCurrTeamName();
		this.props.dispatch({
			type: 'groupControl/backup',
			payload:{
				team_name: team_name,
				group_id: this.getGroupId(),
				...data
			},
			callback: () => {
				this.cancelBackup();
				this.fetchBackup();
			}
		})
	}
	getGroupId =() => {
		const params = this.props.match.params;
		return params.groupId;
	}
	getGroupName= ()=>{
		 const group_id = this.getGroupId();
		 const groups = this.props.groups;
		 var group_name = '';
		 groups.map((order)=>{
			if(order.group_id == group_id){
				group_name = order.group_name;
			}
		 })
		 this.setState({groupName:group_name})
	}
	// 倒入备份
	toAdd = () =>{
		this.setState({showImport:true})
	}
	handleImportBackup =(e) =>{
		notification.success({
			message: '备份已导入',
			duration:'2'
		});
		this.setState({showImport:false})
		this.fetchBackup();
	}
	cancelImportBackup = () =>{
		this.setState({showImport:false})
		this.fetchBackup();
	}
	// 恢复应用备份
	handleRecovery =(data,e)=>{
		console.log(e)
		console.log(data)
		this.setState({showRecovery:true,backup_id:data.backup_id});
	}
	handleRecoveryBackup =() =>{
		this.setState({showRecovery:false,backup_id:''});
	}
	cancelRecoveryBackup = () =>{
		this.setState({showRecovery:false,backup_id:''});
	}
	// 迁移应用备份
	handleMove =(data,e) =>{
		this.setState({showMove:true,backup_id:data.backup_id});
	}
	handleMoveBackup=()=>{
		this.setState({showMove:false});
	}
	cancelMoveBackup = () =>{
		this.setState({showMove:false,backup_id:''});
	}
	// 导出应用备份
	
	handleExport = (data,e) =>{ 
		var backup_id = data.backup_id;
		var team_name = globalUtil.getCurrTeamName()
		var group_id = this.getGroupId();
		var exportURl = config.baseUrl + '/console/teams/'+ team_name +'/groupapp/'+ group_id +'/backup/export?backup_id=' + backup_id
		window.open(exportURl);
		notification.success({
			message: '备份导出中',
			duration:'2'
		});
	}
	// 删除应用备份
	handleDel = (data,e) =>{
		this.setState({showDel:true,backup_id:data.backup_id})
	}
	handleDelete = (e) =>{
		const team_name = globalUtil.getCurrTeamName();
		this.props.dispatch({
			type: 'groupControl/delBackup',
			payload:{
				team_name: team_name,
				group_id: this.getGroupId(),
				backup_id:this.state.backup_id
			},
			callback: (data) => {
				notification.success({
					message: '删除成功',
					duration:'2'
				});
				this.fetchBackup();
			}
		})
	}
	cancelDelete = (e)=>{
		this.setState({showDel:false,backup_id:''})
	}
	render() {
			const columns = [
				{
						title: '备份时间',
						dataIndex: 'create_time'
				}, {
						title: '备份人',
						dataIndex: 'user'
				}, {
						title: '备份模式',
						dataIndex: 'mode',
						render: (val, data) => {
							var map = {
								'full-online': '云端备份',
								'full-offline': '本地备份'
							}
							return map[val] || ''
						}
				}, {
						title: '包大小',
						dataIndex: 'backup_size',
						render: (val, data) => {
								return sourceUtil.unit(val, 'Byte');
						}
				}, {
						title: '状态',
						dataIndex: 'status',
						render: (val, data) => {
							return <BackupStatus onEnd={this.fetchBackup} group_id={this.getGroupId()} data={data} />
						}
				},{
                    title: '备注',
                    dataIndex: 'note'
                }, {
						title: '操作',
						dataIndex: 'action',
						render: (val, data) => {
							return (
								<div>
									{ 
										( data.status == 'success')?
										<Fragment>
											<a href="javascript:;" style={{marginRight:'5px'}} onClick={this.handleRecovery.bind(this,data)}>恢复</a>
											<a href="javascript:;" style={{marginRight:'5px'}} onClick={this.handleMove.bind(this,data)}>迁移</a>
											{data.mode == 'full-online' &&  <a  href="javascript:;" style={{marginRight:'5px'}} onClick={this.handleExport.bind(this,data)}>导出</a> }
											{/* <a  href="javascript:;" onClick={this.handleDel.bind(this,data)}>删除</a> */}
										</Fragment>
										:''
										
									}
									{ 
										(data.status == 'failed')?
										<Fragment>
											 <a  href="javascript:;"onClick={this.handleDel.bind(this,data)}>删除</a>
										</Fragment>
										:''
									}
								</div>	
									
								
							)
						}
				}
			];
			
			const list = this.state.list || [];
			const groupName = this.state.groupName;
			return (
                
                <PageHeaderLayout
                  title={groupName}
                  breadcrumbList={[{
                      title: "首页",
                      href: `/`
                  },{
                      title: "我的应用",
                      href: ``
                  },{
                      title: groupName,
                      href: ``
                  },{
					title: "备份",
					href: ``
				}]}
                  content={(
                    <p>备份历史管理</p>
                  )}
                    extraContent={(
                    <div>
                        <Button style={{marginRight: 8}} type="primary" onClick={this.onBackup} href="javascript:;">新增备份</Button>
                        <Button onClick={this.toAdd} href="javascript:;">导入备份</Button>
                    </div>
                  )}>
                   <Card>
				   	   <ScrollerX sm={800}>
						   <Table 
						    rowKey={(data)=>{return data.backup_id}}
						    pagination={{
								current: this.state.page,
								total: this.state.total,
								pageSize: this.state.pageSize,
								onChange: (page) => {
									this.setState({page: page}, ()=>{
										this.fetchBackup();
									})
								}
							}}
						    columns={columns} dataSource={list} />
					   </ScrollerX>
                   </Card>
				   
				   {this.state.showBackup && <Backup onOk={this.handleBackup} onCancel={this.cancelBackup} />}
				   {this.state.showMove && <MigrationBackup onOk={this.handleMoveBackup} onCancel={this.cancelMoveBackup} backupId = {this.state.backup_id} groupId = {this.getGroupId()} />}
				   {this.state.showRecovery && <RestoreBackup onOk={this.handleRecoveryBackup} onCancel={this.cancelRecoveryBackup} propsParams={this.props.match.params} backupId = {this.state.backup_id} groupId = {this.getGroupId()}/>}
				   {this.state.showImport && <ImportBackup onReLoad={this.handleImportBackup} onCancel={this.cancelImportBackup} backupId = {this.state.backup_id} groupId = {this.getGroupId()}/>}
				   {this.state.showDel && <ConfirmModal
				   	backupId = {this.state.backup_id}
                    onOk={this.handleDelete}
                    onCancel={this.cancelDelete}
                    title="删除备份"
                    desc="确定要删除此备份吗？"
					subDesc="此操作不可恢复"/>}
                </PageHeaderLayout>
              );
	}
}