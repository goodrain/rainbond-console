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
		message,
		Checkbox
} from 'antd';
import globalUtil from '../../utils/global';
const CheckboxGroup = Checkbox.Group;
const FormItem = Form.Item;

const appstatus ={
	'pending':'等待中',
	'importing':'导入中',
	'success':'成功',
	'failed':'失败'
}

@connect(({user, global}) => ({groups: global.groups}), null, null, {withRef: true})
@Form.create()
export default class Index extends PureComponent {
		constructor(props) {
			super(props);
			this.state = {
				file_name:'',
				fileList: this.props.file_name,
				event_id:this.props.event_id,
				importlist:[],
				showappstatus:false,
				showapp:true
			}
		}
		handleSubmit = ()=>{
			if(this.state.file_name == ''){
				message.info('请先选择应用',2);
				return;
			}
			const event_id = this.props.event_id;
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
					this.queryImportApp();
					// this.props.onOk && this.props.onOk(data);
				})
        	})
		}
		
		onChange =(e)=>{
			var fileStr = '';
			e.map((order)=>{
				fileStr += order + ','
			})
			console.log(fileStr)
			fileStr = fileStr.slice(0,(fileStr.length-1))
			console.log(fileStr)
			this.setState({file_name:fileStr})
		}
		queryImportApp=()=>{
			const event_id = this.props.event_id;
			this
			.props
			.dispatch({
				type: 'createApp/queryImportApp',
				payload: {
					team_name: globalUtil.getCurrTeamName(),
					event_id: event_id
				},
				callback: ((data) => {
					console.log(data.list)
					this.setState({importlist:data.list,showappstatus:true,showapp:false})
				})
        	})
		}
		render() {
			const importlist = this.state.importlist;
			console.log(importlist)
			return (
				<Modal
					visible={true}
					onCancel={this.props.onCancel}
					onOk={this.handleSubmit}
					title="批量导入应用"
					>
					<div>
					{
						importlist.length == 0?
						<div>
							<p>请选择需要导入的应用</p>
							<CheckboxGroup options={this.state.fileList} onChange={this.onChange}/>
						</div>
						:
						<ul>
							{
								importlist.map((app)=>{
									return (
									<li>
										{app.file_name}
										<span>{appstatus[app.status]}</span>
									</li>
									)
								})
							}
						</ul>
					}
					</div>
				</Modal>
			)
		}
}