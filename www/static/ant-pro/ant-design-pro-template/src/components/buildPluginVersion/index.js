/*
  添加或者修改插件配置
*/
import React, { PureComponent, Fragment } from 'react';
import { connect } from 'dva';
import { Link, Switch, Route } from 'dva/router';
import { Row, Col, Card, Form, Button, Icon, Menu, Input,  Dropdown, Table, Modal, Radio, Select, Tooltip, Tabs} from 'antd';
import globalUtil from '../../utils/global';
import LogProcress from '../../components/LogProcress';
import userUtil from '../../utils/user';
import teamUtil from '../../utils/team';
import regionUtil from '../../utils/region';
const TabPane = Tabs.TabPane;

@connect(({ user, loading }) => ({
  
}))
class EndLog extends PureComponent {
   constructor(props){
     super(props);
     this.state = {
        logs:[]
     }
   }
   componentDidMount(){
      this.getBuildVersionLog()
   }
   getBuildVersionLog(){
       this.props.dispatch({
          type:'plugin/getBuildVersionLog',
          payload:{
             team_name: globalUtil.getCurrTeamName(),
             plugin_id: this.props.plugin_id,
             build_version: this.props.build_version,
             level: this.props.level
          },
          callback: (data) =>{
             this.setState({logs: data.list||[]})
          }
       })
   }
   render(){
     const logs = this.state.logs;
     return (
          <div>
            {
              logs.map((item)=>{
                  return <p style={{marginBottom: 0}}>{item.message}</p>
              })
            }
          </div>
     )
   }
}

@connect(({ user, loading }) => ({
  currUser: user.currentUser,
}))
export default class Index extends PureComponent {
   constructor(props){
     super(props);
     this.state = {
        status: '',
        event_id: ''
     }
     this.mount = false;
   }
   componentDidMount(){
      this.mount = true;''
      this.getStatus();
   }
   componentWillUnmount(){
      this.mount = false;
   }
   getStatus = () => {
      const plugin_id = this.props.plugin_id;
      const build_version = this.props.build_version;
      console.log(build_version, plugin_id)
      this.props.dispatch({
         type: 'plugin/getBuildPluginVersionStatus',
         payload:{
            team_name: globalUtil.getCurrTeamName(),
            build_version: build_version,
            plugin_id: plugin_id
         },
         callback: (data) => {
             this.setState({status: data.bean.status, event_id: data.bean.event_id})
         }
      })
   }
   handleCancel = () => {
     this.props.onCancel && this.props.onCancel();
   }
   getSocketUrl = () => {
      var currTeam = userUtil.getTeamByTeamName(this.props.currUser, globalUtil.getCurrTeamName());
      var currRegionName = globalUtil.getCurrRegionName();

      if(currTeam){
         var region = teamUtil.getRegionByName(currTeam, currRegionName);

         if(region){
            return regionUtil.getEventWebSocketUrl(region);
         }
      }
      return '';
  }
   render(){
      const eventId = this.state.event_id;
      const plugin_id = this.props.plugin_id;
      const build_version = this.props.build_version;
      return (
        <Modal
        title= {"版本构建日志"}
        width={600}
        visible={true}
        onOk={this.handleSubmit}
        onCancel = {this.handleCancel}
        footer={[<Button onClick={this.handleCancel}>关闭</Button>]}
        > 
          <div style={{padding: '8px', minHeight: 300, maxHeight: 500, overflowY: 'auto'}}>
          {
             this.state.status === 'building' ? 
             <LogProcress socketUrl={this.getSocketUrl()} eventId={eventId} />
             :
             <Tabs type="card">
                <TabPane tab="Info" key="1">
                   <EndLog plugin_id={plugin_id} build_version={build_version} level="info"  />
                </TabPane>
                <TabPane tab="Debug" key="2">
                   <EndLog plugin_id={plugin_id} build_version={build_version} level="debug"  />
                </TabPane>
                <TabPane tab="Error" key="3">
                   <EndLog plugin_id={plugin_id} build_version={build_version} level="error"  />
                </TabPane>
              </Tabs>
          }
          </div>
        </Modal>
      )
   }
}