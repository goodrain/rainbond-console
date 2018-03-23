import React, {PureComponent, Fragment} from 'react';
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
	Modal
} from 'antd';
import AddGroup from '../../components/AddOrEditGroup';
import globalUtil from '../../utils/global';
const {Option} = Select;

const formItemLayout = {
	labelCol: {
			span: 5
	},
	wrapperCol: {
			span: 19
	}
};

@connect(({user, global}) => ({groups: global.groups}), null, null, {withRef: true})

@Form.create()
export default class Index extends PureComponent {
	constructor(props) {
			super(props);
			this.state = {
					codeType: 'Git',
					showUsernameAndPass: false,
					showKey: false,
					addGroup: false
			}
	}
	onAddGroup = () => {
			this.setState({addGroup: true})
	}
	cancelAddGroup = () => {
			this.setState({addGroup: false})
	}
	handleAddGroup = (vals) => {
		const {setFieldsValue} = this.props.form;
		this
		.props
		.dispatch({
			type: 'groupControl/addGroup',
			payload: {
				team_name: globalUtil.getCurrTeamName(),
				...vals
			},
			callback: (group) => {

				if (group) {

					//获取群组
					this
						.props
						.dispatch({
								type: 'global/fetchGroups',
								payload: {
										team_name: globalUtil.getCurrTeamName(),
										region_name: globalUtil.getCurrRegionName()
								},
								callback: () => {
										setFieldsValue({group_id: group.ID});
										this.cancelAddGroup();
								}
						});
				}

			}
		})
	}
	hideShowKey = () => {
			this.setState({showKey: false})
	}
	handleSubmit = (e) => {
			e.preventDefault();
			const form = this.props.form;
			form.validateFields((err, fieldsValue) => {
					if (err) 
							return;
					this.props.onSubmit && this
							.props
							.onSubmit(fieldsValue)
			});
	}
	render() {
		const {getFieldDecorator, getFieldValue} = this.props.form;
		const {groups} = this.props;
		const data = this.props.data || {};
		const showSubmitBtn = this.props.showSubmitBtn === void 0
				? true
				: this.props.showSubmitBtn;
		const showCreateGroup = this.props.showCreateGroup === void 0
				? true
				: this.props.showCreateGroup;
		const disableds = this.props.disableds || [];
			return (
				<Fragment>
					<Form onSubmit={this.handleSubmit} layout="horizontal" hideRequiredMark>
						<Form.Item {...formItemLayout} label="应用名称">
								{getFieldDecorator('service_cname', {
										initialValue: data.service_cname || '',
										rules: [
												{
														required: true,
														message: '要创建的应用还没有名字'
												}
										]
								})(<Input
										disabled={disableds.indexOf('service_cname') > -1}
										placeholder="请为创建的应用起个名字吧"/>)}
						</Form.Item>
						<Form.Item {...formItemLayout} label="应用组">
								{getFieldDecorator('group_id', {
										initialValue: data.group_id || -1,
										rules: [
												{
														required: true,
														message: '请选择'
												}
										]
								})(
										<Select
												disabled={disableds.indexOf('group_id') > -1}
												placeholder="请选择要所属应用组"
												style={{
												display: 'inline-block',
												width: 306,
												marginRight: 15
										}}>
												{(groups || []).map((group) => {
														return <Option value={group.group_id}>{group.group_name}</Option>
												})
}
										</Select>
								)}
								{showCreateGroup
										? <Button onClick={this.onAddGroup}>新建组</Button>
										: null}
						</Form.Item>
						<Form.Item {...formItemLayout} label="镜像地址">
								{getFieldDecorator('docker_cmd', {
										initialValue: data.docker_cmd || '',
										rules: [
												{
														required: true,
														message: '请输入镜像名称'
												}
										]
								})(<Input
										style={{
										width: 'calc(100% - 100px)'
								}}
										placeholder="请输入镜像名称, 如 nginx : 1.11"/>)}
						</Form.Item>

						{showSubmitBtn
							? <Form.Item
									wrapperCol={{
										xs: {
												span: 24,
												offset: 0
										},
										sm: {
												span: formItemLayout.wrapperCol.span,
												offset: formItemLayout.labelCol.span
										}
									}}
									label="">
									<Button onClick={this.handleSubmit} type="primary">
											新建应用
									</Button>
									</Form.Item>
							: null
}
					</Form>
					{this.state.addGroup && <AddGroup onCancel={this.cancelAddGroup} onOk={this.handleAddGroup}/>}
				</Fragment>
			)
		}
}