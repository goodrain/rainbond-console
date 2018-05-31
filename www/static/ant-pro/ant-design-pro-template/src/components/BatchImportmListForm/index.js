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
				showapp:true,
				showsubBtn:true,
				source_dir:this.props.source_dir,
				showImport:true
			}
			this.mountImport = false;
			this.mountQueryImport = true;
		}

		componentDidMount() {
			this.mountImport = true;
			this.handleQueryImportDir();
		}
		componentWillUnmount() {
			this.mountImport = false;
			this.mountQueryImport = false;
		}

		handleSubmit = ()=>{
			if(this.state.file_name == ''){
				notification.info({
					message: '请先选择应用'
				})
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
					notification.success({
						message: '操作成功，正在导入'
					})
					this.setState({showImport:false})
					this.queryImportApp();
					// this.props.onOk && this.props.onOk(data);
				})
        	})
		}
		
        handleQueryImportDir = ()=>{
			if (!this.mountQueryImport) 
  			return;
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
					this.setState({fileList:data.list});
					setTimeout(() => {
						this.handleQueryImportDir();
					}, 2000)
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
			this.mountQueryImport = false;
			if (!this.mountImport) 
  			return;
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
					this.setState({importlist:data.list,showappstatus:true,showapp:false,showsubBtn:false})
					setTimeout(() => {
						this.queryImportApp();
					}, 2000)
				})
        	})
		}
		reImportApp = (app,e) =>{
			console.log(app)
			console.log(e)
			const event_id = this.props.event_id;
			this
			.props
			.dispatch({
				type: 'createApp/importApp',
				payload: {
					team_name: globalUtil.getCurrTeamName(),
					scope: 'enterprise',
					event_id: event_id,
					file_name: app.file_name
				},
				callback: ((data) => {
					notification.success({
						message: '操作成功，正在导入'
					})
				})
        	})
		}
		render() {
			const importlist = this.state.importlist;
			const showsubBtn = this.state.showsubBtn;
			const list = this.state.fileList;
			return (
				<Modal
					visible={true}
					onCancel={this.props.onCancel}
					onOk={this.handleSubmit}
					title="批量导入应用"
					footer={
						showsubBtn ?
						[
						<Button key="back" onClick={this.props.onCancel}>关闭</Button>,
						<Button key="submit" type="primary"  onClick={this.handleSubmit}>
							导入
						</Button>
					   ]
					   :
					   [
						<Button key="back" onClick={this.props.onCancel}>关闭</Button>
					   ]
					}
						
					>
					<div>
					{
						(!this.state.showImport && importlist.length != 0) ?
						<ul>	
							{
								importlist.map((app)=>{
									return (
									<li style={{ lineHeight: '30px',paddingBottom:'5px' }}>
										{app.file_name}  
										<span style={{padding:"0 5px"}}>{appstatus[app.status]}</span>
										{
											app.status == 'failed'?
											<Button onClick={this.reImportApp.bind(this,app)} type="primary" size="small">重新导入</Button>
											:
											''
										}
									</li>
									)
								})
							}
						</ul>
						:
						''
					}
					{	
						this.state.showImport ?
						<div>
							<p>请选择需要导入的应用</p>
							<Checkbox.Group  onChange={this.onChange} style={{display:'block'}}>
								<Row>
									{
										list.map((order)=>{
											return(
												<Col span={24}><Checkbox value={order}>{order}</Checkbox></Col>
											)
										})
									}
								</Row>
							</Checkbox.Group>
						</div>
						:
						''
					}
					{
						(!this.state.showImport && importlist.length == 0) ?
						<p>请稍后，导入中...</p>
						:
						''
					}
					</div>
				</Modal>
			)
		}
}