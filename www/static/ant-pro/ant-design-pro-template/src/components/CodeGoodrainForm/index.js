import React, { PureComponent } from 'react';
import { connect } from 'dva';
import { Link, Switch, Route, routerRedux } from 'dva/router';
import { Row, Col, Card, Form, Button, Icon, Menu, Dropdown, notification, Select, Input, Modal} from 'antd';
import AddGroup from '../../components/AddOrEditGroup';
import globalUtil from '../../utils/global';
import {getGitlabInfo} from '../../services/team';
import {getCodeBranchs} from '../../services/createApp';


const FormItem = Form.Item;
@Form.create()
class CreateNewProject extends PureComponent{
	handleOk = (e) => {
		e.preventDefault();
	    this.props.form.validateFields({force: true}, (err, vals)=>{
	       if(!err){
	          this.props.onOk && this.props.onOk(vals)
	       }
	    })
	}
	handleCancel = () => {
		this.props.onCancel && this.props.onCancel();
	}
	render(){
		const isOk = this.props.isOk;
		const { getFieldDecorator, getFieldValue } = this.props.form;
	     const formItemLayout = {
	      labelCol: {
	        xs: { span: 24 },
	        sm: { span: 6 },
	      },
	      wrapperCol: {
	        xs: { span: 24 },
	        sm: { span: 16 }
	      },
	    };
		return(
			<Modal
				title="新建好雨Git项目"
				visible={true}
				onOk={this.handleOk}
				onCancel={this.handleCancel}
			>
				<Form onSubmit={this.onOk}>
	              <FormItem
	              {...formItemLayout}
	              label="项目名称"
	              >
	              {
	                getFieldDecorator('project_name', {
	                  initialValue: '',
	                  rules:[{required: true, message: '项目名称'}]
	                })(
	                  <Input placeholder="请为创建的项目起个名字吧" />
	                )
	              }
	              </FormItem>
	          </Form>

			</Modal>
		)
	}
}





const { Option } = Select;
const formItemLayout = {
  labelCol: {
    span: 5,
  },
  wrapperCol: {
    span: 19,
  },
};

@connect(({ user, global }) => ({
  groups: global.groups
}), null, null, {withRef: true})

@Form.create()
export default class Index extends PureComponent {
	constructor(props){
		super(props);
		this.state = {
			addGroup: false,
			showCreateProject: false,
			gitlabUrl:'',
			gitlabId: '',
			codeList:[],
			branchs:[]
		}
	}
	componentDidMount(){
		this.getGitlabInfo();
	}
	onAddGroup = () => {
		this.setState({addGroup: true})
	}
	cancelAddGroup = () => {
		this.setState({addGroup: false})
	}
	handleSubmit = (e) => {
		e.preventDefault();
		const form = this.props.form;
		form.validateFields((err, fieldsValue) => {
	        if (err) return;
	        var codeId = fieldsValue.git_project_id;
	        var selectedProject = this.state.codeList.filter((item)=>{
	        	return item.code_id === codeId;
	        })
	        if(selectedProject.length){
	        	fieldsValue.git_url = selectedProject[0].code_repos;
	        }
	        this.props.onSubmit && this.props.onSubmit(fieldsValue)
	    });
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
	fetchGroup = () => {
		this.props.dispatch({
			type: 'global/fetchGroups',
			payload:{
				team_name: globalUtil.getCurrTeamName()
			}
		})
	}
	onCreateProject = () => {
		this.setState({showCreateProject: true})
	}
	handleCancelCreateProject = () => {
		this.setState({showCreateProject: false})
	}
	handleCreateProject = (value) => {
		 this.props.dispatch({
			type:'user/createGitlabProject',
			payload:{
				team_name: globalUtil.getCurrTeamName(),
				...value
			},
			callback:(bean)=>{
				this.setState({gitlabUrl: bean.http_repo_url, gitlabId: bean.project_id})
				this.handleCancelCreateProject();
				this.showCreateProjectOk();
			}
		})
	}
	showCreateProjectOk = () => {
		Modal.success({
		    title: '创建项目成功',
		    content: <div>

		    	<p>项目地址: <a target="_blank" href={this.state.gitlabUrl}>{this.state.gitlabUrl}</a></p>
		    	<p>请前往上传源码, 完成后点击 已上传源码 继续创建</p>
		    </div>,
		    onOk: ()=>{
					this.props.form.setFieldsValue({'git_project_id': this.state.gitlabId})
					this.getGitlabInfo();
		    },
		    okText: '已上传源码'
		});
	}
	getGitlabInfo = () => {
		var self = this;
		
		return getGitlabInfo({
			team_name: globalUtil.getCurrTeamName()
		}).then((data)=>{
			 if(data && data.bean){
			 	self.setState({codeList: data.list ||[]}, ()=>{
					const { getFieldValue } = this.props.form;
					const defaultProjectId = getFieldValue('git_project_id') || this.getDefaultProjectId();
			 		if(defaultProjectId){
			 			this.getCodeBranchs(defaultProjectId);
			 		}
			 	});
			 }
		})
	}
	getCodeBranchs = (projectId) => {
		  const git  = this.state.codeList.filter((item) => {
		  	   return item.code_id === projectId
		  })[0];
		  	
		  getCodeBranchs({
		  	team_name: globalUtil.getCurrTeamName(),
		  	service_project_id: projectId,
		  	type:'gitlab',
		  	git_url: git.code_repos
		  }).then((data)=>{
		  	  if(data) {
		  	  	 this.setState({branchs: data.list || []})
		  	  }
		  })
	}
	handleCodeIdChange = (val) => {
		const { setFieldsValue } = this.props.form;
		setFieldsValue({code_version: 'master'});
		this.getCodeBranchs(val);
	}
	getDefaultProjectId = () => {
		const data = this.props.data || {};
		const codeList = this.state.codeList || [];
		var defaultProject = data.git_project_id || '';
		if(!defaultProject && codeList.length){
			defaultProject = codeList[0].code_id;
		}
		return defaultProject;
	}
	render(){
		const { getFieldDecorator, getFieldValue } = this.props.form;
		const {groups} = this.props;
		const data = this.props.data || {};
		const codeList = this.state.codeList || [];
		var defaultProject = this.getDefaultProjectId();
		const branchs = this.state.branchs || [];
		return (
			        <Form  layout="horizontal" hideRequiredMark>
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
			              initialValue: data.groupd_id || -1,
			              rules: [{ required: true, message: '请选择' }],
			            })(
			              <Select style={{display: 'inline-block', width: 290, marginRight: 15}}>
			              {
			              	(groups || []).map((group)=>{
			              		return <Option value={group.group_id}>{group.group_name}</Option>
			              	})
			              }
			              </Select>
			            )}
			            <Button onClick={this.onAddGroup}>新建组</Button>
			          </Form.Item>
			          <Form.Item
			            {...formItemLayout}
			            label="好雨Git项目"
			          >
			            {getFieldDecorator('git_project_id', {
			              initialValue: defaultProject,
			              rules: [{ required: true, message: '请选择' }],
			            })(
			              <Select placeholder={defaultProject ? '请选择' : "暂无项目，请先创建"} onChange={this.handleCodeIdChange} style={{display: 'inline-block', width: 290, marginRight: 15}}>
			              	{
			              		codeList.map((item)=>{
			              			return <Option value={item.code_id}>{item.code_project_name}</Option>
			              		})
			              	}
			              </Select>
			            )}
			            <Button onClick={this.onCreateProject}>新建项目</Button>
			          </Form.Item>
			          <Form.Item
			            {...formItemLayout}
			            label="代码分支"
			          >
			            {getFieldDecorator('code_version', {
			              initialValue: data.code_version || 'master',
			              rules: [{ required: true, message: '请选择' }],
			            })(
			              <Select>
			              	{
			              		branchs.map((item) => {
			              			return <Option value={item}>{item}</Option>
			              		})
			              	}
			              </Select>
			            )}
			          </Form.Item>
			          <Form.Item
			            wrapperCol={{
			              xs: { span: 24, offset: 0 },
			              sm: { span: formItemLayout.wrapperCol.span, offset: formItemLayout.labelCol.span },
			            }}
			            label=""
			          >
			            <Button disabled={!codeList.length}   onClick={this.handleSubmit} type="primary">
			              免费创建
			            </Button>
			          </Form.Item>
			          {this.state.addGroup && <AddGroup onCancel={this.cancelAddGroup} onOk={this.handleAddGroup} />}
			          {this.state.showCreateProject && <CreateNewProject onOk={this.handleCreateProject} onCancel={this.handleCancelCreateProject} />}
			        </Form>

		)
	}
}