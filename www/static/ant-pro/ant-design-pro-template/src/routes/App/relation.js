import React, { PureComponent, Fragment } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import { Link, Switch, Route } from 'dva/router';
import { Row, Col, Card, Form, Button, Icon, Menu, Input,  Dropdown, Table, Modal, notification} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import { getRoutes } from '../../utils/utils';
import { getRouterData } from '../../common/router'
import { getRelationedApp , getUnRelationedApp, addRelationedApp, removeRelationedApp, batchAddRelationedApp } from '../../services/app';

import styles from './Index.less';
import globalUtil from '../../utils/global';
import ConfirmModal from '../../components/ConfirmModal';
import ScrollerX from '../../components/ScrollerX';
const FormItem = Form.Item;


//查看连接信息

@connect(({ user, appControl }) => ({
  relationOuterEnvs: appControl.relationOuterEnvs,
}))
class ViewRelationInfo extends PureComponent {
   constructor(props){
      super(props);
      this.state = {
        list:[]
      }
   }
   componentDidMount(){
     this.getEnvs();
   }
   getEnvs = () => {
       this.props.dispatch({
         type: 'appControl/fetchRelationOuterEnvs',
         payload: {
            team_name: globalUtil.getCurrTeamName(),
            app_alias: this.props.appAlias
         }
       })
   }
   componentWillUnmount(){
      this.props.dispatch({
         type: 'appControl/clearRelationOuterEnvs'
       })
   }
   render(){
      const {relationOuterEnvs} = this.props;
      return (
        <Modal
        title="依赖信息查看"
        width={600}
        visible={true}
        onCancel = {this.props.onCancel}
        footer={[<Button onClick={this.props.onCancel}>关闭</Button>]}
        >
        <Table 
        pagination={false}
        columns={[{
          title:'变量名',
          dataIndex: 'attr_name'
        },{
          title:'变量值',
          dataIndex: 'attr_value'
        },{
          title:'说明',
          dataIndex: 'name'
        }]}
        dataSource={relationOuterEnvs || []}
       />
         </Modal>
      )
   }
}


class AddRelation extends PureComponent {
   constructor(props){
     super(props);
     this.state = {
       selectedRowKeys:[],
       apps:[],
       page: 1,
       page_size: 6,
       total:0
     }
   }
   componentDidMount(){
     this.getUnRelationedApp();
   }
   handleSubmit = () => {
      if(!this.state.selectedRowKeys.length){
        notification.warning({
          message: '请选择要依赖的应用'
        })
        return;
      }

      var ids = this.state.selectedRowKeys.map((item) => {
          return this.state.apps[item].service_id
      })
      this.props.onSubmit && this.props.onSubmit(ids);

   }
   getUnRelationedApp = () => {
       getUnRelationedApp({
         team_name: globalUtil.getCurrTeamName(),
         app_alias: this.props.appAlias,
         page: this.state.page,
         page_size: this.state.page_size
      }).then((data) => {
          if(data){
              this.setState({apps: data.list || [], total: data.total, selectedRowKeys: []})
          }
      })
   }
   handleCancel = () => {
     this.props.onCancel && this.props.onCancel();
   }
   onPageChange = (page) => {
     this.setState({page: page}, ()=>{
        this.getUnRelationedApp();
     })
   }
   render(){
      const rowSelection = {
        onChange: (selectedRowKeys, selectedRows) => {
           this.setState({selectedRowKeys: selectedRowKeys})
        },
        selectedRowKeys: this.state.selectedRowKeys
      };

      return (
        <Modal
        title="添加依赖"
        width={600}
        visible={true}
        onOk={this.handleSubmit}
        onCancel = {this.handleCancel}
        >
        <Table
          pagination = {{
            current: this.state.page,
            pageSize: this.state.page_size,
            total: this.state.total,
            onChange: this.onPageChange
          }}
          dataSource={this.state.apps || []}
          rowSelection = {rowSelection}
          columns={[{
            title: '应用名',
            dataIndex: 'service_cname'
          },{
            title: '所属组',
            dataIndex: 'group_name'
          }]}
         />
         </Modal>
      )
   }
}


//添加、编辑变量
@Form.create()
class AddVarModal extends PureComponent {
  handleSubmit = (e) => {
    e.preventDefault();
    this.props.form.validateFields((err, values) => {
      if (!err) {
        this.props.onSubmit && this.props.onSubmit(values);
      }
    });
  }
  handleCancel = () => {
      this.props.onCancel && this.props.onCancel();
  }
  render(){
     const { getFieldDecorator } = this.props.form;
     const data = this.props.data || {};
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
     return (
      <Modal
        title="添加变量"
        onOk={this.handleSubmit}
        onCancel = {this.handleCancel}
        visible={true}
      >
        <Form onSubmit={this.handleSubmit}>
          <FormItem
          {...formItemLayout}
          label="变量名"
          >
            {getFieldDecorator('attr_name', {
              initialValue: data.attr_name || '',
              rules: [{ required: true, message: '请输入变量名称' , }, {
                pattern: /^[A-Z][A-Z0-9_]*$/,
                message: '格式不正确， /^[A-Z][A-Z0-9_]*$/'
              }],
            })(
              <Input disabled={!!data.attr_name}  placeholder="请输入变量名称 格式/^[A-Z][A-Z0-9_]*$/" />
            )}
          </FormItem>
          <FormItem
          {...formItemLayout}
          label="变量值"
          >
            {getFieldDecorator('attr_value', {
              initialValue: data.attr_value || '',
              rules: [{ required: true, message: '请输入变量值' }],
            })(
              <Input  placeholder="请输入变量值" />
            )}
          </FormItem>
          <FormItem
          {...formItemLayout}
          label="说明"
          >
            {getFieldDecorator('name', {
              initialValue: data.name || '',
              rules: [{ required: true, message: '请输入变量说明' }],
            })(
              <Input  placeholder="请输入变量说明" />
            )}
          </FormItem>
        </Form>
      </Modal>
     )
  }
}



@connect(({ user, appControl }) => ({
  currUser: user.currentUser,
  outerEnvs: appControl.outerEnvs,
}),null, null, {withRef:true})
export default class Index extends PureComponent {
  constructor(arg){
    super(arg);
    this.state = {
      showAddVar: null,
      showEditVar: null,
      showAddRelation: false,
      linkList:[],
      relationList: [],
      viewRelationInfo: null
    }
  }

  componentDidMount() {
    const { dispatch } = this.props;
    this.loadRelationedApp();
    this.fetchOuterEnvs();

  }
  loadRelationedApp = () => {
    getRelationedApp({
         team_name: globalUtil.getCurrTeamName(),
         app_alias: this.props.appAlias
      }).then((data) => {
          if(data){
              this.setState({relationList: data.list || []})
          }
      })
  }
  handleAddVar = () => {
      this.setState({showAddVar: {new: true}})
  }
  handleCancelAddVar = () => {
     this.setState({showAddVar: null})
  }
  showAddRelation = () => {
    this.setState({showAddRelation: true})
  }
  handleCancelAddRelation = () => {
    this.setState({showAddRelation: false})
  }
  handleSubmitAddRelation = (ids) => {
     
    batchAddRelationedApp({
        team_name: globalUtil.getCurrTeamName(),
         app_alias: this.props.appAlias,
         dep_service_ids: ids
       }).then((data)=>{
          if(data){
             this.loadRelationedApp();
             this.handleCancelAddRelation();
          }
       })
  }
  handleSubmitAddVar = (vals) => {
      this.props.dispatch({
        type:'appControl/addOuterEnvs',
        payload: {
           team_name: globalUtil.getCurrTeamName(),
           app_alias: this.props.appAlias,
           attr_name: vals.attr_name,
           attr_value: vals.attr_value,
           name: vals.name
        },
        callback: () => {
            this.handleCancelAddVar();
            this.fetchOuterEnvs();
        }
      })
  }
  onDeleteVar = (data) => {
    this.setState({deleteVar: data});
  }

  handleRemoveRelationed = (app) => {
      removeRelationedApp({
        team_name: globalUtil.getCurrTeamName(),
         app_alias: this.props.appAlias,
         dep_service_id: app.service_id
       }).then((data)=>{
          if(data){
             this.loadRelationedApp();
          }
       })
  }
  cancelDeleteVar = () => {
    this.setState({deleteVar: null});
  }
  handleDeleteVar = () => {
     this.props.dispatch({
        type:'appControl/deleteEnvs',
        payload: {
           team_name: globalUtil.getCurrTeamName(),
           app_alias: this.props.appAlias,
           attr_name: this.state.deleteVar.attr_name
        },
        callback: () => {
           this.cancelDeleteVar();
           this.fetchOuterEnvs();
        }
      })
  }
  onEditVar = (data) => {
    this.setState({showEditVar: data});
  }
  cancelEditVar = () => {
    this.setState({showEditVar: null});
  }
  handleEditVar = (vals) => {
     this.props.dispatch({
        type:'appControl/editEvns',
        payload: {
           team_name: globalUtil.getCurrTeamName(),
           app_alias: this.props.appAlias,
           attr_name: vals.attr_name,
           attr_value: vals.attr_value,
           name: vals.name
        },
        callback: () => {
           this.cancelEditVar();
           this.fetchOuterEnvs();
        }
      })
  }
  fetchOuterEnvs = () => {
      this.props.dispatch({
        type:'appControl/fetchOuterEnvs',
        payload: {
           team_name: globalUtil.getCurrTeamName(),
           app_alias: this.props.appAlias,
        }
      })
  }
  onViewRelationInfo = (data) => {
     this.setState({viewRelationInfo: data})
  }
  cancelViewRelationInfo = (data) => {
     this.setState({viewRelationInfo: null})
  }
  render() {
    const {linkList, relationList} = this.state;
    const {outerEnvs} = this.props;
    return (
      <Fragment>
     <Card
      style={{marginBottom: 24}}
      title={
        <span>
          应用连接信息
        </span>
      }

     >
      <ScrollerX sm={650}>
      <Table 
        pagination={false}
        columns={[{
          title:'变量名',
          dataIndex: 'attr_name'
        },{
          title:'变量值',
          dataIndex: 'attr_value'
        },{
          title:'说明',
          dataIndex: 'name'
        },{
          title:'操作',
          dataIndex: 'action',
          render: (val, data) => {
              return (
              <Fragment>
                {data.is_change ? <a href="javascript:;" onClick={()=>{this.onDeleteVar(data)}}>删除</a>: ''}
                {data.is_change ? <a href="javascript:;" onClick={()=>{this.onEditVar(data)}}>修改</a>: ''}
              </Fragment>
             )
          }
        }]}
        dataSource={outerEnvs}
       />
       </ScrollerX>
       <div  style={{marginTop:10, textAlign: 'right'}}>
          <Button onClick={this.handleAddVar}><Icon type="plus" /> 添加变量</Button>
       </div>
     </Card>
     <Card
      title={
        <span>
          依赖应用信息
        </span>
      }

     >
      <ScrollerX sm={650}>
      <Table
       pagination = {false}
       columns={[{
        title:'应用名',
        dataIndex: 'service_cname',
        render:(val, data) => {
            return <Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/app/${data.service_alias}/overview`}>{val}</Link>
        }
      },{
        title:'所属组',
        dataIndex: 'group_name',
        render:(val, data) => {
            return <Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/groups/${data.group_id}`}>{val}</Link>
        }
      },{
        title:'应用说明',
        dataIndex: 'var',
        render:(val, data) => {

        }
      },{
        title:'操作',
        dataIndex: 'var',
        render:(val, data) => {
            return (
               <Fragment>
               <a onClick={()=>this.onViewRelationInfo(data)} href="javascript:;" style={{margintRight: 10}}>连接信息</a>
               <a onClick={()=>{this.handleRemoveRelationed(data)}} href="javascript:;" style={{margintRight: 10}}>取消依赖</a>
               </Fragment>
            )
        }
      }]}
      dataSource={relationList}
       />
       </ScrollerX>
       <div  style={{marginTop:10, textAlign: 'right'}}>
        <Button onClick={this.showAddRelation}><Icon type="plus" /> 添加依赖</Button>
       </div>
     </Card>
     {this.state.showAddVar && <AddVarModal onCancel={this.handleCancelAddVar} onSubmit={this.handleSubmitAddVar} data={this.state.showAddVar} />}
     {this.state.showEditVar && <AddVarModal onCancel={this.cancelEditVar} onSubmit={this.handleEditVar} data={this.state.showEditVar}  />}
     {this.state.deleteVar && <ConfirmModal onOk={this.handleDeleteVar} onCancel={this.cancelDeleteVar} title="删除变量" desc="确定要删除此变量吗？" subDesc="此操作不可恢复" />}
     {this.state.showAddRelation && <AddRelation appAlias={this.props.appAlias} onCancel={this.handleCancelAddRelation} onSubmit={this.handleSubmitAddRelation} />}
     {this.state.viewRelationInfo && <ViewRelationInfo appAlias={this.state.viewRelationInfo.service_alias} onCancel={this.cancelViewRelationInfo} />}
     </Fragment>
    );
  }
}
