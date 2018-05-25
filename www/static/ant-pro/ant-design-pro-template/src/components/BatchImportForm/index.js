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
import globalUtil from '../../utils/global';



@connect(({user, global}) => ({groups: global.groups}), null, null, {withRef: true})
@Form.create()
export default class Index extends PureComponent {
		constructor(props) {
			super(props);
			this.state = {
					
			}
		}
		handleSubmit = ()=>{
			
		}
		render() {
			 	const {onCancel} = this.props;
				return (
					<Modal
						visible={true}
						onCancel={onCancel}
						onOk={this.handleSubmit}
						title="批量导入应用"
						okText="导入"
						>
					</Modal>
				)
		}
}