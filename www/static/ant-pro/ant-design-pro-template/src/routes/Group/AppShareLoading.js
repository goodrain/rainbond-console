import React, {PureComponent, Fragment} from 'react';
import {
  Button,
  Icon,
  Card,
  Modal,
  Form,
  Input,
  Select
} from 'antd';
import {connect} from 'dva';
import {routerRedux} from 'dva/router';
import Result from '../../components/Result';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import ConfirmModal from '../../components/ConfirmModal';
import globalUtil from '../../utils/global';
import CodeCustomForm from '../../components/CodeCustomForm';
import LogProcress from '../../components/LogProcress';
import userUtil from '../../utils/user';
import regionUtil from '../../utils/region';

@connect(({user, appControl, loading}) => ({currUser: user.currentUser, loading: loading}))
class ShareEvent extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      data: this.props.data || {},
      eventId: this.props.data.event_id || '',
      status: this.props.data.event_status || 'not_start'
    }
    this.mount = false;
    var teamName = globalUtil.getCurrTeamName();
    var regionName = globalUtil.getCurrRegionName();
    var region = userUtil.hasTeamAndRegion(this.props.currUser, teamName, regionName);
    if (region) {
      this.socketUrl = regionUtil.getEventWebSocketUrl(region);
    }
  }
  componentDidMount = () => {
    this.mount = true;
    this.checkStatus();
  }
  checkStatus = () => {
    const data = this.state.data;
    const status = this.state.status;
    if (status === 'not_start') {
      this.props.receiveStartShare && this.props.receiveStartShare(this.startShareEvent);
    }
    if (status === 'start') {
      this.getShareStatus();
    }
    if (status === 'success') {
      this.onSuccess();
    }

    if (status === 'failure') {
      this.onFail();
    }
  }
  componentWillUnmount = () => {
    this.mount = false;
  }
  onSuccess = () => {
    this.props.onSuccess && this
      .props
      .onSuccess()
  }
  onFail = () => {
    this.props.onFail && this
      .props
      .onFail(this);
  }
  reStart = () => {
    this.setState({eventId: ''})
    this.startShareEvent();
  }
  getShareStatus = () => {
    if (this.state.status !== 'start' || !this.mount) 
      return;
    this
      .props
      .dispatch({
        type: 'groupControl/getShareStatus',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          share_id: this.props.share_id,
          event_id: this.state.data.ID
        },
        callback: (data) => {
          this.setState({
            status: data.bean.event_status
          }, () => {
            if (this.state.status === 'success') {
              this.onSuccess()
            }
            if (this.state.status === 'failure') {
              this.onFail()
            }
            setTimeout(() => {
              this.getShareStatus()
            }, 5000)
          })
        }
      })
  }
  startShareEvent = () => {
    this
      .props
      .dispatch({
        type: 'groupControl/startShareEvent',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          share_id: this.props.share_id,
          event_id: this.state.data.ID
        },
        callback: (data) => {
          this.setState({
            eventId: data.bean.event_id,
            status: data.bean.event_status
          }, () => {
            this.getShareStatus();
            this.props.onStartSuccess && this.props.onStartSuccess()
          })
        }
      })
  }
  renderStatus = () => {
    if (this.state.status === 'start') {
      return <Icon type="sync" className="roundloading"/>
    }
    if (this.state.status === 'success') {
      return <Icon type="check-circle" style={{
        color: '#52c41a'
      }}/>
    }
    if (this.state.status === 'failure') {
      return <Icon type="close-circle"/>
    }
    return null;
  }
  render() {
    const data = this.state.data || {};
    const eventId = this.state.eventId;
    return (
      <div style={{
        marginBottom: 24
      }}>
        <h4>应用名称: {data.service_name}
          {this.renderStatus()}</h4>
        <div>
          {eventId && <LogProcress socketUrl={this.socketUrl} eventId={eventId}/>}
        </div>
      </div>
    )
  }

}

@connect(({user, appControl, loading}) => ({loading: loading}))
export default class shareCheck extends PureComponent {
  constructor(props) {
    super(props);
    this.state = {
      //failure、checking、success
      status: 'checking',
      shareEventList: [],
      successNum: 0,
      showDelete: false,
      startShareCallback: [],
      isStart: false
    }
    this.fails = []
    this.mount = false;
  }
  receiveStartShare = (callback) => {
     this.state.startShareCallback.push(callback);
     if(!this.state.isStart){
        this.state.isStart = true;
        callback();
     }
  }
  handleStartShareSuccess = () => {
     this.state.startShareCallback.shift();
     if(this.state.startShareCallback[0]){
      this.state.startShareCallback[0]();
     }
  }
  componentDidMount() {
    this.mount = true;
    this.getShareEventInfo();

  }

  getShareEventInfo = () => {
    const params = this.getParams();
    this
      .props
      .dispatch({
        type: 'groupControl/getShareEventInfo',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          share_id: params.shareId
        },
        callback: (data) => {
          this.setState({
            shareEventList: data.bean.event_list || [],
            status: !data.bean.is_compelte
              ? 'checking'
              : 'success'
          })
        }
      })
  }
  getParams = () => {
    return {shareId: this.props.match.params.shareId, groupId: this.props.match.params.groupId}
  }
  componentWillUnmount() {
    this.mount = false;

  }
  handleSuccess = () => {
    this.state.successNum++;
    if (this.state.successNum === this.state.shareEventList.length) {
      this.setState({status: 'success'})
    }
  }
  handleFail = (com) => {
    this
      .fails
      .push(com);
    this.setState({status: 'failure'})
  }
  renderChecking = () => {}
  renderError = () => {
    const extra = (
      <div></div>
    );
    const actions = [< Button onClick = {
        this.showDelete
      }
      type = "default" > 放弃创建 < /Button>, 
        <Button onClick={this.recheck} type="primary">重新检测</Button >];

    return <Result
      type="error"
      title="应用分享失败"
      description="请核对并修改以下信息后，再重新检测。"
      extra={extra}
      actions={actions}
      style={{
      marginTop: 48,
      marginBottom: 16
    }}/>
  }
  renderSuccess = () => {
    const extra = (
      <div></div>
    );
    const actions = [ < Button onClick = {
        this.handleBuild
      }
      type = "primary" > 构建应用 < /Button>,
        <Button type="default" onClick={this.handleSetting}>高级设置</Button >, < Button onClick = {
        this.showDelete
      }
      type = "default" > 放弃创建 < /Button>];
        return <Result
              type="success"
              title="应用分享成功"
              description="您可以执行以下操作"
              extra={extra}
              actions={actions}
              style={{ marginTop: 48, marginBottom: 16 }}
            / >
    }
    handleReStart = () => {
      if (!this.fails.length) 
        return;
      this
        .fails
        .forEach((item, index) => {
          item.reStart();
        })
      this.fails = [];
      this.setState({status: 'checking'});
    }
    handleCompleteShare = () => {
      const params = this.getParams();
      this
        .props
        .dispatch({
          type: 'groupControl/completeShare',
          payload: {
            team_name: globalUtil.getCurrTeamName(),
            share_id: params.shareId
          },
          callback: (data) => {
            if(data.app_market_url){
              window.location.href = data.app_market_url;
              return;
            }
            this
              .props
              .dispatch(routerRedux.replace(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/groups/${params.groupId}`))
          }
        })
    }
    handleGiveUp = () => {
      const params = this.getParams();
      this
        .props
        .dispatch({
          type: 'groupControl/giveupShare',
          payload: {
            team_name: globalUtil.getCurrTeamName(),
            share_id: params.shareId
          },
          callback: (data) => {
            this.hideShowDelete();
            this
              .props
              .dispatch(routerRedux.replace(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/groups/${params.groupId}`))
          }
        })
    }
    renderBody = () => {
      const params = this.getParams();
      const eventList = this.state.shareEventList;
      const status = this.state.status;
      const loading = this.props.loading;
      const extra = (
        <div>
          {(eventList || []).map((item) => {
            return <ShareEvent
              receiveStartShare = {this.receiveStartShare}
              onStartSuccess = {this.handleStartShareSuccess}
              onFail={this.handleFail}
              onSuccess={this.handleSuccess}
              share_id={params.shareId}
              data={item}/>
          })
}
        </div>
      );
      var type = '';
      var title = '';
      var desc = '';
      var actions = [];
      if (status === 'success') {
        type = 'success';
        title = "应用同步成功"
        desc = ""
        actions = [ < Button onClick = {
            this.handleCompleteShare
          }
          type = "primary" > 确认分享 < /Button>];
         }
         if(status === 'checking'){
           type = 'ing'
           title="应用同步中"
           desc = "此过程可能比较耗时，请耐心等待";
           actions = [<Button onClick={this.showDelete} type="default">放弃分享</Button >];
      }
      if (status === 'failure') {
        type = 'error';
        desc = "请查看以下日志确认问题后重新同步";
        actions = [< Button onClick = {
            this.handleReStart
          }
          type = "primary" > 重新同步 < /Button>, <Button  onClick={this.showDelete} type="default">放弃分享</Button >];
      }
      return <Result
        type={type}
        title={title}
        extra={extra}
        description={desc}
        actions={actions}
        style={{
        marginTop: 48,
        marginBottom: 16
      }}/ >
        }
        showDelete = () => {
          this.setState({showDelete: true})
        }
        hideShowDelete = () => {
          this.setState({showDelete: false})
        }
        render() {
          const loading = this.props.loading;
          const shareEventList = this.state.shareEventList;
          if (!shareEventList.length) 
            return null;
          return <PageHeaderLayout>
            <Card bordered={false}>
              {this.renderBody()}
              {status === 'checking' && this.renderChecking()}
              {status === 'success' && this.renderSuccess()}
              {status === 'failure' && this.renderError()}
            </Card>
            {this.state.showDelete && <ConfirmModal
              disabled={loading.effects['groupControl/giveupShare']}
              onOk={this.handleGiveUp}
              onCancel={this.hideShowDelete}
              title="放弃分享"
              desc="确定要放弃此次分享吗?"/>}
          </PageHeaderLayout>
        }
      }