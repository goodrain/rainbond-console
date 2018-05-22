import React, {PureComponent, Fragment} from 'react';
import {
  Button,
  Icon,
  Card,
  Modal,
  Row,
  Col,
  Switch,
  Table,
  Radio,
  Tabs,
  Affix,
  Input
} from 'antd';
import {connect} from 'dva';
import {routerRedux} from 'dva/router';
import globalUtil from '../../utils/global';
import {Link} from 'dva/router';
import httpResponseUtil from '../../utils/httpResponse';
import ConfirmModal from '../../components/ConfirmModal';

import appUtil from '../../utils/app';
import {buildApp} from '../../services/createApp';
import AppCreateSetting from '../../components/AppCreateSetting';

@connect(({user, appControl, teamControl, createApp}) => ({}), null, null, {withRef: true})
export default class Index extends PureComponent {
  constructor(props) {
    super(props);
    this.state = {
      //property、deploy
      type: 'property',
      appDetail: null
    }
  }
  componentDidMount() {
    this.loadDetail();
  }
  componentWillUnmount() {
    this
      .props
      .dispatch({type: 'appControl/clearDetail'})
  }
  loadDetail = () => {
    this
      .props
      .dispatch({
        type: 'appControl/fetchDetail',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.getAppAlias()
        },
        callback: (data) => {
          this.setState({appDetail: data});
        },
        handleError: (data) => {
          var code = httpResponseUtil.getCode(data);
          if (code) {
            //应用不存在
            if (code === 404) {
              this
                .props
                .dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/exception/404`));
            }

            //访问的应用不在当前的数据中心里
            if (code === 10404) {}

            //访问的应用不在当前团队里
            if (code === 10403) {}

          }

        }
      })
  }
  getAppAlias() {
    return this.props.match.params.appAlias;
  }

  handleBuild = () => {
    const team_name = globalUtil.getCurrTeamName();
    const app_alias = this.getAppAlias();
    buildApp({team_name: team_name, app_alias: app_alias}).then((data) => {
      if (data) {
        this
          .props
          .dispatch({
            type: 'global/fetchGroups',
            payload: {
              team_name: team_name
            }
          });
        this
          .props
          .dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/app/${app_alias}/overview`));
      }
    })
  }
  handleDelete = () => {
    const team_name = globalUtil.getCurrTeamName();
    const app_alias = this.getAppAlias();
    this
      .props
      .dispatch({
        type: 'appControl/deleteApp',
        payload: {
          team_name: team_name,
          app_alias: app_alias,
          is_force: true
        },
        callback: () => {
          this
            .props
            .dispatch(routerRedux.replace(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/index`))
        }
      })
  }
  showDelete = () => {
    this.setState({showDelete: true})
  }
  render() {
    const appDetail = this.state.appDetail || {};
    const type = this.state.type;

    if (!appDetail || !appDetail.service) {
      return null;
    }

    return (
      <div>
        <h2 style={{
          textAlign: 'center'
        }}>高级设置</h2>
        <div style={{
          overflow: 'hidden'
        }}>
          <AppCreateSetting appDetail={appDetail}/>
          <div
            style={{
            background: '#fff',
            padding: '20px',
            textAlign: 'right',
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            zIndex: 2,
            borderTop: '1px solid #e8e8e8'
          }}>
            <Button
              style={{
              marginRight: 8
            }}
              onClick={this.handleBuild}
              type="primary">确认构建</Button>
            <Button onClick={this.showDelete} type="default">放弃创建</Button>
          </div>
          {this.state.showDelete && <ConfirmModal
            onOk={this.handleDelete}
            title="放弃创建"
            subDesc="此操作不可恢复"
            desc="确定要放弃创建此应用吗？"
            onCancel={() => {
            this.setState({showDelete: false})
          }}/>}
        </div>

      </div>
    )
  }
}