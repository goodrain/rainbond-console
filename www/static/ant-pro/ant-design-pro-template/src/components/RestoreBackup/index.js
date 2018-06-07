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
		Spin
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
				backup_id:this.props.backupId,
				restore_id:'',
				showRestore:false,
				restore_status:'',
				new_group_id:''
			}
			this.mount = false;
		}

		componentDidMount() {
			this.mount = true;
			
		}
		componentWillUnmount() {
			this.mount = false;
		}

		handleRestore = (e)=>{
			var teamsName = this.state.teamsName;
			var regionName = this.state.regionName;
			this.props.dispatch({
				type: 'groupControl/migrateApp',
				payload:{
					team_name: globalUtil.getCurrTeamName(),
					region:this.props.propsParams.region,
					team: this.props.propsParams.team,
					backup_id:this.props.backupId,
					group_id:this.props.groupId,
					migrate_type:'recover'
				},
				callback: (data) => {
					notification.success({message: "开始恢复中",duration:'2'});
					this.setState({restore_id:data.bean.restore_id},()=>{
						this.queryMigrateApp()
					})
				}
			})
		}

		handleSubmit = (e)=>{
			var teamsName = this.state.teamsName;
			var regionName = this.state.regionName;
			this.props.dispatch({
				type: 'groupControl/migrateApp',
				payload:{
					team_name: globalUtil.getCurrTeamName(),
					region:this.props.propsParams.region,
					new_group_id:this.state.new_group_id
				},
				callback: (data) => {
					notification.success({message: "删除成功",duration:'2'});
					this.props.onCancel & this.props.onCancel()
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
					this.setState({showRestore:true,restore_status:data.bean.status,new_group_id:data.bean.group_id})
					if(data.bean.status == 'starting'){
						setTimeout(() => {
							this.queryMigrateApp();
						}, 2000)
					}
				}
			})
	    }

	  
		
		render() {
			const restoreStatus = this.state.restore_status;
			return (
				<Modal
					visible={true}
					onCancel={this.props.onCancel}
					title="迁移"
					footer={
						!this.state.showRestore?
						[<Button key="back" onClick={this.props.onCancel}>关闭</Button>,
						<Button key="submit" type="primary"  onClick={this.handleRestore}>
							恢复
						</Button>
						]
						:
						restoreStatus == 'success'?
						[
						<Button key="back" onClick={this.props.onCancel}>关闭</Button>,
						<Button key="submit" type="primary"  onClick={this.handleSubmit}>
							确认
						</Button>	
					   ]
					   :
					   [
						<Button key="back" onClick={this.props.onCancel}>关闭</Button>
					   ]
					}
					>
					{
						this.state.showRestore?
						<div>
							{
								restoreStatus == 'starting'?
								<div>
									<p style={{textAlign:'center'}}>
										<Spin />
									</p>
									<p style={{textAlign:'center',fontSize:'14px'}}>
										恢复中，请稍后(请勿关闭弹窗)
									</p>
								</div>
								:''

							}
							{
								restoreStatus == 'success'?
								<div>
									<p style={{textAlign:'center',color:"#28cb75", fontSize:'36px'}}>
										<Icon type="check-circle-o" />
									</p>
									<p style={{textAlign:'center',fontSize:'14px'}}>
										恢复成功，是否删除原备份？
									</p>
								</div>
								:''
							}
							{
								restoreStatus == 'failed'?
								<div>
									<p style={{textAlign:'center',color:'999', fontSize:'36px'}}>
										<Icon type="close-circle-o" />
									</p>
									<p style={{textAlign:'center',fontSize:'14px'}}>
										恢复失败，请重新恢复
									</p>
								</div>
								:''
							}
						</div>
						:
						<div>
							<p>您是否要恢复备份到当前数据中心?</p>
						</div>
					}
					
				</Modal>
			)
		}
}