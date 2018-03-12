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

export default class Index extends PureComponent {
   constructor(props){
     super(props);
     this.state = {
       selectedRowKeys:[],
       apps:[]
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

      this.props.onSubmit && this.props.onSubmit(this.state.selectedRowKeys);

   }
   getUnRelationedApp = () => {
       getUnRelationedApp({
         team_name: globalUtil.getCurrTeamName(),
         app_alias: this.props.appAlias
      }).then((data) => {
          if(data){
              this.setState({apps: data.list || []})
          }
      })
   }
   handleCancel = () => {
     this.props.onCancel && this.props.onCancel();
   }
   render(){
      const rowSelection = {
        onChange: (selectedRowKeys, selectedRows) => {
           this.setState({selectedRowKeys: selectedRows.map((item)=>{return item.service_id})})
        },
        getCheckboxProps: record => ({
          disabled: record.name === 'Disabled User', // Column configuration not to be checked
        }),
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
          pagination = {false}
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