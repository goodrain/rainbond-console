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
    this.props.dispatch({
      type: 'global/getRegionSource',
      payload:{
         team_name: globalUtil.getCurrTeamName(),
         enterprise_id: this.props.user.enterprise_id,
         region: globalUtil.getCurrRegionName()
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

  render() {
    const dataCenter = this.state.dataCenter;
    const usedDisk = this.state.disk.used || 0;
    const limitDisk = this.state.disk.limit || 0;
    const timeDisk = this.state.disk.expire_date || '未包月或已到期'
    const usedMemory= this.state.memory.used  || 0;
    const limitMemory = this.state.memory.limit || 0;
    const timeMemory = this.state.memory.expire_date || '未包月或已到期'

    const pageHeaderContent = (
        <Button style={{float:'right'}}><a target="_blank" href="https://www.goodrain.com/spa/#/personalCenter/my/recharge">发票查询</a></Button>
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
        title={"资源规划"}
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
                      <Col span={2} style={{fontSize:'16px'}}>
                        内存
                      </Col>
                      <Col span={22}>
                          包月用量:{limitMemory}(M)／实际用量:{usedMemory}(M)／到期时间:{timeMemory}
                      </Col>
                      <Col span={2}></Col>
                      <Col span={22}>
                          <Slider  />
                      </Col>
                  </Row>
                  <Row style={{padding:'5px 0'}}>
                      <Col span={2} style={{fontSize:'16px'}}>
                        磁盘
                      </Col>
                      <Col span={22}>
                          包月用量:{limitDisk}(G)／实际用量:{usedDisk}(G)／到期时间:{timeDisk}
                      </Col>
                      <Col span={2}></Col>
                      <Col span={22}><Slider  /></Col>
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
