import React, { PureComponent } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import {Link} from 'dva/router';
import { Table, Card, Row, Col, Radio, Input, Button, Icon, DatePicker, Tooltip, Menu, Dropdown} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import styles from '../List/BasicList.less';
import globalUtil from '../../utils/global';
import InvoiceEcharts from '../../components/InvoiceEcharts';

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
          disk:{},
          memory:{},
          list:[],
          datalist:[]
      }
  }
  componentDidMount() {
      this.getCompanyInfo();
      this.getRegionResource();
      // this.getRegionOneDayMoney();
  }
  // 获取某个数据中心的资源详情  // 新-- 数据中心列表
  getRegionResource(){
    this.props.dispatch({
      type: 'global/getRegionSource',
      payload:{
         team_name: globalUtil.getCurrTeamName(),
         enterprise_id: this.props.user.enterprise_id,
        //  region: globalUtil.getCurrRegionName()
        region:''
      },
      callback: (data) => {this.setState({datalist:data.list})
      }
    })
  }
  // 获取企业信息 //新-- 企业信息
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
  // 获取某数据中心下某一天的资源费用数据 
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
    const datalist = this.state.datalist;
    const companyInfo = this.state.companyInfo || {}

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
    
    return (
      <PageHeaderLayout>
        <div className={styles.standardList}>
          <Card bordered={false}>
            <Row>
              <Col sm={8} xs={24}>
                    <Info title="企业账户"  value={`${companyInfo.balance || 0}元`} bordered />
                    <p style={{textAlign:'center'}}>
                      <a href='' style={{paddingRight:'10px'}}>储值</a>
                      <Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/invoiceManage`}>发票管理</Link>
                    </p>
              </Col>
              <Col sm={8} xs={24}>
                    <Info title="上一小时按需消费" value={`${companyInfo.last_hour_cost || 0}元`} bordered />
                    <p style={{textAlign:'center'}}>
                      <span style={{paddingRight:'5px'}}>{companyInfo.last_hour_used_mem || 0}M内存</span>／
                      <span  style={{paddingLeft:'5px'}}>{companyInfo.last_hour_used_disk || 0}G磁盘</span>
                    </p>
              </Col>
              <Col sm={8} xs={24}>
                    <Info title="xx月资源" value={`${companyInfo.cost || 0}元/${companyInfo.recharge || 0} 元`} />
                    <p style={{textAlign:'center'}}>
                      <a href=''style={{paddingRight:'10px'}}>消费明细</a>
                      <a href=''>储值明细</a>
                    </p>
              </Col>
            </Row>
          </Card>

          <Card
            className={styles.listCard}
            bordered={false}
            title="数据中心资源展示"
            style={{ marginTop: 24 }}
            bodyStyle={{ padding: '0 32px 40px 32px' }}
          >
            <InvoiceEcharts  enterprise_id={this.props.user.enterprise_id} /> 
          </Card>
        </div>
      </PageHeaderLayout>
    );
  }
}
