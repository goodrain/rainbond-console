import React, {PureComponent} from 'react';
import {connect} from 'dva';
import {Card, Button, Icon, List} from 'antd';
import {Link, routerRedux} from 'dva/router';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import globalUtil from '../../utils/global';
import styles from './Index.less';
import CreatePluginForm from '../../components/CreatePluginForm';

@connect(({list, loading}) => ({}))
export default class Index extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {
      list: []
    }
    this.timer = null;
  }
  componentDidMount() {}
  handleSubmit = (val) => {
    this
      .props
      .dispatch({
        type: 'plugin/createPlugin',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          ...val
        },
        callback: ((data) => {
          this
            .props
            .dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/myplugns/${data.bean.plugin_id}`))
        })
      })
  }
  render() {
    const list = this.state.list;

    const content = (
      <div className={styles.pageHeaderContent}></div>
    );

    const extraContent = (
      <div className={styles.extraImg}></div>
    );

    return (
      <PageHeaderLayout title="创建插件" content={content} extraContent={extraContent}>
        <Card>
          <div
            style={{
            width: 500,
            margin: '20px auto'
          }}>
            <CreatePluginForm onSubmit={this.handleSubmit}/>
          </div>
        </Card>
      </PageHeaderLayout>
    );
  }
}
