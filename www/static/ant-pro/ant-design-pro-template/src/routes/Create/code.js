import React, {PureComponent} from 'react';
import moment from 'moment';
import PropTypes from 'prop-types';
import {connect} from 'dva';
import {Link, Switch, Route, routerRedux} from 'dva/router';
import {
  Row,
  Col,
  Card,
  Form,
  Button,
  Icon,
  Menu,
  Dropdown,
  notification
} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import {getRoutes} from '../../utils/utils';
import {getRouterData} from '../../common/router';
import ConfirmModal from '../../components/ConfirmModal';
import styles from './Index.less';
import globalUtil from '../../utils/global';
import CodeCustom from './code-custom';
import CodeDemo from './code-demo';
import CodeGoodrain from './code-goodrain';
import CodeGithub from './code-github';
import rainbondUtil from '../../utils/rainbond';
const ButtonGroup = Button.Group;

@connect(({user, groupControl, global}) => ({rainbondInfo: global.rainbondInfo}), null, null, {pure: false})
export default class Main extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {}
  }
  componentDidMount() {}
  componentWillUnmount() {}
  handleTabChange = (key) => {
    const {dispatch, match} = this.props;
    const {appAlias} = this.props.match.params;
    dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/create/code/${key}`));
  }
  render() {
    const rainbondInfo = this.props.rainbondInfo;

    const map = {
      'custom': CodeCustom,
      'demo': CodeDemo,
      'goodrain': CodeGoodrain,
      'github': CodeGithub
    }

    const tabList = [
      {
        key: 'custom',
        tab: '自定义源码'
      }, {
        key: 'demo',
        tab: '官方DEMO'
      }
    ];

    if (rainbondUtil.gitlabEnable(rainbondInfo)) {
      tabList.push({key: 'goodrain', tab: '好雨代码仓库'})
    }

    if (rainbondUtil.githubEnable(rainbondInfo)) {
      tabList.push({key: 'github', tab: 'GitHub项目'})
    }

    const {match, routerData, location} = this.props;
    var type = this.props.match.params.type;
    if (!type) {
      type = 'custom';
    }
    const Com = map[type]

    return (
      <PageHeaderLayout
        title={"由源码创建应用"}
        onTabChange={this.handleTabChange}
        content={< p > 从指定源码仓库中获取源码，基于源码信息创建新应用 < /p>}
        tabActiveKey={type}
        tabList={tabList}>

        {Com
          ? <Com {...this.props}/>
          : '参数错误'
}
      </PageHeaderLayout>
    );
  }
}
