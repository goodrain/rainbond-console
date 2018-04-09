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
	Alert
} from 'antd';
import rainbondUtil from '../../utils/rainbond';
import globalUtil from '../../utils/global';
import CodeGoodrainForm from '../../components/CodeGoodrainForm';
import GitlabAccountForm from '../../components/GitlabAccountForm';
import Result from '../../components/Result';
import userUtil from '../../utils/user';
import styles from './Index.less';

@connect(({user, global}) => ({user: user.currentUser}))
export default class Index extends PureComponent {
	constructor(props) {
		super(props);
		this.state = {
			registerGitlabSuccess: false
		}
	}
	componentDidMount() {}
	handleSubmit = (value) => {
		const teamName = globalUtil.getCurrTeamName();
		const gitUrl = value.git_url;
		this
			.props
			.dispatch({
				type: 'createApp/createAppByCode',
				payload: {
					team_name: teamName,
					code_from: 'gitlab_exit',
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
	handleAccountSubmit = (value) => {
		this
			.props
			.dispatch({
				type: 'user/gitlabRegister',
				payload: {
					...value
				},
				callback: (data) => {
					this
						.props
						.dispatch({
							type: 'user/fetchCurrent',
							callback: () => {
								this.setState({registerGitlabSuccess: true})
							}
						})

				}
			})
	}
	renderRegisterGitlabSuccess = () => {
		const user = this.props.user;
		const extra = (
			<div>
				<p>用户名: {user.email}
					或 {user.phone || '手机号'}</p>
				<p>密&nbsp;&nbsp;&nbsp;&nbsp;码: 同云帮登录密码</p>
			</div>
		);
		const actions = [ <Button onClick = {
			() => {
				this.setState({registerGitlabSuccess: false})
			}
		}
		type = "primary" > 点击继续创建应用 </Button>];
		return <Result
			type="success"
			title="好雨Git账号注册成功"
			description="已下是您的好雨Git账号信息"
			extra={extra}
			actions={actions}
			style={{ marginTop: 48, marginBottom: 16 }}
		/ >
	}
	render() {

		const codeList = this.state.codeList;
		const user = this.props.user;
		return (
			<Card >
				<div className={styles.formWrap}>

					{(!userUtil.hasGitlatAccount(user))
					? <div>
						<Alert message="请先注册您的好雨Git账号" type="warning" closable/>
							<div
								style={{
								marginBottom: 32
							}}></div>
							<GitlabAccountForm
								data={{
								email: user.email
							}}
								onSubmit={this.handleAccountSubmit}/>
							</div>
					: <div>
						{!this.state.registerGitlabSuccess && <CodeGoodrainForm onSubmit={this.handleSubmit}/>}
					</div>
					}
					{this.state.registerGitlabSuccess && this.renderRegisterGitlabSuccess()}
				</div>
			</Card>
		)
	}
}