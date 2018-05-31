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
							<RadioButton value="full-online">在线备份</RadioButton>
							</Tooltip>
							<Tooltip title="备份到服务器指定目录">
								<RadioButton value="full-offline">离线备份</RadioButton>
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


@connect(({groupControl}) => ({}), null, null, {pure: false})
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
			showBackup: false
		}
	}
	componentDidMount() {
		this.fetchBackup();
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
	getGroupId() {
		const params = this.props.match.params;
		return params.groupId;
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
								'full-online': '在线模式',
								'full-offline': '离线模式'
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
									{ /*
										( data.status == 'success')?
										<Fragment>
											<Button type="primary" style={{marginRight:'5px'}} onClick={this.handleRecovery.bind(this,data)}>恢复</Button>
											<Button type="primary" style={{marginRight:'5px'}} onClick={this.handleMove.bind(this,data)}>迁移</Button>
											<Button onClick={this.handleDelete.bind(this,data)}>删除</Button>
										</Fragment>
										:''
										*/
									}
									{ 
										/*
										(data.status == 'failed')?
										<Fragment>
											<Button onClick={this.handleDelete.bind(this,data)}>删除</Button>
										</Fragment>
										:''
										*/
									}
								</div>	
									
								
							)
						}
				}
			];
			const groupDetail = {};
			const list = this.state.list || [];
			return (
                
                <PageHeaderLayout
                  title={"备份历史管理"}
                  breadcrumbList={[{
                      title: "首页",
                      href: `/`
                  },{
                      title: "我的应用",
                      href: ``
                  },{
                      title: "test",
                      href: ``
                  }]}
                  content={(
                    <p>备份管理</p>
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
                </PageHeaderLayout>
              );
	}
}