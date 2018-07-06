import React, { PureComponent } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import { Table, Card, Row, Col, Radio, Input, Button, Icon, DatePicker, Tooltip, Menu, Dropdown,Divider,Slider, InputNumber,Link} from 'antd';
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
        dataCenter:{},
        disk:{},
        memory:{},
        time:'',
        buydisk:0,
        buymemory: 0,
        buytime:0
      }
  }
  componentDidMount() {
     this.getRegionResource();
     this.getResPrice();
     this.buyPurchase();
  }
  
  getRegionResource(){
    const regionName = this.props.match.params.regionName;
    this.props.dispatch({
      type: 'global/getRegionSource',
      payload:{
         team_name: globalUtil.getCurrTeamName(),
         enterprise_id: this.props.user.enterprise_id,
         region: regionName
      },
      callback: (data) => {this.setState({dataCenter:data.bean,disk:data.bean.disk,memory:data.bean.memory})
      }
    })
  }
  
  getResPrice(){
    this.props.dispatch({
      type: 'global/resPrice',
      payload:{
         team_name: globalUtil.getCurrTeamName(),
         region_name:globalUtil.getCurrRegionName(),
         memory: 2,
         disk: 4,
         rent_time: 100
      },
      callback: (data) => {
         console.log(data)
      }
    })
  }

  buyPurchase(){
    this.props.dispatch({
      type: 'global/buyPurchase',
      payload:{
         team_name: globalUtil.getCurrTeamName(),
         region_name:globalUtil.getCurrRegionName(),
         memory: 2,
         disk: 4,
         rent_time: 100
      },
      callback: (data) => {
         console.log(data)
      }
    })
  }

   getResPrice(){
    this.props.dispatch({
      type: 'global/resPrice',
      payload:{
         team_name: globalUtil.getCurrTeamName(),
         enterprise_id: this.props.user.enterprise_id,
         region_name:globalUtil.getCurrRegionName(),
         memory: 2,
         disk: 4,
         rent_time: 100
      },
      callback: (data) => {
         console.log(data)
      }
    })
  }
  handleMemoryChange = (value) => {
     console.log(value)
  }
  handleDiskChange = (value) => {
    console.log(value)
 }
  render() {
    const dataCenter = this.state.dataCenter;
    const usedDisk = this.state.disk.used || 0;
    const limitDisk = this.state.disk.limit || 0;
    const timeDisk = this.state.disk.expire_date || '未包月或已到期'
    const usedMemory= this.state.memory.used  || 0;
    const limitMemory = this.state.memory.limit || 0;
    const timeMemory = this.state.memory.expire_date || '未包月或已到期'

    const pageHeaderContent = (
        null
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
          title: "资源规划",
          href: ``
        }]}
        content={pageHeaderContent}
      >
      
        <Card
          className={styles.listCard}
          bordered={false}
        >
            <div >
              <div>
                  <strong>配置计算资源</strong>
                  <Row style={{padding:'5px 0'}}>
                      <Col span={2} style={{fontSize:'16px', paddingTop: 8}}>
                        内存
                      </Col>

                      <Col span={16}> 
                        <Slider onAfterChange={this.handleMemoryChange} step={1} min={0} max={1024 * 100} marks={{
                      }}  /></Col>
                      <Col span={4} style={{fontSize:'16px', paddingTop: 8}}>MB</Col>
                  </Row>
                  <Row style={{padding:'5px 0'}}>
                      <Col span={2} style={{fontSize:'16px', paddingTop: 8}}>
                        磁盘
                      </Col>
                      <Col span={16}> 
                        <Slider  onAfterChange={this.handleDiskChange} step={1} min={0} max={1024 * 100} marks={{
                      }}  /></Col>
                      <Col span={4} style={{fontSize:'16px', paddingTop: 8}}>GB</Col>
                  </Row>
                  <Row style={{padding:'5px 0'}}>
                      <Col span={2} style={{fontSize:'16px'}}>
                         服务期限
                      </Col>
                      <Col span={22}>
                         到期时间:{timeDisk}
                      </Col>
                      <Col span={2}></Col>
                      <Col span={22}></Col>
                  </Row>
              </div>
              <Divider />
              <div>
                  <strong>费用详情</strong>

              </div>
            </div>
        </Card>
      </PageHeaderLayout>
    );
  }
}
