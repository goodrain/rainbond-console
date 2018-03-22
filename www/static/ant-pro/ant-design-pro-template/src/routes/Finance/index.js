import React, { PureComponent } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import { Table, Card, Row, Col, Radio, Input, Button, Icon, DatePicker, Tooltip } from 'antd';

import PageHeaderLayout from '../../layouts/PageHeaderLayout';

import styles from '../List/BasicList.less';

const RadioButton = Radio.Button;
const RadioGroup = Radio.Group;
const { Search } = Input;

@connect(({ list, loading }) => ({
  list,
  loading: loading.models.list,
}))
export default class BasicList extends PureComponent {
  constructor(props){
      super(props);
      this.state = {
          date: moment(new Date(), "YYYY-MM-DD")
      }
  }
  componentDidMount() {
  }
  handleDateChange(date, str){
    console.log(str)
  }
  render() {
    const { loading } = this.props;
    const list = this.state.list || [];
    const Info = ({ title, value, bordered }) => (
      <div className={styles.headerInfo}>
        <span>{title}</span>
        <p>{value}</p>
        {bordered && <em />}
      </div>
    );

    const extraContent = (
      <div className={styles.extraContent}>
        <DatePicker onChange={this.handleDateChange} allowClear={false} defaultValue={moment(this.state.date, "YYYY-MM-DD")} />
      </div>
    );

    const columns = [{
        title: '时间',
        dataIndex: 'name',
        key: 'name',
      },{
        title: '内存费用',
        dataIndex: 'name',
        key: 'name',
      }, {
        title: '磁盘费用',
        dataIndex: 'age',
        key: 'age',
      }, {
        title: '流量费用',
        dataIndex: 'address',
        key: 'address',
      }, {
        title: '总费用',
        dataIndex: 'address',
        key: 'address',
      }, {
        title: '状态',
        dataIndex: 'address',
        key: 'address',
      }];


    return (
      <PageHeaderLayout>
        <div className={styles.standardList}>
          <Card bordered={false}>
            <Row>
              <Tooltip title="点击去充值">
              <Col sm={8} xs={24}>
                    <Info title="企业账户余额" value={"666 元"} bordered />
              </Col>
              </Tooltip>
              <Tooltip title="点击去扩容">
              <Col sm={8} xs={24}>
                    <Info title="当前数据中心剩余内存" value={"666G"} bordered />
              </Col>
              </Tooltip>
              <Tooltip title="点击去扩容">
              <Col sm={8} xs={24}>
                    <Info title="当前数据中心剩余磁盘" value={"888G"} />
              </Col>
              </Tooltip>
            </Row>
          </Card>

          <Card
            className={styles.listCard}
            bordered={false}
            title="每小时资源费用"
            style={{ marginTop: 24 }}
            bodyStyle={{ padding: '0 32px 40px 32px' }}
            extra={extraContent}
          >
            <Table dataSource={list} columns={columns} />
            
          </Card>
        </div>
      </PageHeaderLayout>
    );
  }
}
