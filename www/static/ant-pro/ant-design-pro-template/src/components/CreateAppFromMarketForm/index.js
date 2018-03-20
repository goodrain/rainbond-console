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
		fetchGroup = () => {
				this
						.props
						.dispatch({
								type: 'global/fetchGroups',
								payload: {
										team_name: globalUtil.getCurrTeamName()
								}
						})
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
				const {groups, onCancel} = this.props;
				const data = this.props.data || {};

				return (
						<Modal
								visible={true}
								onCancel={onCancel}
								onOk={this.handleSubmit}
								title="要安装到哪个应用组?"
								footer={[< Button onClick = {
										onCancel
								} > 取消 < /Button>, <Button type="primary" disabled={this.props.disabled} onClick={this.handleSubmit}>确定</Button >]}>
								<Form onSubmit={this.handleOk} layout="horizontal" hideRequiredMark>
										<Form.Item {...formItemLayout} label="选择应用组">
												{getFieldDecorator('group_id', {
														initialValue: data.groupd_id || -1,
														rules: [
																{
																		required: true,
																		message: '请选择'
																}
														]
												})(
														<Select
																style={{
																display: 'inline-block',
																width: 220,
																marginRight: 15
														}}>
																{(groups || []).map((group) => {
																		return <Option value={group.group_id}>{group.group_name}</Option>
																})
}
														</Select>
												)}
												<Button onClick={this.onAddGroup}>新建组</Button>
										</Form.Item>
										{this.state.addGroup && <AddGroup onCancel={this.cancelAddGroup} onOk={this.handleAddGroup}/>}
								</Form>
						</Modal>

				)
		}
}