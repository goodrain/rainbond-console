import React, { PureComponent, Fragment } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import {Link} from 'dva/router';
import { Table, Card, Row, Col, Radio, Input, Button, Icon, Tooltip, Menu, Dropdown, Select} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import styles from '../List/BasicList.less';
import globalUtil from '../../utils/global';
import invoiceUtil from './invoice-util';
import ShowInvoiceInfo from './showInvoiceInfo';

@connect(({user, loading }) => ({
  user: user.currentUser,
  loading: loading.models.list,
}))
export default class Index extends PureComponent {
  constructor(props){
      super(props);
      this.state = {
         selectedRowKeys: [],
         showForm:false,
         data:[],
         page: 1,
         pageSize: 10,
         receipt_status: '',
         invoiceId: ''
      }
  }
  componentDidMount() {
     this.getInovices();
  }
  getInovices(){
    this.props.dispatch({
        type: 'invoice/getInovices',
        payload:{
            team_name: globalUtil.getCurrTeamName(),
            receipt_status: this.state.receipt_status,
            page: this.state.page,
            limit: this.state.pageSize
        },
        callback: (data) => {
            this.setState({data: data.list || []})
        }
    })
  }
  onViewInvoiceInfo = (data) => {
    this.setState({invoiceId: data.receipt_id})
  }
  onCancelViewInvoice = () => {
    this.setState({invoiceId: ''})
  }
  reGetInovices(){
      this.state.page = 1;
      this.getInovices();
  }
  onSelectChange = (selectedRowKeys) => {
    this.setState({ selectedRowKeys });
  }
  handleinvoice =()=>{
     this.setState({showForm:true})
  }
  handleOkInvoice =()=>{

  }
  handleCancelInvoice =()=>{
    this.setState({showForm:false})
  }
  onStatusChange = (value) => {
      this.state.receipt_status = value;
      this.reGetInovices()
  }

  render() {
    const { loading } = this.props;
    const { selectedRowKeys } = this.state;
    const data = this.state.data || [];
    const extraContent = (
      <div className={styles.extraContent}>
        <Select defaultValue={this.state.receipt_status} onChange={this.onStatusChange}>
            <Select.Option value="">全部</Select.Option>
            <Select.Option value="Not">未处理</Select.Option>
            <Select.Option value="Post">已邮寄</Select.Option>
            <Select.Option value="Cancel">已取消</Select.Option>
        </Select>
      </div>
    );
    const columns = [{
      title: '申请时间',
      dataIndex: 'create_time',
    }, {
      title: '发票类型',
      dataIndex: 'receipt_type',
      render: (v) => {
        return invoiceUtil.getTypeCN(v)
      }
    }, {
      title: '抬头',
      dataIndex: 'receipt_subject',
    },
    {
      title: '发票金额',
      dataIndex: 'receipt_money',
      render: (v) => {
          return v + '元'
      }
    },{
        title: '发票内容',
        dataIndex: 'receipt_content',
      },{
        title: '状态',
        dataIndex: 'receipt_status',
        render: (v) => {
            return invoiceUtil.getStatusCN(v)
        }
      },{
        title: '快递单号',
        dataIndex: 'post_tracking_no',
      },{
        title: '操作',
        dataIndex: '',
        render: (v, data) => {
            return <Fragment>
                <a href="javascript:;" onClick={()=>{this.onViewInvoiceInfo(data)}} style={{marginRight: 8}}>查看订单</a>
                {false && <a href="javascript:;" onClick={this.handleCancel}>取消申请</a>}
            </Fragment>
        }
      }];
    const pageHeaderContent = (
        <Button style={{float:'right'}}><Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/applyinvoice`}>申请发票</Link></Button>
    );
    return (
      <PageHeaderLayout
        breadcrumbList={[{
          title: "首页",
          href: `/`
        }, {
          title: "财务中心",
          href: ``
        }, {
          title: "发票管理",
          href: ``
        }]}
        content={pageHeaderContent}
      >
        <div className={styles.standardList}>

          <Card
            className={styles.listCard}
            bordered={false}
            title="发票申请记录"
            style={{ marginTop: 24 }}
            bodyStyle={{ padding: '0 32px 40px 32px' }}
            extra={extraContent}
          >
            <Table dataSource={data} columns={columns} />
          </Card>
          {this.state.invoiceId && <ShowInvoiceInfo 
             id={this.state.invoiceId}
             onCancel={this.onCancelViewInvoice}
          />}
        </div>
      </PageHeaderLayout>
    );
  }
}
