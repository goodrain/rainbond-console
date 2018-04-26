import React, { PureComponent } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import { Table, Card, Row, Col, Radio, Input, Button, Icon, DatePicker, Tooltip, Menu, Dropdown} from 'antd';
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
          disk:{},
          memory:{},
          list:[],
          
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
         this.setState({memory:data.bean.memory || {}, disk: data.bean.disk})
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
          console.log(data)
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
    console.log(list)
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
           return ( 
                  data.memory_limit  === '0'?
                  <Tooltip placement="topLeft" title={'已使用内存' +  data.memory_usage + 'GB，已超出内存' + data.memory_over + '(GB)'}>
                    {v + '元'}
                  </Tooltip>
                  :
                  <Tooltip placement="topLeft" title={'包月内存'+ data.memory_limit  +'(GB)，已使用内存' + data.memory_usage +'GB，已超出内存' + data.memory_over + '(GB)'}>
                   {v + '元'}
                  </Tooltip>
              )
        }
      }, {
        title: '磁盘费用',
        dataIndex: 'disk_fee',
        key: 'disk_fee',
        render: (v,data) => {
           return ( 
              data.disk_limit  === '0'?
              <Tooltip placement="topLeft" title={'已使用磁盘' + data.disk_usage +'GB，已超出磁盘' + data.disk_over + '(GB)'}>
               { v + '元'}
              </Tooltip>
              :
              <Tooltip placement="topLeft" title={'包月磁盘'+ data.disk_limit +'(GB)，已使用磁盘' + data.disk_usage +'GB，已超出磁盘' + data.disk_over + '(GB)'}>
               {v + '元'}
              </Tooltip>
          )
        }
      }, {
        title: '流量费用',
        dataIndex: 'net_fee',
        key: 'net_fee',
        render: (v,data) => {
          return ( 
              <Tooltip placement="topLeft" title={'已使用流量' + data.net_usage +'(GB)'}>
                { v + '元'}
              </Tooltip>
             )
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
    var entId = this.state.companyInfo.ent_id;
    console.log(this.state.companyInfo)
    if(this.state.companyInfo.owed_amt > 0){
       money = `欠费 ${this.state.companyInfo.owed_amt} 元`;
    }
    var regionName = globalUtil.getCurrRegionName();
    let regionId = '';
    if(regionName == 'ali-hz') {
       regionId = 2;
    }

    if(regionName == 'ali-sh'){
       regionId = 1;
    }
    
    return (
      <PageHeaderLayout>
        <div className={styles.standardList}>
          <Card bordered={false}>
            <Row>
              <Col sm={8} xs={24}>
                    <Info title="企业账户余额" value={money} bordered />
              </Col>
              <Tooltip title={`过期时间：${this.state.memory.expire_date || '-'}`}>
              <Col sm={8} xs={24}>
                    <Info title="数据中心内存 (已使用/总资源)" value={`${this.state.memory.used || 0}/${this.state.memory.limit || 0} M`} bordered />
              </Col>
              </Tooltip>
              <Tooltip title={`过期时间：${this.state.disk.expire_date || '-'}`}>
              <Col sm={8} xs={24}>
                    <Info title="数据中心磁盘 (已使用/总资源)" value={`${this.state.disk.used || 0}/${this.state.disk.limit || 0} G`} />
              </Col>
              </Tooltip>
            </Row>
          </Card>

          <div style={{textAlign: 'right', paddingTop: 24}}>

            <Button.Group>
            {(regionId && !entId) && <Button type="primary"><a target="_blank" href={`https://www.goodrain.com/spa/#/resBuy/${regionId}`}>购买资源</a></Button>}
            {(entId && regionId)&& <Button type="primary"><a target="_blank" href={`https://www.goodrain.com/spa/#/resBuy/${regionId}/${entId}`}>购买资源</a></Button>}
            <Button><a target="_blank" href="https://www.goodrain.com/spa/#/personalCenter/my/recharge">账户充值</a></Button>
            <Dropdown overlay={<Menu>
                      <Menu.Item>
                        <a target="_blank" href="https://www.goodrain.com/spa/#/personalCenter/my/mydc-history">查看消费记录</a>
                      </Menu.Item>
          </Menu>}><Button>更多...</Button></Dropdown>
            </Button.Group>
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
