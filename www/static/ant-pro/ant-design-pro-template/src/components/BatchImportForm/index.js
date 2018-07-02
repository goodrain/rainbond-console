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
		Modal,
		message
} from 'antd';
import globalUtil from '../../utils/global';



@connect(({user, global}) => ({groups: global.groups}), null, null, {withRef: true})
@Form.create()
export default class Index extends PureComponent {
		constructor(props) {
			super(props);
			this.state = {
				fileList:[]
			}
		}
		handleSubmit = ()=>{
			const event_id = this.props.event_id;
			const source_dir = this.props.source_dir;
			this
			.props
			.dispatch({
				type: 'createApp/importApp',
				payload: {
					team_name: globalUtil.getCurrTeamName(),
					scope: 'enterprise',
					event_id: event_id,
					file_name: this.state.file_name
				},
				callback: ((data) => {
					message.success('操作成功，正在导入',2);
					// this.props.onOk && this.props.onOk(data);
				})
        	})
		}

		handleQueryImportDir = ()=>{
			const event_id = this.props.event_id;
			const source_dir = this.props.source_dir;
			this
			.props
			.dispatch({
				type: 'createApp/queryImportDirApp',
				payload: {
					team_name: globalUtil.getCurrTeamName(),
					event_id:event_id
				},
				callback: ((data) => {
					this.setState({fileList:data.list},()=>{
						 if(this.state.fileList.length >0){
							 this.props.onOk && this.props.onOk(this.state.fileList)
						 }else{
							message.info('您还没有放入文件，请先放入文件！',2);
						 }
					});

				})
			})
		}
		render() {
			const event_id = this.props.event_id;
			const source_dir = this.props.source_dir;
			return (
				<Modal
					visible={true}
					onCancel={this.props.onCancel}
					onOk={this.handleQueryImportDir}
					title="批量导入应用"
					>
					<div>
						<p>请将要上传的文件，放入<strong>{source_dir}</strong>目录，然后点击“确认”按钮</p>
					</div>
				</Modal>
			)
		}
}