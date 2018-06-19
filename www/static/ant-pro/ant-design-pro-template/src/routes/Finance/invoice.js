import React, { PureComponent } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import { Table, Card, Row, Col, Radio, Input, Button, Icon, DatePicker, Tooltip, Menu, Dropdown} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import styles from '../List/BasicList.less';
import globalUtil from '../../utils/global';
import InvoiceForm from '../../components/InvoiceForm';

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
      this.state = {
         selectedRowKeys: []
          
      }
  }
  componentDidMount() {
     
  }
  onSelectChange = (selectedRowKeys) => {
    console.log('selectedRowKeys changed: ', selectedRowKeys);
    this.setState({ selectedRowKeys });
  }
  render() {
    const { loading } = this.props;
    const { selectedRowKeys } = this.state;
    const extraContent = (
      <div className={styles.extraContent}>
        <DatePicker onChange={this.handleDateChange} allowClear={false} defaultValue={moment(this.state.date, "YYYY-MM-DD")} />
      </div>
    );
    const columns = [{
      title: '订单号',
      dataIndex: 'order',
    }, {
      title: '储值金额',
      dataIndex: 'money',
    }, {
      title: '储值方式',
      dataIndex: 'type',
    },
    {
      title: '订单时间',
      dataIndex: 'time',
    }];
    const data = [];
    for (let i = 0; i < 20; i++) {
      data.push({
        key: i,
        order: `${i}`,
        money: '10000',
        type: `alipay`,
        time:i
      });
    }
    const pageHeaderContent = (
        <Button style={{float:'right'}}><a target="_blank" href="https://www.goodrain.com/spa/#/personalCenter/my/recharge">发票查询</a></Button>
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
          href: ``
        }, {
          title: "发票申请",
          href: ``
        }]}
        title={"发票申请"}
        content={pageHeaderContent}
      >
        <div className={styles.standardList}>

          <Card
            className={styles.listCard}
            bordered={false}
            title="选择开票订单"
            style={{ marginTop: 24 }}
            bodyStyle={{ padding: '0 32px 40px 32px' }}
            extra={extraContent}
          >
            <Table rowSelection={rowSelection} dataSource={data} columns={columns} />
            <div style={{textAlign:'center'}}><Button type="primary">申请开票</Button></div>
          </Card>
          <InvoiceForm/>
        </div>
      </PageHeaderLayout>
    );
  }
}
