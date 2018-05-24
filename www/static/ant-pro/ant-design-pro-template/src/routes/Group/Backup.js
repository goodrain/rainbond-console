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
import ScrollerX from '../../components/ScrollerX';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
const {TextArea}  = Input
const RadioButton = Radio.Button;
const RadioGroup = Radio.Group;

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
			current: 1,
			total: 0,
			pageSize: 10,
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
			},
			callback: (data) => {
				this.setState({list: data.list ||[]})
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
						dataIndex: 'service_cname',
						render: (val, data) => {
								return <Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/app/${data.service_alias}/overview`}>{val}</Link>
						}
				}, {
						title: '备份人',
						dataIndex: 'service_type'
				}, {
						title: '备份模式',
						dataIndex: 'min_memory',
						render: (val, data) => {
								return val + 'MB'
						}
				}, {
						title: '包大小',
						dataIndex: 'status_cn',
						render: (val, data) => {
								return <Badge status={appUtil.appStatusToBadgeStatus(data.status)} text={val}/>
						}
				}, {
						title: '状态',
						dataIndex: 'update_time',
						render: (val) => {
								return moment(val).format("YYYY-MM-DD HH:mm:ss")
						}
				},{
                    title: '备注',
                    dataIndex: 'update_time999',
                    render: (val) => {
                            return moment(val).format("YYYY-MM-DD HH:mm:ss")
                    }
                }, {
						title: '操作',
						dataIndex: 'action',
						render: (val, data) => {
							return (
								<Fragment>
									
								</Fragment>
							)
						}
				}
			];
            const groupDetail = {};
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
                       <Table columns={columns} dataSource={[]} />
                   </Card>
				   {this.state.showBackup && <Backup onOk={this.handleBackup} onCancel={this.cancelBackup} />}
                </PageHeaderLayout>
              );
	}
}