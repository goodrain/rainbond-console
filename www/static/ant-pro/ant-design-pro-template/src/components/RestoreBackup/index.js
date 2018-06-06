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
				backup_id:this.props.backupId,
				showRestore:false
			}
			this.mount = false;
		}

		componentDidMount() {
			
		}
		componentWillUnmount() {
			this.mount = false;
		}

		handleSubmit = (e)=>{
			this.setState({showRestore:true})
		}
		
	    
	
		render() {
			return (
				<Modal
					visible={true}
					onCancel={this.props.onCancel}
					onOk={this.handleSubmit}
					title="恢复备份"
					footer={
						this.state.showRestore?
						[
						<Button key="back" onClick={this.props.onCancel}>关闭</Button>,
						<Button key="submit" type="primary"  onClick={this.handleSubmit}>
							确定
						</Button>
						]
						:
						[
						<Button key="back" onClick={this.props.onCancel}>关闭</Button>,
						<Button key="submit" type="primary"  onClick={this.handleSubmit}>
							恢复
						</Button>
					   ]
					}
					>
					{
						this.state.showRestore?
						<div>
							<p>
							   您需要要删除备份前的文件么？
							</p>
						</div>
						:
						<div>
							<p>您要恢复备份到当前数据中心么？</p>
						</div>
					}
					
				</Modal>
			)
		}
}