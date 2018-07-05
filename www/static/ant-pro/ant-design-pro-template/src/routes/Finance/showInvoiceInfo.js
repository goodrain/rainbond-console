/*
  添加或者修改插件配置
*/
import React, { PureComponent, Fragment } from 'react';
import { connect } from 'dva';
import { Link, Switch, Route } from 'dva/router';
import {Modal, Button, Table} from 'antd';
import globalUtil from '../../utils/global';

@connect()
export default class Index extends PureComponent {
   constructor(props){
       super(props);
       this.state = {
           data: [],
           bean: {}
       }
   }
   componentDidMount(){
      this.load();
   }
   load = () => {
       const id = this.props.id;
       this.props.dispatch({
           type: 'invoice/getInvoiceInfo',
           payload: {
               team_name: globalUtil.getCurrTeamName(),
               receipt_id: id
           },
           callback: (data) => {
             this.setState({bean: data.bean || {}})
           }
       })
   }
   handleCancel = () => {
     this.props.onCancel && this.props.onCancel();
   }
   render(){
      const data = this.state.bean;
      return (
        <Modal
        title= {'发票详情'}
        visible={true}
        width={1000}
        onCancel = {this.handleCancel}
        footer={[<Button onClick={this.handleCancel}>关闭</Button>]}
        >
            <Table columns={[
                {
                    title: '申请人',
                    dataIndex: 'order_no',
                    render: () => {
                        return data.user_name
                    }
                },
                {
                    title: '企业',
                    dataIndex: 'receipt_subject',
                    render: () => {
                        return data.receipt_subject
                    }
                },
                {
                    title: '订单号',
                    dataIndex: 'order_no'
                },
                {
                    title: '订单金额',
                    dataIndex: 'order_price',
                    render: (v) => {
                        return v + '元'
                    }
                },
                {
                    title: '付款方式',
                    dataIndex: 'pay_type'
                },
                {
                    title: '第三方流水号',
                    dataIndex: 'pay_trade_no'
                },
                {
                    title: '订单时间',
                    dataIndex: 'pay_time'
                }
            ]}
            pagination={false}
             dataSource={data.orders}
             />
        </Modal>
      )
   }
}