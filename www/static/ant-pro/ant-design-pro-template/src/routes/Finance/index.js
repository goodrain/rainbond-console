import React, { PureComponent } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import { Table, Card, Row, Col, Radio, Input, Button, Icon, DatePicker, Tooltip } from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import styles from '../List/BasicList.less';
import globalUtil from '../../utils/global';

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
          date: moment(new Date(), "YYYY-MM-DD"),
          companyInfo: {},
          regionDiskStock: 0,
          regionMemoryStock: 0,
          list:[]
      }
  }
  componentDidMount() {
      this.getCompanyInfo();
      this.getRegionResource();
      this.getRegionOneDayMoney();
  }
  getRegionResource(){
    this.props.dispatch({
      type: 'global/getRegionSource',
      payload:{
         team_name: globalUtil.getCurrTeamName(),
         enterprise_id: this.props.user.enterprise_id,
         region: globalUtil.getCurrRegionName()
      },
      callback: (data) => {
         this.setState({regionDiskStock: data.bean.disk.stock, regionMemoryStock: data.bean.memory.stock})
      }
    })
  }
  getCompanyInfo = () => {
     this.props.dispatch({
       type: 'global/getCompanyInfo',
       payload:{
          team_name: globalUtil.getCurrTeamName(),
          enterprise_id: this.props.user.enterprise_id
       },
       callback: (data) => {
          this.setState({companyInfo: data.bean})
       }
     })
  }
  getRegionOneDayMoney = () => {
    this.props.dispatch({
      type: 'global/getRegionOneDayMoney',
      payload:{
         team_name: globalUtil.getCurrTeamName(),
         enterprise_id: this.props.user.enterprise_id,
         date: this.state.date,
         region: globalUtil.getCurrRegionName()
      },
      callback: (data) => {
         this.setState({list: data.list || []})
      }
    })
  }
  handleDateChange = (date, str) => {
    this.setState({date: str}, () => {
       this.getRegionOneDayMoney();
    })
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
        dataIndex: 'time',
        key: 'time',
      },{
        title: '内存费用',
        dataIndex: 'memory_fee',
        key: 'memory_fee',
        render: (v,data) => {
           return v + '元'
        }
      }, {
        title: '磁盘费用',
        dataIndex: 'disk_fee',
        key: 'disk_fee',
        render: (v,data) => {
           return v + '元'
        }
      }, {
        title: '流量费用',
        dataIndex: 'net_fee',
        key: 'net_fee',
        render: (v,data) => {
           return v + '元'
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
      <PageHeaderLayout>
        <div className={styles.standardList}>
          <Card bordered={false}>
            <Row>
              <Col sm={8} xs={24}>
                    <Info title="企业账户余额" value={`${this.state.companyInfo.balance || 0} 元`} bordered />
              </Col>
              <Col sm={8} xs={24}>
                    <Info title="当前数据中心剩余内存" value={`${this.state.regionDiskStock} G`} bordered />
              </Col>
              <Col sm={8} xs={24}>
                    <Info title="当前数据中心剩余磁盘" value={`${this.state.regionMemoryStock} G`} />
              </Col>
            </Row>
          </Card>

          <Card style={{textAlign: 'right'}}>
             <Button type="primary" style={{marginRight: 8}}><a target="_blank" href="https://www.goodrain.com/#/personalCenter/my/recharge">账户充值</a></Button>
             <Button><a target="_blank" href="javascript:;">扩展数据中心资源</a></Button>
          </Card>

          <Card
            className={styles.listCard}
            bordered={false}
            title="当前数据中心每小时资源费用"
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
