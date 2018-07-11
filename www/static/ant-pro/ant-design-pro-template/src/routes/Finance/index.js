import React, { PureComponent } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import {Link} from 'dva/router';
import { Table, Card, Row, Col, Radio, Input, Button, Icon, DatePicker, Tooltip, Menu, Dropdown} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import styles from '../List/BasicList.less';
import globalUtil from '../../utils/global';
import InvoiceEcharts from '../../components/InvoiceEcharts';
import PayHistory from '../../components/PayHistory';
import ConsumeDetail from '../../components/ConsumeDetail';

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
          datalist:[],
          showPayHistory: false,
          showConsumeDetail: false
      }
  }
  showConsumeDetail = () => {
    this.setState({showConsumeDetail: true})
  }
  hideConsumeDetail = () => {
    this.setState({showConsumeDetail: false})
  }
  showPayHistory = () => {
    this.setState({showPayHistory: true})
  }
  hidePayHistory = () => {
    this.setState({showPayHistory: false})
  }
  componentDidMount() {
      this.getCompanyInfo();
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
                      <a target="_blank" href='https://www.goodrain.com/spa/#/personalCenter/my/recharge' style={{paddingRight:'10px'}}>充值</a>
                      <Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/invoiceManage`}>发票管理</Link>
                    </p>
              </Col>
              <Col sm={8} xs={24}>
                    <Info title="上一小时按需消费" value={`${companyInfo.last_hour_cost || 0}元`} bordered />
              </Col>
              <Col sm={8} xs={24}>
                    <Info title="本月账单" value={`消耗${companyInfo.cost || 0}元 / 充值${companyInfo.recharge || 0} 元`} />
                    <p style={{textAlign:'center'}}>
                      <a href='javascript:;' onClick={this.showConsumeDetail} style={{paddingRight:'10px'}}>消耗明细</a>
                      <a href='javascript:;' onClick={this.showPayHistory}>充值明细</a>
                    </p>
              </Col>
            </Row>
          </Card>

          <InvoiceEcharts  enterprise_id={this.props.user.enterprise_id} /> 
        </div>
        {this.state.showPayHistory && <PayHistory onCancel={this.hidePayHistory} />}
        {this.state.showConsumeDetail && <ConsumeDetail onCancel={this.hideConsumeDetail} />}
      </PageHeaderLayout>
    );
  }
}
