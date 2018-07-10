/*
  添加依赖应用
*/
import React, { PureComponent, Fragment } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import { Link, Switch, Route } from 'dva/router';
import { Row, Col, Card, Form, Button, Icon, Menu, Input,  Dropdown, Table, Modal, notification, Select} from 'antd';
import { getRelationedApp , getUnRelationedApp, addRelationedApp, removeRelationedApp } from '../../services/app';
import globalUtil from '../../utils/global';

@connect()
export default class Index extends PureComponent {
   constructor(props){
     super(props);
     this.state = {
       list:[],
       page:1,
       page_size: 10,
       total: 0,
       start:'',
       end:''
     }
   }
   componentDidMount(){
     this.loadPayHistory();
   }
   loadPayHistory = () => {
       this.props.dispatch({
           type:'global/getPayHistory',
           payload:{
               team_name: globalUtil.getCurrTeamName(),
               page: this.state.page,
               page_size: this.state.page_size,
               end: this.state.end,
               start: this.state.start
           },
           callback: (data) => {
               this.setState({total: data.total, list: data.list})
           }
       })
   }
   handleCancel = () => {
     this.props.onCancel && this.props.onCancel();
   }
   handleDateChange = (value) => {
       if(value === 'all'){
           this.state.start = this.state.end = '';
       }else{
           this.state.end = moment().subtract(value, 'days').format('YYY-MM-DD');
           this.state.start = moment().format('YYYY-MM-DD');
           this.setState({start})
       }
       this.loadPayHistory();
   }
   render(){

      return (
        <Modal
        title="充值记录"
        width={1000}
        visible={true}
        onCancel = {this.handleCancel}
        footer={[
            <Button onClick={this.handleCancel}>关闭</Button>
        ]}
        >
        <p>
            <Select onChange={this.handleDateChange}>
                <Select.Option value="all">全部</Select.Option>
                <Select.Option value={7}>7天内</Select.Option>
                <Select.Option value={30}>1个月内</Select.Option>
                <Select.Option value={30*7}>7个月内</Select.Option>
            </Select>
        </p>
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