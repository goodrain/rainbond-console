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
import styles from './Index.less';
import AddGroup from '../../components/AddOrEditGroup';
import globalUtil from '../../utils/global';
import ImageCmdForm from '../../components/ImageCmdForm';
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
	handleSubmit = (value) => {
		const teamName = globalUtil.getCurrTeamName();
		this
			.props
			.dispatch({
				type: 'createApp/createAppByDockerrun',
				payload: {
					team_name: teamName,
					image_type: 'docker_run',
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
		const image = decodeURIComponent(this.props.match.params.image||'');
		return (
			<Card >
				<div className={styles.formWrap}>
					<ImageCmdForm data={{docker_cmd: image||''}} onSubmit={this.handleSubmit}/>
				</div>
			</Card>
		)
	}
}