import React, {PureComponent, Fragment} from 'react';
import moment from 'moment';
import {connect} from 'dva';
import {
  ChartCard,
  yuan,
  MiniArea,
  MiniBar,
  MiniProgress,
  Field,
  Bar,
  Pie,
  TimelineChart
} from '../../components/Charts';
import numeral from 'numeral';
import {Link, Switch, Route} from 'dva/router';
import {
  DatePicker,
  Row,
  Col,
  Card,
  Form,
  Button,
  Table,
  Icon,
  Menu,
  Dropdown,
  Tooltip
} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import {getRoutes, getTimeDistance} from '../../utils/utils';
import {getRouterData} from '../../common/router'

import styles from './Index.less';
import globalUtil from '../../utils/global';
import userUtil from '../../utils/user';
import teamUtil from '../../utils/team';
import regionUtil from '../../utils/region';

const ButtonGroup = Button.Group;
const {RangePicker} = DatePicker;
import monitorDataUtil from '../../utils/monitorDataUtil'

class Empty extends PureComponent {
  render() {
    return (
      <div
        style={{
        height: '300px',
        lineHeight: '300px',
        textAlign: ' center',
        fontSize: 26
      }}>暂无数据</div>
    )
  }
}

@connect(({user, appControl}) => ({currUser: user.currentUser, appDetail: appControl.appDetail, onlineNumberRange: appControl.onlineNumberRange, appRequestRange: appControl.appRequestRange, requestTimeRange: appControl.requestTimeRange}))
class MonitorHistory extends PureComponent {
  state = {
    houer: 1
  };
  getStartTime() {
    return (new Date().getTime() / 1000) - (60 * 60 * this.state.houer);
  }
  getStep() {
    if (this.state.houer > 24) {
      return 60 * 60;
    } else {
      return 60 * 2;
    }
  }
  componentDidMount() {
    this.mounted = true;
    this.inerval = 10000;
    this.fetchRequestTimeRange();
    this.fetchRequestRange();
    this.fetchOnlineNumberRange();
  }
  componentWillUnmount() {
    this.mounted = false;
  }
  fetchRequestTimeRange() {
    if (!this.mounted) 
      return;
    this
      .props
      .dispatch({
        type: 'appControl/fetchRequestTimeRange',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          start: this.getStartTime(),
          serviceId: this.props.appDetail.service.service_id,
          step: this.getStep()
        },
        complete: () => {
          if (this.mounted) {
            setTimeout(() => {
              this.fetchRequestTimeRange();
            }, this.inerval)
          }

        }
      })
  }
  fetchRequestRange() {
    if (!this.mounted) 
      return;
    this
      .props
      .dispatch({
        type: 'appControl/fetchRequestRange',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          start: this.getStartTime(),
          serviceId: this.props.appDetail.service.service_id,
          step: this.getStep()
        },
        complete: () => {
          if (this.mounted) {
            setTimeout(() => {
              this.fetchRequestRange();
            }, this.inerval)

          }
        }
      })
  }
  fetchOnlineNumberRange() {
    if (!this.mounted) 
      return;
    this
      .props
      .dispatch({
        type: 'appControl/fetchOnlineNumberRange',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          start: this.getStartTime(),
          serviceId: this.props.appDetail.service.service_id,
          step: this.getStep()
        },
        complete: () => {
          if (this.mounted) {
            setTimeout(() => {
              this.fetchOnlineNumberRange();
            }, this.inerval)

          }
        }
      })
  }

  selectDate = (houer) => {
    this.setState({houer});
  }
  isActive(houer) {
    if (houer === this.state.houer) {
      return styles.currentDate;
    }
  }
  render() {
    const {rangePickerValue} = this.state;

    const salesExtra = (
      <div className={styles.salesExtraWrap}>
        <div className={styles.salesExtra}>
          <a className={this.isActive(1)} onClick={() => this.selectDate(1)}>
            1小时
          </a>
          <a className={this.isActive(8)} onClick={() => this.selectDate(8)}>
            8小时
          </a>
          <a className={this.isActive(24)} onClick={() => this.selectDate(24)}>
            24小时
          </a>
          <a className={this.isActive(24 * 7)} onClick={() => this.selectDate(24 * 7)}>
            7天
          </a>
        </div>
      </div>
    );

    const requiestTime = monitorDataUtil.queryRangeTog2F(this.props.requestTimeRange);
    const appRequest = monitorDataUtil.queryRangeTog2F(this.props.appRequestRange);
    const online = monitorDataUtil.queryRangeTog2F(this.props.onlineNumberRange, true);

    return (
      <div>
        <Card
          title="响应时间"
          style={{
          marginBottom: 20
        }}
          extra={salesExtra}>
          {requiestTime.length
            ? <TimelineChart height={200} data={requiestTime}/>
            : <Empty/>
}
        </Card>
        <Card
          extra={salesExtra}
          title="吞吐率"
          style={{
          marginBottom: 20
        }}>
          {appRequest.length
            ? <TimelineChart height={200} data={appRequest}/>
            : <Empty/>
}

        </Card>
        <Card extra={salesExtra} title="在线人数">
          {online.length
            ? <TimelineChart height={200} data={online}/>
            : <Empty/>
}

        </Card>
      </div>
    )
  }
}

@connect(({user, appControl}) => ({
  currUser: user.currentUser,
  appDetail: appControl.appDetail,
  onlineNumber: appControl.onlineNumber,
  onlineNumberRange: appControl.onlineNumberRange,
  appRequest: appControl.appRequest,
  appRequestRange: appControl.appRequestRange,
  requestTime: appControl.requestTime,
  requestTimeRange: appControl.requestTimeRange
}))
class MonitorNow extends PureComponent {
  constructor(props) {
    super(props);
    this.inerval = 10000;
    this.state = {
      logs: []
    }
  }
  getStartTime() {
    return (new Date().getTime() / 1000) - (60 * 60)
  }
  getStep() {
    return 60;
  }
  componentDidMount() {
    this.mounted = true;
    this.fetchRequestTime();
    this.fetchRequestTimeRange();
    this.fetchRequest();
    this.fetchRequestRange();
    this.fetchOnlineNumber();
    this.fetchOnlineNumberRange();
    this.createSocket();
  }
  componentWillUnmount() {
    this.mounted = false;
    this.destroySocket();
    this
      .props
      .dispatch({type: 'appControl/clearOnlineNumberRange'})
    this
      .props
      .dispatch({type: 'appControl/clearRequestTime'})
    this
      .props
      .dispatch({type: 'appControl/clearRequestTimeRange'})
    this
      .props
      .dispatch({type: 'appControl/clearRequest'})
    this
      .props
      .dispatch({type: 'appControl/clearRequestRange'})
    this
      .props
      .dispatch({type: 'appControl/clearOnlineNumber'})
  }
  getSocketUrl = () => {
    var currTeam = userUtil.getTeamByTeamName(this.props.currUser, globalUtil.getCurrTeamName());
    var currRegionName = globalUtil.getCurrRegionName();

    if (currTeam) {
      var region = teamUtil.getRegionByName(currTeam, currRegionName);

      if (region) {
        return regionUtil.getMonitorWebSocketUrl(region);
      }
    }
    return '';
  }
  fetchRequestTime() {
    if (!this.mounted) 
      return;
    this
      .props
      .dispatch({
        type: 'appControl/fetchRequestTime',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          serviceId: this.props.appDetail.service.service_id
        },
        complete: () => {
          if (this.mounted) {
            setTimeout(() => {
              this.fetchRequestTime();
            }, this.inerval)

          }
        }
      })
  }
  fetchRequestTimeRange() {
    if (!this.mounted) 
      return;
    this
      .props
      .dispatch({
        type: 'appControl/fetchRequestTimeRange',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          start: this.getStartTime(),
          serviceId: this.props.appDetail.service.service_id,
          step: this.getStep()
        },
        complete: () => {
          if (this.mounted) {
            setTimeout(() => {
              this.fetchRequestTimeRange();
            }, this.inerval)
          }

        }
      })
  }
  fetchRequest() {
    if (!this.mounted) 
      return;
    this
      .props
      .dispatch({
        type: 'appControl/fetchRequest',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          serviceId: this.props.appDetail.service.service_id
        },
        complete: () => {
          if (this.mounted) {
            setTimeout(() => {
              this.fetchRequest();
            }, this.inerval)
          }
        }
      })
  }
  fetchRequestRange() {
    if (!this.mounted) 
      return;
    this
      .props
      .dispatch({
        type: 'appControl/fetchRequestRange',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          start: this.getStartTime(),
          serviceId: this.props.appDetail.service.service_id,
          step: this.getStep()
        },
        complete: () => {
          if (this.mounted) {
            setTimeout(() => {
              this.fetchRequestRange();
            }, this.inerval)

          }
        }
      })
  }
  fetchOnlineNumber() {
    if (!this.mounted) 
      return;
    this
      .props
      .dispatch({
        type: 'appControl/fetchOnlineNumber',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          serviceId: this.props.appDetail.service.service_id
        },
        complete: () => {
          if (this.mounted) {

            setTimeout(() => {
              this.fetchOnlineNumber();
            }, this.inerval)
          }
        }
      })
  }
  fetchOnlineNumberRange() {
    if (!this.mounted) 
      return;
    this
      .props
      .dispatch({
        type: 'appControl/fetchOnlineNumberRange',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          start: this.getStartTime(),
          serviceId: this.props.appDetail.service.service_id,
          step: this.getStep()
        },
        complete: () => {
          if (this.mounted) {
            setTimeout(() => {
              this.fetchOnlineNumberRange();
            }, this.inerval)

          }
        }
      })
  }
  destroySocket() {
    if (this.webSocket) {
      this
        .webSocket
        .close();
      this.webSocket = null;
    }
  }
  createSocket() {

    if (!this.mounted) 
      return;
    
    var self = this;
    this.webSocket = new WebSocket(this.getSocketUrl());
    this.webSocket.onopen = () => {
      if (self.webSocket) {
        self
          .webSocket
          .send("topic=" + this.props.appDetail.service.service_id);
      }

    }
    this.webSocket.onmessage = function (e) {
      if (self.webSocket && e.data && e.data !== 'ok') {
        self.updateTable(e.data);
      }
    };
    this.webSocket.onclose = function () {
      self.createSocket();
    }
  }
  updateTable(event) {
    try {
      event = JSON.parse(event);
    } catch (e) {}
    this.setState({logs: event})
  }
  render() {
    const topColResponsiveProps = {
      xs: 24,
      sm: 12,
      md: 12,
      lg: 12,
      xl: 8,
      style: {
        marginBottom: 24
      }
    };
    return (
      <Fragment>
        <Row gutter={24}>
          <Col {...topColResponsiveProps}>
            <ChartCard
              bordered={false}
              title="平均响应时间"
              action={< Tooltip title = "指标说明" > <Icon type="info-circle-o"/> < /Tooltip>}
              total={numeral(monitorDataUtil.queryTog2(this.props.requestTime)).format('0,0')}
              footer={< Field label = "最大响应时间" value = "-" />}
              contentHeight={46}>
              <MiniArea
                color="#975FE4"
                data={monitorDataUtil.queryRangeTog2(this.props.requestTimeRange)}/>
            </ChartCard>
          </Col>
          <Col {...topColResponsiveProps}>
            <ChartCard
              bordered={false}
              title="吞吐率"
              action={< Tooltip title = "指标说明" > <Icon type="info-circle-o"/> < /Tooltip>}
              total={numeral(monitorDataUtil.queryTog2(this.props.appRequest)).format('0,0')}
              footer={< Field label = "最大吞吐率" value = "-" />}
              contentHeight={46}>
              <MiniArea
                color="#4593fc"
                data={monitorDataUtil.queryRangeTog2(this.props.appRequestRange)}/>
            </ChartCard>
          </Col>
          <Col {...topColResponsiveProps}>
            <ChartCard
              bordered={false}
              title="在线人数"
              action={< Tooltip title = "指标说明" > <Icon type="info-circle-o"/> < /Tooltip>}
              total={numeral(monitorDataUtil.queryTog2(this.props.onlineNumber)).format('0,0')}
              footer={< Field label = "日访问量" value = "-" />}
              contentHeight={46}>
              <MiniBar data={monitorDataUtil.queryRangeTog2(this.props.onlineNumberRange)}/>
            </ChartCard>
          </Col>
        </Row>
        <Card title="过去5分钟耗时最多的URL排行">
          <Table
            columns={[
            {
              title: 'Url',
              dataIndex: 'Key'
            }, {
              title: '累计时间(ms)',
              dataIndex: 'CumulativeTime',
              width: 150
            }, {
              title: '平均时间(ms)',
              dataIndex: 'AverageTime',
              width: 150
            }, {
              title: '请求次数',
              dataIndex: 'Count',
              width: 100
            }, {
              title: '异常次数',
              dataIndex: 'AbnormalCount',
              width: 100
            }
          ]}
            pagination={false}
            dataSource={this.state.logs}/>
        </Card>
      </Fragment>
    )
  }
}

@connect(({user, appControl}) => ({currUser: user.currentUser}), null, null, {withRef: true})
export default class Index extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {
      type: 'now',
      anaPlugins: null
    }
  }
  componentDidMount() {
    this.getAnalyzePlugins();
  }
  getAnalyzePlugins() {
    this
      .props
      .dispatch({
        type: 'appControl/getAnalyzePlugins',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias
        },
        callback: (data) => {
          const list = data.list || [];
          this.setState({anaPlugins: list});
        }
      })
  }
  changeType = (type) => {
    if (type !== this.state.type) {
      this.setState({type: type});
    }
  }
  render() {
    const {type, anaPlugins} = this.state;
    const {appDetail} = this.props;

    if (!appDetail || !anaPlugins) {
      return null;
    }

    //判断是否有安装性能分析插件
    if (!anaPlugins.length) {
      return <Card>
        <div
          style={{
          textAlign: 'center',
          fontSize: 18,
          padding: '30px 0'
        }}>
          尚未开通性能分析插件

          <p style={{
            paddingTop: 8
          }}>
            <Link to={'/app/' + appDetail.service.service_alias + '/plugin'}>去开通</Link>
          </p>
        </div>
      </Card>
    }

    return (
      <Fragment>
        <div
          style={{
          textAlign: 'right',
          marginBottom: 25
        }}>
          <ButtonGroup>
            <Button
              onClick={() => {
              this.changeType('now')
            }}
              type={type === 'now'
              ? 'primary'
              : ''}>实时</Button>
            <Button
              onClick={() => {
              this.changeType('history')
            }}
              type={type === 'history'
              ? 'primary'
              : ''}>历史</Button>
          </ButtonGroup>
        </div>
        {type === 'now'
          ? <MonitorNow {...this.props}/>
          : <MonitorHistory {...this.props}/>
}
      </Fragment>
    );
  }
}
