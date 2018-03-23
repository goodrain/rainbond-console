import React, { PureComponent, Fragment } from 'react';
import { connect } from 'dva';
import { Link, Switch, Route, routerRedux } from 'dva/router';
import { Row, Col, Card, Form, Button, Icon, Menu, Dropdown, notification, Select, Input, Modal} from 'antd';
import AddGroup from '../../components/AddOrEditGroup';
import globalUtil from '../../utils/global';
import ShowRegionKey from '../../components/ShowRegionKey';

const { Option } = Select;


class ShowKeyModal extends PureComponent {
	constructor(props){
		super(props);
		this.state = {

		}
	}
	componentDidMount(){

	}
	render(){
		const { onCancel } = this.props;
		return (
			<Modal
				title="配置授权Key"
				visible={true}
				onCancel={onCancel}
				footer={[<Button onClick={onCancel}>已授权</Button>]}
			>
				<p><Icon type="info-circle-o" /> 请拷贝如下Key到您的私有Git仓库进行授权，云帮平台方可访问您的私有Git仓库</p>
				<p style={{border: '1px dotted #dcdcdc', padding: '20px'}}>
					sdfsdfsdfsdf
				</p>
			</Modal>
		)
	}
}



const formItemLayout = {
  labelCol: {
    span: 5,
  },
  wrapperCol: {
    span: 19,
  },
};

@connect(({ user, global }) => ({
  currUser: user.currentUser,
  groups: global.groups
}), null, null, {withRef: true})

@Form.create()
export default class Index extends PureComponent {
	constructor(props){
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

		this.props.dispatch({
			type:'groupControl/addGroup',
			payload: {
				team_name: globalUtil.getCurrTeamName(),
				...vals
			},
			callback: (group) => {
				 
				 if(group){
				 	
				 	//获取群组
			          this.props.dispatch({
			            type: 'global/fetchGroups',
			            payload: {
			               team_name: globalUtil.getCurrTeamName(),
			               region_name: globalUtil.getCurrRegionName(),
			            },
			            callback: ()=>{
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
	handleSubmit = (e) => {
		e.preventDefault();
		const form = this.props.form;
		form.validateFields((err, fieldsValue) => {
	        if (err) return;
	        this.props.onSubmit && this.props.onSubmit(fieldsValue)
	    });
	}
	render(){
		const { getFieldDecorator, getFieldValue } = this.props.form;
		const {groups} = this.props;
		const {showUsernameAndPass, showKey} = this.state;
		const gitUrl = getFieldValue('git_url');
		const isHttp = /^(http:\/\/|https:\/\/)/.test(gitUrl||'');
		const isSSH = !isHttp;

		const data = this.props.data || {};
		const showSubmitBtn = this.props.showSubmitBtn === void 0 ? true : this.props.showSubmitBtn;
		const showCreateGroup = this.props.showCreateGroup === void 0 ? true : this.props.showCreateGroup;
		return (
				<Fragment>
			        <Form onSubmit={this.handleSubmit} layout="horizontal" hideRequiredMark>
			          <Form.Item
			            {...formItemLayout}
			            label="应用名称"
			          >
			            {getFieldDecorator('service_cname', {
			              initialValue: data.service_cname || '',
			              rules: [{ required: true, message: '要创建的应用还没有名字' }],
			            })(
			              <Input placeholder="请为创建的应用起个名字吧" />
			            )}
			          </Form.Item>
			          <Form.Item
			            {...formItemLayout}
			            label="应用组"
			          >
			            {getFieldDecorator('group_id', {
			              initialValue: data.group_id||-1,
			              rules: [{ required: true, message: '请选择' }],
			            })(
			              <Select placeholder="请选择要所属应用组" style={{display: 'inline-block', width: 306, marginRight: 15}}>
			              {
			              	(groups || []).map((group)=>{
			              		return <Option value={group.group_id}>{group.group_name}</Option>
			              	})
			              }
			              </Select>
			            )}
			            {showCreateGroup ? <Button onClick={this.onAddGroup}>新建组</Button> : null}
			          </Form.Item>
			          <Form.Item
			            {...formItemLayout}
			            label="仓库地址"
			          >
			            <Input.Group compact>
			              <Select defaultValue={this.state.codeType} style={{ width: 100 }}>
			                <Option value="Git">Git</Option>
			              </Select>
			              {getFieldDecorator('git_url', {
			                initialValue: data.git_url || '',
			                rules: [
			                  { required: true, message: '请输入仓库地址' },
			                  { pattern: /^(.+@.+\.git)|([^@]+\.git(\?.+)?)$/gi, message: '仓库地址不正确' }
			                ],
			              })(
			                <Input style={{ width: 'calc(100% - 100px)' }} placeholder="请输入仓库地址" />
			              )}
			            </Input.Group>
			            {
			            	(gitUrl && isSSH) ? 
			            	<div style={{textAlign: 'right'}}>这是一个私有仓库? <a onClick={()=>{this.setState({showKey: true})}} href="javascript:;">配置授权Key</a></div>
			            	:''
			            }
			            {
			            	(gitUrl && isHttp) ? 
			            	<div style={{textAlign: 'right'}}>这是一个私有仓库? <a onClick={()=>{this.setState({showUsernameAndPass: true})}} href="javascript:;">填写仓库账号密码</a></div>
			            	:''
			            }
			          </Form.Item>
			          <Form.Item
			            style={{display: (showUsernameAndPass && isHttp) ? '': 'none'}}
			            {...formItemLayout}
			            label="仓库用户名"
			          >
			            {getFieldDecorator('username_1', {
			              initialValue: data.username || '',
			              rules: [{ required: false, message: '请输入仓库用户名' }],
			            })(
			              <Input  autoComplete="off" placeholder="请输入仓库用户名" />
			            )}
			          </Form.Item>
			          <Form.Item
			          	 style={{display: (showUsernameAndPass && isHttp) ? '': 'none'}}
			            {...formItemLayout}
			            label="仓库密码"
			          >
			            {getFieldDecorator('password_1', {
			              initialValue: data.password || '',
			              rules: [{ required: false, message: '请输入仓库密码' }],
			            })(
			              <Input autoComplete="new-password" type="password" placeholder="请输入仓库密码" />
			            )}
			          </Form.Item>
			          <Form.Item
			            {...formItemLayout}
			            label="代码分支"
			          >
			            {getFieldDecorator('code_version', {
			              initialValue: data.code_version || 'master',
			              rules: [{ required: true, message: '请输入代码分支' }],
			            })(
			              <Input placeholder="请输入代码分支" />
			            )}
			          </Form.Item>
			          
			          {
			          showSubmitBtn ? 
			          <Form.Item
			            wrapperCol={{
			              xs: { span: 24, offset: 0 },
			              sm: { span: formItemLayout.wrapperCol.span, offset: formItemLayout.labelCol.span },
			            }}
			            label=""
			          >
			          	
			          		<Button  onClick={this.handleSubmit} type="primary">
				              新建应用
				            </Button>
				          
			            
			          </Form.Item>
			            :null
			          }
			        </Form>
			      {this.state.addGroup && <AddGroup onCancel={this.cancelAddGroup} onOk={this.handleAddGroup} />}
			      {(showKey && isSSH) && <ShowRegionKey onCancel={this.hideShowKey} />}
			</Fragment>
		)
	}
}