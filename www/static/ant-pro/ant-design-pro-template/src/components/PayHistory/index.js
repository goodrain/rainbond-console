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

var statusMap = {
	'Not': {
		text : '待付款',
		colorClass: ''
	},
	'Send': {
		text : '付款中',
		colorClass: ''
	},
	'Succeed': {
		text: '付款成功',
		colorClass: 'text-success'
	},
	'Failed': {
		text: '付款失败',
		colorClass: 'text-danger'
	},
	'Cancelled': {
		text: '已取消',
		colorClass: ''
	},
	'Closed': {
		text: '已关闭',
		colorClass: 'text-warning'
	},
	'Expired': {
		text: '已过期'
	},
	unknow: {
		text: '未知'
	}
}

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
           this.state.end = moment().format('YYYY-MM-DD');
           this.state.start = moment().subtract(value, 'days').format('YYYY-MM-DD');
       }
       this.state.page = 1;
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
        <p style={{textAlign: 'right'}}>
            <Select defaultValue="all" style={{width: 100}} onChange={this.handleDateChange}>
                <Select.Option value="all">全部</Select.Option>
                <Select.Option value={7}>7天内</Select.Option>
                <Select.Option value={30}>1个月内</Select.Option>
                <Select.Option value={30*7}>7个月内</Select.Option>
            </Select>
        </p>
        <Table
          pagination = {false}
          dataSource={this.state.list || []}
          columns={[{
            title: '订单号',
            dataIndex: 'order_no'
          },{
            title: '订单内容',
            dataIndex: 'content',
            render: (v, order) => {
                return <div>
                    {
                        order.app_alias ?
                            <div>应用:{order.app_alias}</div>
                            :''
                    }
                    {
                        (order.region_alias && order.order_type == 'res')?
                        <div>
                            <span>数据中心:{order.region_alias}</span>
                            <span>内存:{sourceUtil.getMemoryAndUnit(order.res_memory)}</span>
                            <span>磁盘:{sourceUtil.getDiskAndUnit(order.res_disk)}</span>
                            <span>时长:{order.res_spent_time}天</span>
                            <span>网络:{sourceUtil.getNetAndUnit(order.res_net)}</span>
                        </div>
                        :''
                    }
                    {
                        (order.order_type == 'recharge')?
                        <div>
                            账户充值
                        </div>
                        :''
                    }
                </div>
            }
          },{
            title: '订单金额',
            dataIndex: 'order_price',
            render: (v ,data) => {
                return (v || 0) + '元' 
            }
          } ,{
            title: '订单状态',
            dataIndex: 'order_status',
            render: (v ,data) => {
                try{
                    return statusMap[v].text || '未知';
                }catch(e){
                    
                }
                return ''
                
            }
          } ,{
            title: '时间',
            dataIndex: 'create_time'
          }]}
         />
         </Modal>
      )
   }
}