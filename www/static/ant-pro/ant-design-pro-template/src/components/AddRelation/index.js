/*
  添加依赖应用
*/
import React, { PureComponent, Fragment } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import { Link, Switch, Route } from 'dva/router';
import { Row, Col, Card, Form, Button, Icon, Menu, Input,  Dropdown, Table, Modal, notification} from 'antd';
import { getRelationedApp , getUnRelationedApp, addRelationedApp, removeRelationedApp } from '../../services/app';
import globalUtil from '../../utils/global';

export default class AddRelation extends PureComponent {
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