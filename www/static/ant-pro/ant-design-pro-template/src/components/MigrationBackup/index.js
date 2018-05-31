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

const FormItem = Form.Item;
const Option = Select.Option;

const appRestore = {
	'starting':'迁移中',
	'success':'成功',
	'failed':'失败'
}


@connect(({user, global}) => ({currUser: user.currentUser}))
@Form.create()
export default class Index extends PureComponent {
		constructor(props) {
			super(props);
			this.state = {
				teamsData:[],
				regionData:[],
				teamsName:'',
				regionName:'',
				teamsAlias:'',
				regionAlias:'',
				backup_id:this.props.backupId,
				restore_id:'',
				showRestore:false,
				restore_status:''
			}
			this.mount = false;
		}

		componentDidMount() {
			this.mount = true;
			var teams = this.props.currUser.teams;
			var teamsArr = [];
			teams.map((order)=>{
				var orderbox = {};
				orderbox['team_alias']=order.team_alias;
				orderbox['team_name']=order.team_name;
				orderbox['region']=order.region;
				teamsArr.push(orderbox);
			})
			this.setState({teamsData:teamsArr})
			console.log(teamsArr)
		}
		componentWillUnmount() {
			this.mount = false;
		}

		handleSubmit = (e)=>{
			var teamsName = this.state.teamsName;
			var regionName = this.state.regionName;
			if(teamsName == ''){
				notification.warning({message: "请选择迁移团队"})
                return;
			}
			if(regionName == ''){
				notification.warning({message: "请选择迁移数据中心"})
                return;
			}
			this.props.dispatch({
				type: 'groupControl/migrateApp',
				payload:{
					team_name: globalUtil.getCurrTeamName(),
					region:this.state.regionName,
					team: this.state.teamsName,
					backup_id:this.props.backupId,
					group_id:this.props.groupId
				},
				callback: (data) => {
					notification.success({message: "操作成功，开始迁移应用"});
					this.setState({restore_id:data.bean.restore_id},()=>{
						this.queryMigrateApp()
					})
				}
			})
		}
		
	    //查询迁移状态
	    queryMigrateApp =()=>{
			if (!this.mount) 
  			return;
			this.props.dispatch({
				type: 'groupControl/queryMigrateApp',
				payload:{
					team_name: globalUtil.getCurrTeamName(),
					restore_id:this.state.restore_id,
					group_id:this.props.groupId
				},
				callback: (data) => {
					this.setState({showRestore:true,restore_status:data.bean.status})
					if(data.bean.status == 'starting'){
						setTimeout(() => {
							this.queryMigrateApp();
						}, 2000)
					}
				}
			})
	    }

		handleTeamsChange = (value) => {
			const teamsData = this.state.teamsData;
			var regionList =[];
			teamsData.map((order)=>{
				if(order.team_name == value){
					regionList = order.region
				}
			})
			this.setState({teamsName:value,regionData:regionList,regionName:''})
		}
		onRegionChange = (value) => {
			var regionData = this.state.regionData;
			this.setState({regionName:value})
		}
		
		render() {
			const teamsData = this.state.teamsData || [];
			const regionData = this.state.regionData || [];
		    const restoreStatus = this.state.restore_status
			return (
				<Modal
					visible={true}
					onCancel={this.props.onCancel}
					onOk={this.handleSubmit}
					title="批量导入应用"
					footer={
						this.state.showRestore?
						[<Button key="back" onClick={this.props.onCancel}>关闭</Button>]
						:
						[
						<Button key="back" onClick={this.props.onCancel}>关闭</Button>,
						<Button key="submit" type="primary"  onClick={this.handleSubmit}>
							迁移
						</Button>
					   ]
					}
					>
					{
						this.state.showRestore?
						<div>
							<p style={{textAlign:'center'}}>迁移状态</p>
							<p style={{textAlign:'center',fontSize:'18px'}}>
								{appRestore[restoreStatus]}
							</p>
						</div>
						:
						<div>
							<p>请选择迁移的团队和数据中心</p>
							<Select style={{ width: 120, marginRight:'10px'}} onChange={this.handleTeamsChange}>
								{
									teamsData.map((order)=>{
										return(
											<Option value={order.team_name}>{order.team_alias}</Option>
										)
									})
								}
							</Select>
							<Select style={{ width: 120 }} onChange={this.onRegionChange} >
								{
									regionData.map((order)=>{
										return(
											<Option value={order.team_region_name}>{order.team_region_alias}</Option>
										)
									})
								}
							</Select>
						</div>
					}
					
				</Modal>
			)
		}
}