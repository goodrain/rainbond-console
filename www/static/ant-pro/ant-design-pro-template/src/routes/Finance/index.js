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
          date: moment(new Date().getTime()).format('YYYY-MM-DD'),
          companyInfo: {},
          regionDiskUsed: 0,
          regionMemoryUsed: 0,
          regionMemroyLimit: 0,
          regionDiskLimit : 0,
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
         this.setState({regionMemroyLimit:data.bean.memory.limit, regionDiskLimit:data.bean.disk.limit, regionDiskUsed: data.bean.disk.used || 0, regionMemoryUsed: data.bean.memory.used || 0})
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
    const list = [];
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

    var money = `${this.state.companyInfo.balance || 0} 元`;
    if(this.state.companyInfo.owed_amt > 0){
       money = `欠费 ${this.state.companyInfo.owed_amt} 元`;
    }
    
    return (
      <PageHeaderLayout>
        <div className={styles.standardList}>
          <Card bordered={false}>
            <Row>
              <Col sm={8} xs={24}>
                    <Info title="企业账户余额" value={money} bordered />
              </Col>
              <Col sm={8} xs={24}>
                    <Info title="当前数据中心剩余内存" value={`${this.state.regionDiskUsed}/${this.state.regionDiskLimit} G`} bordered />
              </Col>
              <Col sm={8} xs={24}>
                    <Info title="当前数据中心剩余磁盘" value={`${this.state.regionMemoryUsed}/${this.state.regionMemoryLimit} G`} />
              </Col>
            </Row>
          </Card>

          <div style={{textAlign: 'right', paddingTop: 24}}>
             <Button style={{marginRight: 8}} type="primary"><a target="_blank" href="javascript:;">购买资源</a></Button>
             <Button><a target="_blank" href="https://www.goodrain.com/#/personalCenter/my/recharge">账户充值</a></Button>
             
          </div>

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
