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
				notification
} from 'antd';
import rainbondUtil from '../../utils/rainbond';
import globalUtil from '../../utils/global';
import {getGithubInfo} from '../../services/team';
import CodeGithubForm from '../../components/CodeGithubForm';
import styles from './Index.less';

@connect(({user, global}) => ({}))
export default class Index extends PureComponent {
				constructor(props) {
								super(props);
								this.state = {
												//是否绑定了github仓库
												is_auth: '',
												//绑定github的地址
												auth_url: '',
												//代码分支及版本信息
												codeList: []
								}
				}
				componentDidMount() {
								const rainbondInfo = this.props.rainbondInfo;
								if (rainbondUtil.githubEnable(rainbondInfo)) {
												this.getGithubInfo();
								}
				}
				getGithubInfo = () => {
								getGithubInfo({
												team_name: globalUtil.getCurrTeamName()
								}).then((data) => {
												if (data && data.bean) {
																if (!data.bean.is_auth) {
																				this.setState({auth_url: data.bean.url})
																				return;
																}
																this.setState({is_auth: true, codeList: data.list});
												}
								})
				}
				toAuth = () => {
								if (this.state.auth_url) {
												location.href = this.state.auth_url;
								}

				}
				handleSubmit = (value) => {
								const teamName = globalUtil.getCurrTeamName();
								this
												.props
												.dispatch({
																type: 'createApp/createAppByCode',
																payload: {
																				team_name: teamName,
																				code_from: 'github',
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
								const is_auth = this.state.is_auth;

								return (
												<Card >
																<div className={styles.formWrap}>

																				{(!is_auth)
																								? <div
																																style={{
																																textAlign: 'center',
																																padding: '100px 0',
																																fontSize: 14
																												}}>
																																尚未绑定github仓库
																																<Button
																																				onClick={this.toAuth}
																																				style={{
																																				marginLeft: 20
																																}}
																																				type="primary">点击绑定</Button>
																												</div>
																								: <CodeGithubForm onSubmit={this.handleSubmit}/>
}
																</div>
												</Card>
								)
				}
}