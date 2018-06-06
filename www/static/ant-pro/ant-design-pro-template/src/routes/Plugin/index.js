import React, {PureComponent} from 'react';
import {connect} from 'dva';
import {Card, Button, Icon, List} from 'antd';
import {Link, routerRedux} from 'dva/router';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import globalUtil from '../../utils/global';
import pluginUtil from '../../utils/plugin';
import userUtil from '../../utils/user';
import TeamUtil from '../../utils/team';
import styles from './Index.less';
import Ellipsis from '../../components/Ellipsis';
import Manage from './manage';
import ConfirmModal from '../../components/ConfirmModal';
import NoPermTip from '../../components/NoPermTip';
const ButtonGroup = Button.Group;


class MartketPlugin extends PureComponent {
  constructor(props){
      super(props);
      this.state = {
          pageSize:10,
          total:0,
          page:1,
          loading: false,
          plugins: []
      }
  }
  componentDidMount = () => {
      this.loadPlugins();
  }
  handleClose = () => {
      this.props.onClose && this.props.onClose();
  }
  handleSearch = (app_name) => {
      this.setState({
          app_name: app_name,
          page: 1
      }, () => {
          this.loadPlugins();
      })
  }
  loadPlugins = () => {
      this.setState({
          loading: true
      }, () => {
          this
              .props
              .dispatch({
                  type: 'plugin/getUnInstalledPlugin',
                  payload: {
                      plugin_name: this.state.app_name,
                      page: this.state.page,
                      pageSize: this.state.pageSize
                  },
                  callback: (data) => {
                      this.setState({
                          plugins: data.list || [],
                          loading: false,
                          total: data.total
                      })
                  }
              })
      })
  }
  handleInstall= (data) => {
      this
          .props
          .dispatch({
              type: 'plugin/installMarketPlugin',
              payload: {
                  plugin_id: data.id
              },
              callback: (data) => {
                  notification.success({message: '操作成功'});
                  this.loadPlugins();
                  this.props.onInstallSuccess && this.props.onInstallSuccess();
              }
          })
  }
  handlePageChange = (page) => {
      this.state.page = page;
      this.loadPlugins();
  }
  render(){
      const list = this.state.plugins || [];
      const paginationProps = {
          pageSize: this.state.pageSize,
          total: this.state.total,
          current: this.state.page,
          onChange: (pageSize) => {
              this.handlePageChange(pageSize)
          }
      };
      return <List
                rowKey="id"
                grid={{
                gutter: 24,
                lg: 2,
                md: 2,
                sm: 1,
                xs: 1
              }}
                dataSource={list}
                renderItem={item => ((
                  <List.Item
                    key={item.id}
                    >
                    <Card
          
                      className={styles.card}
                      actions={[item.is_installed ? <span>已安装</span> : <span onClick={()=>{this.handleInstall(item)}}>安装</span>]}>
                      <Card.Meta
                        style={{height: 99, overflow: 'hidden'}}
                        avatar={< Icon style = {{fontSize: 50, color:'rgba(0, 0, 0, 0.2)'}}type = "api" />}
                        title={item.plugin_name}
                        description={(
                        <Ellipsis className={styles.item} lines={3}>< p style={{ display: 'block',color:'rgb(220, 220, 220)', marginBottom:8}} > {
                          pluginUtil.getCategoryCN(item.category)
                        } < /p>{item.desc}</Ellipsis>
                      )}/>
                    </Card>
                  </List.Item>
                ))}/>
  }
}


@connect(({list, loading}) => ({}))
class PluginList extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {
      list: [],
      deletePlugin: null,
      downstream_net_plugin: null,
      perf_analyze_plugin: null,
      downstream_net_pluginData: {
          category: 'downstream_net_plugin',
          desc: '实现智能路由、A/B测试、灰度发布、端口复用等微服务治理功能',
          plugin_alias: '服务网络治理插件',
          hasInstall: false
      },
      perf_analyze_pluginData: {
        category: 'perf_analyze_plugin',
        desc: '实时分析应用的吞吐率、响应时间、在线人数等指标',
        plugin_alias: '服务实时性能分析',
        hasInstall: false
      },
      showMarketPlugin: false
    }
    this.timer = null;
  }
  componentDidMount() {
    this.fetchDefaultPlugin();
  }
  fetchDefaultPlugin = () => {
     this.props.dispatch({
       type: 'plugin/getDefaultPlugin',
       payload: {
         team_name: globalUtil.getCurrTeamName()
       },
       callback: ((data) => {
          this.state.downstream_net_plugin = data.bean.downstream_net_plugin;
          this.state.perf_analyze_plugin = data.bean.perf_analyze_plugin;
          this.fetchPlugins();
       })
     })
  }
  fetchPlugins = () => {
    this
      .props
      .dispatch({
        type: 'plugin/getMyPlugins',
        payload: {
          team_name: globalUtil.getCurrTeamName()
        },
        callback: ((data) => {
          var list = data.list || [];
          if(this.state.downstream_net_plugin === false){
            list.unshift(this.state.downstream_net_pluginData)
          }
          if(this.state.perf_analyze_plugin === false){
            list.unshift(this.state.perf_analyze_pluginData)
          }
          this.setState({
            list: data.list || []
          })
        })
      });
  }
  handleCreate = () => {
    this
      .props
      .dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/create-plugin`))
  }
  hanldeDeletePlugin = () => {
    this
    .props
    .dispatch({
      type: 'plugin/deletePlugin',
      payload: {
        team_name: globalUtil.getCurrTeamName(),
        plugin_id: this.state.deletePlugin.plugin_id
      },
      callback: ((data) => {
        this.fetchPlugins();
        this.cancelDeletePlugin();
      })
    });
  }
  onDeletePlugin = (plugin) => {
     this.setState({deletePlugin: plugin})
  }
  cancelDeletePlugin = () => {
    this.setState({deletePlugin: null})
  }
  onInstallPlugin = (item) => {
    this
    .props
    .dispatch({
      type: 'plugin/installDefaultPlugin',
      payload: {
        team_name: globalUtil.getCurrTeamName(),
        plugin_type: item.category
      },
      callback: ((data) => {
        this.fetchDefaultPlugin();
      })
    });
  }
  getItemTitle = (item) => {
    if(item.hasInstall !== false){
       return < Link to = {
        `/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/myplugns/${item.plugin_id}`
      } > {
        item.plugin_alias
      } < /Link>
    }else{
       return item.plugin_alias;
    }
  }
  getAction = (item) => {
    if(item.hasInstall !== false){
      return [<Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/myplugns/${item.plugin_id}`}>管理</Link>, <span onClick={()=>{this.onDeletePlugin(item)}}>删除</span>]
    }else{
      return [<span onClick={()=>{this.onInstallPlugin(item)}}>安装</span>]
    }
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
          <div style={{marginBottom:'10px',textAlign:'right'}}>
            <ButtonGroup>
              <Button onClick={this.handleCreate}><Icon type="plus" />新建插件</Button>
              {!this.state.showMarketPlugin && <Button onClick={() => {this.setState({showMarketPlugin: true})}}><Icon type="arrow-down" />从内部市场安装</Button>}
              {this.state.showMarketPlugin && <Button onClick={() => {this.setState({showMarketPlugin: false})}}><Icon type="close" />隐藏内部市场</Button>}
            </ButtonGroup>
          </div>
        <div  style={{display: this.state.showMarketPlugin ? 'flex' : 'block',position:'relative', overflow: 'hidden'}}>
            <div className={styles.cardList}
                style={{
                  marginTop: 14,
                  transition: 'all .8s',
                  width: this.state.showMarketPlugin ? '50%' : '100%',
                  display: 'inline-block'
              }}
            >
              <List
                rowKey="id"
                grid={this.state.showMarketPlugin ? {
                  gutter: 24,
                  lg: 2,
                  md: 2,
                  sm: 1,
                  xs: 1
                } : {
                gutter: 24,
                lg: 3,
                md: 2,
                sm: 1,
                xs: 1
              }}
                dataSource={list}
                renderItem={item => ((
                  <List.Item
                    key={item.id}
                    >
                    <Card
          
                      className={styles.card}
                      actions={this.getAction(item)}>
                      <Card.Meta
                        style={{height: 99, overflow: 'hidden'}}
                        avatar={< Icon style = {{fontSize: 50, color:'rgba(0, 0, 0, 0.2)'}}type = "api" />}
                        title={this.getItemTitle(item)}
                        description={(
                        <Ellipsis className={styles.item} lines={3}>< p style={{ display: 'block',color:'rgb(220, 220, 220)', marginBottom:8}} > {
                          pluginUtil.getCategoryCN(item.category)
                        } < /p>{item.desc}</Ellipsis>
                      )}/>
                    </Card>
                  </List.Item>
                ))}/>
            </div>

            <div className={styles.cardList} style={{
                    transition: 'all .8s',
                    transform: this.state.showMarketPlugin ? 'translate3d(0, 0, 0)' : 'translate3d(100%, 0, 0)',
                    marginLeft:8,
                    width: '49%'
                }}>
                {this.state.showMarketPlugin && <MartketPlugin dispatch={this.props.dispatch} />}
            </div>
        </div>
        
            {this.state.deletePlugin && <ConfirmModal
          onOk={this.hanldeDeletePlugin}
          onCancel={this.cancelDeletePlugin}
          title="删除插件"
          desc="确定要删除此插件吗？"/>}
        
        
      </PageHeaderLayout>
    );
  }
}

@connect(({user}) => ({currUser: user.currentUser}))
class Index extends PureComponent {
  render() {
    const currUser = this.props.currUser;
    const team_name = globalUtil.getCurrTeamName();
    const team = userUtil.getTeamByTeamName(currUser, team_name);
    if(!TeamUtil.canManagePlugin(team)){
       return <NoPermTip />
    }
    const pluginId = this.props.match.params.pluginId;
    if (pluginId) {
      return <Manage {...this.props}/>
    } else {
      return <PluginList {...this.props}/>
    }
  }
}
export default Index;
