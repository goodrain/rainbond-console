import React, { PureComponent } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import { Table, Card, Row, Col, Radio, Input, Button, Icon, DatePicker, Tooltip, Menu, Dropdown,Divider,Slider, InputNumber,Link, notification} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import styles from '../List/BasicList.less';
import globalUtil from '../../utils/global';
import sourceUnit from '../../utils/source-unit';
import InvoiceForm from '../../components/InvoiceForm';
const { RangePicker } = DatePicker;

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
      const format = "YYYY-MM-DD";
      this.state = {
        dataCenter: null,
        disk:{},
        memory:{},
        time:'',
        buydisk:0,
        buymemory: 0,
        buytime:0,
        dateFormat:  format,
        defaultStartDate : moment().format(format),
        defaultEndDate: moment().add(30, 'day').format(format),
        endDate: '',
        money:{}
      }
  }
  componentDidMount() {
     this.getRegionResource();
    //  this.getResPrice();
    //  this.buyPurchase();
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
      callback: (data) => {
        const endDateStr = data.bean.disk.expire_date || data.bean.memory.expire_date;
        const datas = {
          dataCenter:data.bean,
          disk:data.bean.disk,
          memory:data.bean.memory,
          buydisk: data.bean.disk.limit || 1,
          buymemory: data.bean.memory.limit || 1024
        }
        if(endDateStr){
           datas.defaultEndDate = moment(endDateStr).format('YYYY-MM-DD')

        }
        this.setState(datas, () => {
           this.getResPrice();
        })
      }
    })
  }
  
  getResPrice(){
    const regionName = this.props.match.params.regionName;
    moment(this.state.endDate || this.state.defaultEndDate).diff(moment(this.state.defaultStartDate), 'days');
    this.props.dispatch({
      type: 'global/resPrice',
      payload:{
         team_name: globalUtil.getCurrTeamName(),
         region_name: regionName,
         memory: this.state.buymemory,
         disk: this.state.buydisk,
         rent_time: moment(this.state.endDate || this.state.defaultEndDate).diff(moment(this.state.defaultStartDate), 'days')
      },
      callback: (data) => {
         this.setState({money: data.bean})
      }
    })
  }

  buyPurchase = () => {
    const regionName = this.props.match.params.regionName;
    moment(this.state.endDate || this.state.defaultEndDate).diff(moment(this.state.defaultStartDate), 'days')
    this.props.dispatch({
      type: 'global/buyPurchase',
      payload:{
         team_name: globalUtil.getCurrTeamName(),
         region_name: regionName,
         memory: this.state.buymemory,
         disk: this.state.buydisk,
         rent_time: moment(this.state.endDate || this.state.defaultEndDate).diff(moment(this.state.defaultStartDate), 'days')
      },
      callback: (data) => {
         this.getRegionResource();
         notification.success({message: '包月成功'})
      }
    })
  }
  handleMemoryChange = (value) => {
     this.setState({buymemory: value}, () => {
      this.getResPrice();
    })

  }
  handleDiskChange = (value) => {
    this.setState({buydisk: value}, () => {
      this.getResPrice();
    })
 }
  handleDateChange = (d) => {
    this.setState({endDate: d[1].format(this.state.dateFormat)}, () => {
       this.getResPrice();
    });
  }
  checkMemoryChange = (v) => {
     if(v < this.state.memory.limit){
        this.setState({buymemory: this.state.memory.limit||1024})
     }else{
      this.setState({buymemory: v})
     }
  }
  checkDiskChange = (v) => {
    if(v < this.state.disk.limit){
      this.setState({buydisk: this.state.disk.limit||1})
    }else{
      this.setState({buydisk: v})
    }
  }
  render() {
    const dataCenter = this.state.dataCenter;
    if(!dataCenter) return null;
    const usedDisk = this.state.disk.used || 0;
    const limitDisk = this.state.disk.limit || 0;
    const timeDisk = this.state.disk.expire_date || '未包月或已到期'
    const usedMemory= this.state.memory.used  || 0;
    const limitMemory = this.state.memory.limit || 0;
    const timeMemory = this.state.memory.expire_date || '未包月或已到期'
    const memoryMasks = {}
    
    memoryMasks[usedMemory] = <Tooltip title={"当前使用量: "+ sourceUnit.unit(usedMemory, 'MB')}><Icon type="up" /></Tooltip>;
    memoryMasks[limitMemory] = <Tooltip title={"已包月: " +  sourceUnit.unit(limitMemory, 'MB')}><Icon type="up" /></Tooltip>;

    const diskMasks = {}
    diskMasks[usedDisk] = <Tooltip title={"当前使用量: "+ sourceUnit.unit(usedDisk, 'GB')}><Icon type="up" /></Tooltip>;
    diskMasks[limitDisk] = <Tooltip title={"已包月: " +  sourceUnit.unit(limitDisk, 'GB')}><Icon type="up" /></Tooltip>;
    const money = this.state.money;
    

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
          href: `/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/finance`
        }, {
          title: `${this.state.dataCenter.alias || ''}`,
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
                  <h3>配置资源</h3>
                  <Row>
                      <Col span={2} style={{fontSize:'16px', paddingTop: 8}}>
                        内存
                      </Col>

                      <Col span={16}> 
                        <Slider tipFormatter={(value) => {
                           return sourceUnit.unit(value, 'MB')
                        }} value={this.state.buymemory || 1} onChange={this.checkMemoryChange} onAfterChange={this.handleMemoryChange} step={512} min={0} max={1024 * 100} marks={memoryMasks}  /></Col>
                      <Col span={4} style={{fontSize:'16px', paddingTop: 8}}> {sourceUnit.unit(this.state.buymemory, 'MB')} </Col>
                  </Row>
                  <Row>
                      <Col span={2} style={{fontSize:'16px', paddingTop: 8}}>
                        磁盘
                      </Col>
                      <Col span={16}> 
                        <Slider
                         onChange={this.checkDiskChange}
                         tipFormatter={(value) => {
                           return sourceUnit.unit(value, 'GB')
                        }}  value={this.state.buydisk || 1}  onAfterChange={this.handleDiskChange} step={1} min={0} max={1024} marks={diskMasks}  /></Col>
                      <Col span={4} style={{fontSize:'16px', paddingTop: 8}}> {sourceUnit.unit(this.state.buydisk, 'GB')}</Col>
                  </Row>
                  <Row style={{padding:'5px 0'}}>
                      <Col span={2} style={{fontSize:'16px'}}>
                         包月时长
                      </Col>
                      <Col span={22}>
                      <RangePicker onChange={this.handleDateChange} disabledDate={(current)=>{
                        return current < moment(this.state.defaultEndDate, this.state.dateFormat);
                      }} value={[moment(this.state.defaultStartDate, this.state.dateFormat), moment(this.state.endDate || this.state.defaultEndDate, this.state.dateFormat)]} format={this.state.dateFormat} />
                      </Col>
                      <Col span={2}></Col>
                      <Col span={22}></Col>
                  </Row>
              </div>
              <Divider />
              <div>
                  <h3>费用详情</h3>
                  <p></p>
                  <p>
                       总费用： {money.total_fee || 0} 元
                  </p>
                  <p>
                       已付费： {((money.total_fee - money.actual_fee) || 0).toFixed(2)} 元
                  </p>
                  <p>
                       应付费： {money.actual_fee || 0} 元
                  </p>
              </div>
              <Row>
                <Col span="24">
                    <Button onClick={this.buyPurchase} type="primary" style={{marginRight: 8}}>确认购买</Button>
                    <Button onClick={()=>{history.back()}} style={{marginRight: 8}}>返回</Button>
                </Col>
              </Row>
            </div>
        </Card>
      </PageHeaderLayout>
    );
  }
}
