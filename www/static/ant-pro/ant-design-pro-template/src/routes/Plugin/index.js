import React, {PureComponent} from 'react';
import {connect} from 'dva';
import {Card, Button, Icon, List} from 'antd';
import {Link, routerRedux} from 'dva/router';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import globalUtil from '../../utils/global';
import pluginUtil from '../../utils/plugin';
import styles from './Index.less';
import Ellipsis from '../../components/Ellipsis';
import Manage from './manage';

@connect(({list, loading}) => ({}))
class PluginList extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {
      list: []
    }
    this.timer = null;
  }
  componentDidMount() {
    this
      .props
      .dispatch({
        type: 'plugin/getMyPlugins',
        payload: {
          team_name: globalUtil.getCurrTeamName()
        },
        callback: ((data) => {
          this.setState({
            list: data.list || []
          })
        })
      });
  }
  handleCreate = () => {
    this
      .props
      .dispatch(routerRedux.push("/create-plugin"))
  }
  render() {
    const list = this.state.list;

    const content = (
      <div className={styles.pageHeaderContent}>
        <p>
          应用插件是标准化的为应用提供功能扩展，与应用共同运行的程序
        </p>
      </div>
    );

    const extraContent = (
      <div className={styles.extraImg}></div>
    );

    return (
      <PageHeaderLayout title="我的插件" content={content} extraContent={extraContent}>
        <div className={styles.cardList}>
          <List
            rowKey="id"
            grid={{
            gutter: 24,
            lg: 3,
            md: 2,
            sm: 1,
            xs: 1
          }}
            dataSource={[
            '', ...list
          ]}
            renderItem={item => (item
            ? (
              <List.Item
                key={item.id}
                onClick={() => {
                this
                  .props
                  .dispatch(routerRedux.push('/myplugns/' + item.plugin_id))
              }}>
                <Card
                  hoverable
                  className={styles.card}
                  actions={[ < span > {
                    pluginUtil.getCategoryCN(item.category)
                  } < /span>, <Link to={'/myplugns / '+item.plugin_id}>管理</Link>]}>
                  <Card.Meta
                    avatar={< Icon style = {{fontSize: 50, color:'rgba(0, 0, 0, 0.2)'}}type = "api" />}
                    title={< Link to = {
                    '/myplugns/' + item.plugin_id
                  } > {
                    item.plugin_alias
                  } < /Link>}
                    description={(
                    <Ellipsis className={styles.item} lines={3}>{item.desc}</Ellipsis>
                  )}/>
                </Card>
              </List.Item>
            )
            : (
              <List.Item>
                <Button type="dashed" onClick={this.handleCreate} className={styles.newButton}>
                  <Icon type="plus"/>
                  新建插件
                </Button>
              </List.Item>
            ))}/>
        </div>
      </PageHeaderLayout>
    );
  }
}

export default class Index extends PureComponent {
  render() {
    const pluginId = this.props.match.params.pluginId;
    if (pluginId) {
      return <Manage {...this.props}/>
    } else {
      return <PluginList {...this.props}/>
    }
  }
}
