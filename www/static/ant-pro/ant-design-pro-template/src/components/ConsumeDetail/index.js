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

      return (
        <Modal
        title="花费明细"
        width={1000}
        visible={true}
        onCancel = {this.handleCancel}
        footer=[{
            <Button onClick={this.handleCancel}>关闭</Button>
        }]
        >
        <Table
          pagination = {false}
          dataSource={this.state.apps || []}
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