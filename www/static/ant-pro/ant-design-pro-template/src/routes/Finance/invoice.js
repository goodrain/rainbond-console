import React, { PureComponent } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import { Table, Card, Row, Col, Radio, Input, Button, Icon, DatePicker, Tooltip, Menu, Dropdown, notification} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import styles from '../List/BasicList.less';
import globalUtil from '../../utils/global';
import InvoiceForm from '../../components/InvoiceForm';

const {RangePicker} = DatePicker;

const RadioButton = Radio.Button;
const RadioGroup = Radio.Group;
const { Search } = Input;

@connect(({user, list, loading }) => ({
  user: user.currentUser,
  list,
  loading: loading.models.list,
}))
export default class BasicList extends PureComponent {
  constructor(props){
      super(props);
      const now = Date.now();
      this.state = {
         selectedRowKeys: [],
         showForm:false,
         startDate: moment(now - (1000 * 60 * 60 * 24 * 30)).format('YYYY-MM-DD'),
         endDate: moment(now).format('YYYY-MM-DD'),
         data:[],
         invoiceInfo:{},
         
      }
  }
  componentDidMount() {
     this.loadOrders()
  }
  loadOrders(){
    this.props.dispatch({
      type:'invoice/getOrders',
      payload:{
        team_name: globalUtil.getCurrTeamName(),
        start: this.state.startDate,
        end: this.state.endDate,
        selectedRowKeys:[]
      },
      callback: (data) => {
        this.setState({data: data.list || []})
      }
    })
  }
  onSelectChange = (selectedRowKeys) => {
    this.setState({ selectedRowKeys });
  }
  handleinvoice =()=>{
     this.props.dispatch({
       type: 'invoice/confirmApplyInvoice',
       payload: {
         team_name: globalUtil.getCurrTeamName(),
         orders: this.state.selectedRowKeys.join(',')
       },
       callback: (data) => {
          this.setState({invoiceInfo: data.bean || {}, showForm: true})
       }
     })
  }
  
  handleOkInvoice =(value)=>{
    this.props.dispatch({
      type: 'invoice/submitApplyInvoice',
      payload: {
        team_name: globalUtil.getCurrTeamName(),
        orders: this.state.selectedRowKeys.join(','),
        ...value
      },
      callback: (data) => {
         this.handleCancelInvoice();
         this.loadOrders();
         notification.success({
           message: '申请成功， 请在注意查看进度'
         })
      }
    })
  }
  handleCancelInvoice =()=>{
    this.setState({invoiceInfo: {}, showForm: false})
  }
  handleDateChange = (value) => {
    const start = value[0];
    const end = value[1];
    this.state.startDate = start.format('YYYY-MM-DD');
    this.state.startDate = end.format('YYYY-MM-DD');
    this.loadOrders();
  }
  render() {
    const { loading } = this.props;
    const { selectedRowKeys } = this.state;
    const data = this.state.data || [];
    const extraContent = (
      <div className={styles.extraContent}>
        <RangePicker onChange={this.handleDateChange} allowClear={false} defaultValue={[moment(this.state.startDate), moment(this.state.endDate)]} />
      </div>
    );
    const columns = [{
      title: '订单号',
      dataIndex: 'order_no',
    }, {
      title: '储值金额',
      dataIndex: 'order_price',
    }, {
      title: '储值方式',
      dataIndex: 'pay_type',
    },
    {
      title: '订单时间',
      dataIndex: 'pay_time',
    }];
    const pageHeaderContent = (
        null
    );
    const rowSelection = {
      selectedRowKeys,
      onChange: this.onSelectChange,
    };

    return (
      <PageHeaderLayout
        breadcrumbList={[{
          title: "首页",
          href: `/`
        }, {
          title: "财务中心",
          href: `/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/finance`
        }, {
          title: "发票管理",
          href: `/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/invoiceManage`
        }, {
          title: "发票申请",
          href: ``
        }]}
        content={pageHeaderContent}
      >
        <div className={styles.standardList}>

          <Card
            className={styles.listCard}
            bordered={false}
            title={<Button disabled={!this.state.selectedRowKeys.length} type="primary" onClick={() => {this.handleinvoice()}}>申请发票</Button>}
            style={{ marginTop: 24 }}
            bodyStyle={{ padding: '0 32px 40px 32px' }}
            extra={extraContent}
          >
            <Table rowKey={'order_no'} rowSelection={rowSelection} pagination={false} dataSource={data} columns={columns} />
          </Card>
          {this.state.showForm && <InvoiceForm 
             data={this.state.invoiceInfo}
             onOk={this.handleOkInvoice}
             title="发票申请"
             onCancel={this.handleCancelInvoice}
          />}
        </div>
      </PageHeaderLayout>
    );
  }
}
