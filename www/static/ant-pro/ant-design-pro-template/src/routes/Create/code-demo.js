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
				Input
} from 'antd';
import styles from './Index.less';
import CodeDemoForm from '../../components/CodeDemoForm';
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

@connect(({user, global}) => ({currUser: user.currentUser, groups: global.groups}))

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
					setFieldsValue({group: 111})
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
	handleSubmit = (value) => {
		const teamName = globalUtil.getCurrTeamName();
		this
			.props
			.dispatch({
				type: 'createApp/createAppByCode',
				payload: {
					team_name: teamName,
					code_from: 'gitlab_demo',
					...value
				},
				callback: (data) => {
					const appAlias = data.bean.service_alias;
					this
						.props
						.dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/create/create-check/${appAlias}`));
				}
			})
	}
	render() {
		const {getFieldDecorator, getFieldValue} = this.props.form;
		const {groups} = this.props;
		const code = decodeURIComponent(this.props.match.params.code||'');
		return (
			<Card >
				<div className={styles.formWrap}>
					<CodeDemoForm data={{git_url: code||''}} onSubmit={this.handleSubmit}/>
				</div>
			</Card>
		)
	}
}