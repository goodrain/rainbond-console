import React, { PureComponent, Fragment } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import { Link, Switch, Route } from 'dva/router';
import { Row, Col, Card, Form, Button, Icon, Menu, Dropdown, Modal} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import { getRoutes } from '../../utils/utils';
import { getRouterData } from '../../common/router';

import styles from './Log.less';
import globalUtil from '../../utils/global';
import { getMonitorLog, getMonitorWebSocketUrl, getHistoryLog } from '../../services/app';
import AppLogSocket from '../../utils/appLogSocket';
import NoPermTip from '../../components/NoPermTip';
import appUtil from '../../utils/app';

class History1000Log extends PureComponent {
    constructor(props){
      super(props);
      this.state = {
        list:[],
        loading: true
      }
    }
    componentDidMount(){
      this.loadData();
    }
    loadData(){
       getMonitorLog({
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          lines: 1000
       }).then((data) => {
           if(data) {
               this.setState({loading: false, list: data.list || []})
           }
       })
    }
    render(){
        const {loading, list} = this.state;
        return (
           <Modal
            title="最近1000条日志"
            visible={true}
            width={1000}
            onCancel = {this.props.onCancel}
            footer={[<Button onClick={this.props.onCancel}>关闭</Button>]}
           >

            {
              loading ? 
              <div style={{textAlign: 'center'}}>
                 <Icon type="loading" style={{marginTop: 100, marginBottom: 100}} />
              </div>
              :''
            }

            {
              !loading ? 
              <div style={{textAlign: 'left', maxHeight: 600, overflowY: 'auto', background: '#000'}}>
                 {
                   list.length > 0 ?
                   <div>
                      {
                        list.map((item)=>{
                            return (
                              <p style={{marginBottom:0, color:'#999'}}>-- {item}</p>
                            )
                        })
                      }
                   </div>
                   :
                   <p  style={{textAlign: 'center',marginBottom:0, color:'#999'}}>暂无日志</p>
                 }
              </div>
              :''
            }


           </Modal>
        )
    }
}




class HistoryLog extends PureComponent {
    constructor(props){
      super(props);
      this.state = {
        list:[],
        loading: true
      }
    }
    componentDidMount(){
      this.loadData();
    }
    loadData(){
       getHistoryLog({
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias
       }).then((data) => {
           if(data) {
               this.setState({loading: false, list: data.list || []})
           }
       })
    }
    render(){
        const {loading, list} = this.state;
        return (
           <Modal
            title="历史日志下载"
            visible={true}
            width={700}
            onCancel = {this.props.onCancel}
            footer={[<Button onClick={this.props.onCancel}>关闭</Button>]}
           >

            {
              loading ? 
              <div style={{textAlign: 'center'}}>
                 <Icon type="loading" style={{marginTop: 100, marginBottom: 100}} />
              </div>
              :''
            }

            {
              !loading ? 
              <div style={{textAlign: 'left'}}>
                 {
                   list.length > 0 ?
                   <div>
                      {
                        list.map((item)=>{
                            return (
                              <p><a target="_blank" href={"//"+item.file_url}>{item.file_name}</a></p>
                            )
                        })
                      }
                   </div>
                   :
                   <p  style={{textAlign: 'center'}}>暂无历史日志</p>
                 }
              </div>
              :''
            }


           </Modal>
        )
    }
}



@connect(({ user, appControl }) => ({
  currUser: user.currentUser
}),null, null, {withRef:true})
export default class Index extends PureComponent {
  constructor(arg){
    super(arg);
    this.state = {
        logs:[],
        started: true,
        websocketUrl: '',
        showHistoryLog: false,
        showHistory1000Log: false
    }
    this.socket = null;
  }

  componentDidMount() {
    if(!this.canView()) return;
    const { dispatch } = this.props;
    this.loadLog();
    this.loadWebSocketUrl();
   
  }//是否可以浏览当前界面
  canView(){
    return appUtil.canManageAppLog(this.props.appDetail);
  }
  loadLog(){
      getMonitorLog({
         team_name: globalUtil.getCurrTeamName(),
         app_alias: this.props.appAlias
      }).then((data) => {
          if(data){
              this.setState({logs: (data.list || []).reverse()})
          }
      })
  }
  loadWebSocketUrl(){
     
     getMonitorWebSocketUrl({
         team_name: globalUtil.getCurrTeamName(),
         app_alias: this.props.appAlias
      }).then((data) => {
          if(data){
              this.state.websocketUrl = data.bean.web_socket_url;
              this.createSocket();
          }
      })
  }
  componentWillUnmount(){
      if(this.socket){
          this.socket.destroy();
          this.socket = null;
      }
  }
  createSocket(){
      const appDetail = this.props.appDetail;
      if(this.state.websocketUrl){
         this.socket = new AppLogSocket({
          url: this.state.websocketUrl,
          serviceId: appDetail.service.service_id,
          isAutoConnect: true,
          onMessage: (msg) =>  {
            if(this.state.started){
                var logs = this.state.logs || [];
                this.setState({logs: [msg].concat(logs)})
            }
          }
        })
      }
  }
  handleStop = ()=>{
    this.setState({started: false})
  }
  handleStart=()=>{
    this.setState({started: true})
  }
  showDownHistoryLog = () =>{
      this.setState({showHistoryLog: true})
  }
  hideDownHistoryLog = () =>{
      this.setState({showHistoryLog: false})
  }

  showDownHistory1000Log = () =>{
      this.setState({showHistory1000Log: true})
  }
  hideDownHistory1000Log = () =>{
      this.setState({showHistory1000Log: false})
  }
  render() {
    if(!this.canView()) return <NoPermTip />;
    const logs = this.state.logs;
    return (
     <Card
      title={
        <Fragment>
          {
            this.state.started ?
              <Button onClick={this.handleStop}>
                暂停推送
              </Button>
            :
            <Button onClick={this.handleStart}>
              开始推送
            </Button>
          }
          
          
        </Fragment>
      }
      extra={
        <Fragment>
            <a onClick={this.showDownHistoryLog} href="javascript:;" style={{marginRight: 10}}>历史日志下载</a>
            <a onClick={this.showDownHistory1000Log} href="javascript:;">最近1000条日志</a>
        </Fragment>
      }
     >
        <div className={styles.logs}>
          {
            logs.map((log) => {
               return (
                  <p>{log}</p>
               )
            })
          }
        </div>
        {this.state.showHistoryLog && <HistoryLog onCancel={this.hideDownHistoryLog} appAlias={this.props.appAlias} />}
        {this.state.showHistory1000Log && <History1000Log onCancel={this.hideDownHistory1000Log} appAlias={this.props.appAlias} />}
     </Card>
    );
  }
}
