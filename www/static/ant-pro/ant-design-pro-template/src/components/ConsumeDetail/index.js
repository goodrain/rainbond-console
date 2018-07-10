/*
  添加依赖应用
*/
import React, { PureComponent, Fragment } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import { Link, Switch, Route } from 'dva/router';
import { Row, Col, Card, Form, Button, Icon, Menu, Input,  Dropdown, Table, Modal, DatePicker} from 'antd';
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
    const columns = [{
        title: '时间',
        dataIndex: 'time',
        key: 'time',
      },{
        title: '内存费用',
        dataIndex: 'memory_fee',
        key: 'memory_fee',
        render: (v,data) => {
          return ( 
                  data.memory_limit  === '0'?
                  <Tooltip placement="topLeft" title={'已使用内存' +  data.memory_usage + 'GB，已超出内存' + data.memory_over + '(GB)'}>
                    {v + '元'}
                  </Tooltip>
                  :
                  <Tooltip placement="topLeft" title={'包月内存'+ data.memory_limit  +'(GB)，已使用内存' + data.memory_usage +'GB，已超出内存' + data.memory_over + '(GB)'}>
                  {v + '元'}
                  </Tooltip>
              )
        }
      }, {
        title: '磁盘费用',
        dataIndex: 'disk_fee',
        key: 'disk_fee',
        render: (v,data) => {
          return ( 
              data.disk_limit  === '0'?
              <Tooltip placement="topLeft" title={'已使用磁盘' + data.disk_usage +'GB，已超出磁盘' + data.disk_over + '(GB)'}>
              { v + '元'}
              </Tooltip>
              :
              <Tooltip placement="topLeft" title={'包月磁盘'+ data.disk_limit +'(GB)，已使用磁盘' + data.disk_usage +'GB，已超出磁盘' + data.disk_over + '(GB)'}>
              {v + '元'}
              </Tooltip>
          )
        }
      }, {
        title: '流量费用',
        dataIndex: 'net_fee',
        key: 'net_fee',
        render: (v,data) => {
          return ( 
              <Tooltip placement="topLeft" title={'已使用流量' + data.net_usage +'(GB)'}>
                { v + '元'}
              </Tooltip>
            )
        }
      }, {
        title: '总费用',
        dataIndex: 'total_fee',
        key: 'total_fee',
        render: (v,data) => {
          return v + '元'
        }
      }];
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
        <p style={{textAlign: 'right'}}>
            <DatePicker onChange={this.handleDateChange} allowClear={false} defaultValue={moment(this.state.date, "YYYY-MM-DD")} />
        </p>
        <Table
          pagination = {false}
          dataSource={this.state.list || []}
          columns={columns}
         />
         </Modal>
      )
   }
}