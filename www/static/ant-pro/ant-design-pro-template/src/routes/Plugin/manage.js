import React, {PureComponent, Fragment} from 'react';
import {connect} from 'dva';
import {Link} from 'dva/router';
import {
  Row,
  Col,
  Card,
  Button,
  Icon,
  List,
  Form,
  Select,
  Table,
  Notification,
  Dropdown,
  Menu
} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import globalUtil from '../../utils/global';
import styles from './Index.less';
import CreatePluginForm from '../../components/CreatePluginForm';
import pluginUtil from '../../utils/plugin';
import AddOrEditConfig from '../../components/AddOrEditConfig';
import ConfirmModal from '../../components/ConfirmModal';
import BuildPluginVersion from '../../components/buildPluginVersion';
import ScrollerX from '../../components/ScrollerX';
const FormItem = Form.Item;
const Option = Select.Option;
const ButtonGroup = Button.Group;

@Form.create()
@connect(({list, loading}) => ({}))
export default class Index extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {
      currInfo: null,
      versions: [],
      currVersion: '',
      config: [],
      showAddConfig: false,
      showEditConfig: null,
      showDeleteVersion: false,
      showBuildLog: false,
      event_id: '',
      apps: []
    }
    this.mount = false;
  }
  componentDidMount() {
    this.mount = true;
    this.getVersions();
    this.getUsedApp();
  }
  componentWillUnmount() {
    this.mount = false;
  }
  getUsedApp = () => {
    this
      .props
      .dispatch({
        type: 'plugin/getUsedApp',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          plugin_id: this.getId()
        },
        callback: (data) => {
          this.setState({
            apps: data.list || []
          })
        }
      })
  }
  getVersions = () => {
    this
      .props
      .dispatch({
        type: 'plugin/getPluginVersions',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          plugin_id: this.getId()
        },
        callback: (data) => {
          this.setState({versions: data.list})
          if (!this.state.currVersion && data.list.length) {
            this.setState({
              currVersion: data.list[0].build_version
            }, () => {
              this.getPluginVersionInfo();
              this.getPluginVersionConfig();
            })
          }
        }
      })
  }
  getPluginVersionInfo = () => {
    if (!this.mount) 
      return;
    this
      .props
      .dispatch({
        type: 'plugin/getPluginVersionInfo',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          plugin_id: this.getId(),
          build_version: this.state.currVersion
        },
        callback: (data) => {
          this.setState({currInfo: data.bean});
          setTimeout(() => {
            this.getPluginVersionInfo();
          }, 5000)
        }
      })
  }
  getPluginVersionConfig = () => {
    this
      .props
      .dispatch({
        type: 'plugin/getPluginVersionConfig',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          plugin_id: this.getId(),
          build_version: this.state.currVersion
        },
        callback: (data) => {
          this.setState({config: data.list})
        }
      })
  }
  getId = () => {
    return this.props.match.params.pluginId;
  }
  handleSubmit = (val) => {
    alert(val)
    this
      .props
      .dispatch({
        type: 'plugin/createPlugin',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          ...val
        },
        callback: ((data) => {})
      })
  }
  handleVersionChange = (val) => {
    val = val.key;
    if (val === this.state.currVersion) 
      return;
    this.setState({
      currVersion: val
    }, () => {
      this.getPluginVersionInfo();
      this.getPluginVersionConfig();
    })
  }
  showAddConfig = () => {
    this.setState({showAddConfig: true})
  }
  hiddenAddConfig = () => {
    this.setState({showAddConfig: false})
  }
  hanldeEditSubmit = (values) => {
    this
      .props
      .dispatch({
        type: 'plugin/editPluginVersionInfo',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          plugin_id: this.getId(),
          build_version: this.state.currVersion,
          ...values
        },
        callback: (data) => {
          Notification.success({message: '修改成功'})
        }
      })
  }
  handleDelConfig = (config) => {
    this
      .props
      .dispatch({
        type: 'plugin/removePluginVersionConfig',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          plugin_id: this.getId(),
          build_version: this.state.currVersion,
          config_group_id: config.ID
        },
        callback: (data) => {
          this.getPluginVersionConfig();
        }
      })
  }
  handleAddConfig = (values) => {
    this
      .props
      .dispatch({
        type: 'plugin/addPluginVersionConfig',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          plugin_id: this.getId(),
          build_version: this.state.currVersion,
          entry: values
        },
        callback: (data) => {
          this.hiddenAddConfig();
          this.getPluginVersionConfig();
        }
      })
  }
  handleEditConfig = (values) => {
    this
      .props
      .dispatch({
        type: 'plugin/editPluginVersionConfig',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          plugin_id: this.getId(),
          build_version: this.state.currVersion,
          entry: {
            ...this.state.showEditConfig,
            ...values
          }
        },
        callback: (data) => {
          this.hideEditConfig();
          this.getPluginVersionConfig();
        }
      })
  }
  showEditConfig = (config) => {
    this.setState({showEditConfig: config})
  }
  hideEditConfig = (config) => {
    this.setState({showEditConfig: null})
  }
  showDeleteVersion = (config) => {
    this.setState({showDeleteVersion: true})
  }
  cancelDeleteVersion = (config) => {
    this.setState({showDeleteVersion: false})
  }
  handleDeleteVersion = () => {
    this
      .props
      .dispatch({
        type: 'plugin/removePluginVersion',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          plugin_id: this.getId(),
          build_version: this.state.currVersion
        },
        callback: (data) => {
          this.cancelDeleteVersion();
          this.state.currVersion = '';
          this.getVersions();
        }
      })
  }
  handleCreatePluginVersion = () => {
    this
      .props
      .dispatch({
        type: 'plugin/createPluginVersion',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          plugin_id: this.getId()
        },
        callback: (data) => {
          Notification.success({message: '操作成功'})
          this.state.currVersion = '';
          this.getVersions();
        }
      })
  }
  handleBuildPluginVersion = () => {
    this
      .props
      .dispatch({
        type: 'plugin/buildPluginVersion',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          plugin_id: this.getId(),
          build_version: this.state.currVersion
        },
        callback: (data) => {
          this.state.currVersion = '';
          this.setState({event_id: data.bean.event_id, showBuildLog: true});
          this.getVersions();
        }
      })
  }
  showBuildLog = () => {
    this.setState({showBuildLog: true})
  }
  hideBuildLog = () => {
    this.setState({showBuildLog: false})
  }
  canEditInfoAndConfig = () => {
    return !pluginUtil.isMarketPlugin(this.state.currInfo) && pluginUtil.canEditInfoAndConfig(this.state.currInfo)
  }
  render() {
    const versions = this.state.versions || [];
    const {form} = this.props;
    const {getFieldDecorator} = form;
    const config = this.state.config;
    const content = (
      <div className={styles.pageHeaderContent}></div>
    );

    if (!this.state.currInfo) 
      return null;
    
    const menu = (
      <Menu onClick={this.handleVersionChange}>
        {versions.map((version) => {
          return <Menu.Item key={version.build_version}>{version.build_version}</Menu.Item>
        })
}
      </Menu>
    );

    const action = (
      <div>
        {/* <ButtonGroup>
          <Dropdown overlay={menu} placement="bottomRight">
            <Button>当前版本：{this.state.currVersion}</Button>
          </Dropdown>
        </ButtonGroup> */}
        <ButtonGroup>
          {pluginUtil.canBuild(this.state.currInfo)
            ? <Button type="primary" onClick={this.handleBuildPluginVersion}>构建</Button>
            : null
}
          {(this.state.currInfo.build_status !== 'unbuild')
            ? <Button type="default" onClick={this.showBuildLog}>查看构建日志</Button>
            : null
}
          {/* <Button type="default" onClick={this.handleCreatePluginVersion}>创建新版本</Button> */}
          {/* <Button onClick={this.showDeleteVersion} type="default">删除当前版本</Button> */}
        </ButtonGroup>

      </div>
    );

    const formItemLayout = {};

    const extra = (
      <Row style={{
        float: 'right',
        width: 300
      }}>
        <Col xs={24} sm={12}>
          <div className={styles.textSecondary}></div>
          <div className={styles.heading}></div>
        </Col>
        <Col xs={24} sm={12}>
          <div className={styles.textSecondary}>构建状态</div>
          <div className={styles.heading}>{pluginUtil.getBuildStatusCN(this.state.currInfo.build_status)}</div>
        </Col>
      </Row>
    );

    return (
      <PageHeaderLayout
        title={this.state.currInfo.plugin_alias}
        content={this.state.currInfo.desc}
        extraContent={extra}
        action={action}>

        <Card style={{
          marginBottom: 16
        }} title="版本基础信息">
          <div
            style={{
            maxWidth: 500,
            margin: '0 auto'
          }}>
            <CreatePluginForm
              allDisabled={!this.canEditInfoAndConfig()}
              isEdit={true}
              onSubmit={this.hanldeEditSubmit}
              data={this.state.currInfo}
              submitText="确认修改"/>
          </div>
        </Card>

        <Card style={{
          marginBottom: 16
        }} title="配置组管理">
        <ScrollerX sm={700}>
          <Table
            columns={[
            {
              title: '配置项名',
              dataIndex: 'config_name'
            }, {
              title: '依赖元数据类型',
              dataIndex: 'service_meta_type',
              render: (v, data) => {
                return pluginUtil.getMetaTypeCN(v)
              }
            }, {
              title: '注入类型',
              dataIndex: 'injection',
              render: (v, data) => {
                return pluginUtil.getInjectionCN(v)
              }
            }, {
              title: '配置项',
              dataIndex: 'options',
              width: '40%',
              render: (v, data) => {
                return (v || []).map((item) => {
                  return <p className={styles.configGroup}>
                    <span>属性名: {item.attr_name}</span>
                    <span>属性类型: {item.attr_type}</span>
                    {item.attr_type !== 'string'
                      ? <span>可选值: {item.attr_alt_value}</span>
                      : null}
                    <span>可否修改: {item.is_change
                        ? '可修改'
                        : '不可修改'}</span>
                    <span>简短说明: {item.attr_info}</span>
                  </p>
                })
              }
            }, {
              title: '操作',
              dataIndex: 'action',
              render: (v, data) => {
                if (!this.canEditInfoAndConfig()) {
                  return null;
                }
                return (
                  <Fragment>
                    <a
                      href="javascript:;"
                      onClick={() => {
                      this.showEditConfig(data)
                    }}
                      style={{
                      marginRight: 8
                    }}>修改</a>
                    <a
                      href="javascript:;"
                      onClick={() => {
                      this.handleDelConfig(data)
                    }}>删除</a>
                  </Fragment>
                )
              }
            }
          ]}
            dataSource={config}
            pagination={false}/> 
            </ScrollerX>
            {this.canEditInfoAndConfig()
            ? <div
                style={{
                textAlign: 'right',
                paddingTop: 24
              }}>
                <Button onClick={this.showAddConfig}><Icon type="plus"/>新增配置</Button>
              </div>
            : null
}

        </Card>

        <Card title="已安装当前插件的应用">
          <Table
            columns={[
            {
              title: '应用名称',
              dataIndex: 'service_cname',
              render: (v, data) => {
                return <Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/app/${data.service_alias}/overview`}>{v}</Link>
              }
            }, {
              title: '安装版本',
              dataIndex: 'build_version'
            }, {
              title: '操作',
              dataIndex: 'action',
              render: (v, data) => {
                return <Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/app/${data.service_alias}/plugin`}>查看已安装插件</Link>
              }
            }
          ]}
            dataSource={this.state.apps}
            pagination={false}/>
        </Card>
        {this.state.showAddConfig && <AddOrEditConfig
          onCancel={this.hiddenAddConfig}
          onSubmit={this.handleAddConfig}/>}
        {this.state.showEditConfig && <AddOrEditConfig
          data={this.state.showEditConfig}
          onCancel={this.hideEditConfig}
          onSubmit={this.handleEditConfig}/>}
        {this.state.showDeleteVersion && <ConfirmModal
          onOk={this.handleDeleteVersion}
          onCancel={this.cancelDeleteVersion}
          title="删除版本"
          desc="确定要删除当前版本吗？"
          subDesc="此操作不可恢复"/>}
        {this.state.showBuildLog && this.state.currVersion && <BuildPluginVersion
          onCancel={this.hideBuildLog}
          event_id={this.state.event_id}
          plugin_id={this.getId()}
          build_version={this.state.currVersion}/>}
      </PageHeaderLayout>
    );
  }
}
