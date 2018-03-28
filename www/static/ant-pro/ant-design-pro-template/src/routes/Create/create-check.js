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
import {getCreateCheckId, getCreateCheckResult, buildApp, getCheckuuid} from '../../services/createApp';
import globalUtil from '../../utils/global';
import CodeCustomForm from '../../components/CodeCustomForm';
import LogProcress from '../../components/LogProcress';
import userUtil from '../../utils/user';
import regionUtil from '../../utils/region';
import ShowRegionKey from '../../components/ShowRegionKey';
const {TextArea} = Input;

const formItemLayout = {
  labelCol: {
    span: 5
  },
  wrapperCol: {
    span: 19
  }
};

/* 修改镜像名称 */
@Form.create()
class ModifyImageName extends PureComponent {
  handleSubmit = (e) => {
    e.preventDefault();
    const form = this.props.form;
    form.validateFields((err, fieldsValue) => {
      if (err) 
        return;
      this.props.onSubmit && this
        .props
        .onSubmit(fieldsValue)
    });
  }
  render() {
    const {getFieldDecorator, getFieldValue} = this.props.form;
    const data = this.props.data || {};
    return (
      <Modal
        visible={true}
        title="修改镜像名称"
        onOk={this.handleSubmit}
        onCancel={this.props.onCancel}>
        <Form onSubmit={this.handleSubmit} layout="horizontal" hideRequiredMark>
          <Form.Item {...formItemLayout} label="镜像地址">
            {getFieldDecorator('docker_cmd', {
              initialValue: data.docker_cmd || '',
              rules: [
                {
                  required: true,
                  message: '请输入镜像名称'
                }
              ]
            })(<Input
              style={{
              width: 'calc(100% - 100px)'
            }}
              placeholder="请输入镜像名称, 如 nginx : 1.11"/>)}
          </Form.Item>
        </Form>
      </Modal>
    )
  }
}

/* 修改镜像命令 */
@Form.create()
class ModifyImageCmd extends PureComponent {
  handleSubmit = (e) => {
    e.preventDefault();
    const form = this.props.form;
    form.validateFields((err, fieldsValue) => {
      if (err) 
        return;
      this.props.onSubmit && this
        .props
        .onSubmit(fieldsValue)
    });
  }
  render() {
    const {getFieldDecorator, getFieldValue} = this.props.form;
    const data = this.props.data || {};
    return (
      <Modal
        visible={true}
        title="修改DockerRun命令"
        onOk={this.handleSubmit}
        onCancel={this.props.onCancel}>
        <Form onSubmit={this.handleSubmit} layout="horizontal" hideRequiredMark>
          <Form.Item {...formItemLayout} label="命令">
            {getFieldDecorator('docker_cmd', {
              initialValue: data.docker_cmd || '',
              rules: [
                {
                  required: true,
                  message: '请输入DockerRun命令'
                }
              ]
            })(<TextArea
              placeholder="例如： docker run -d -p 8080:8080 -e PWD=1qa2ws --name=tomcat_demo tomcat"/>)}
          </Form.Item>
        </Form>
      </Modal>
    )
  }
}

@Form.create()
class ModifyUrl extends PureComponent {

  constructor(props) {
    super(props);
  }
  handleCancel = () => {
    this.props.onCancel && this
      .props
      .onCancel();
  }
  handleSubmit = (e) => {
    e.preventDefault();
    const form = this.props.form;
    form.validateFields((err, fieldsValue) => {
      if (err) 
        return;
      this.props.onSubmit && this
        .props
        .onSubmit(fieldsValue)
    });
  }
  render() {
    const formItemLayout = {
      labelCol: {
        span: 5
      },
      wrapperCol: {
        span: 19
      }
    };
    const {getFieldDecorator, getFieldValue} = this.props.form;
    const data = this.props.data || {};
    const showUsernameAndPass = !!this.props.showUsernameAndPass;
    return <Modal
      title="信息修改"
      width={600}
      visible={true}
      onOk={this.handleSubmit}
      onCancel={this.handleCancel}>
      <Form onSubmit={this.handleSubmit} layout="horizontal" hideRequiredMark>
        <Form.Item {...formItemLayout} label="应用名称">
          {getFieldDecorator('service_cname', {
            initialValue: data.service_cname || '',
            rules: [
              {
                required: true,
                message: '要创建的应用还没有名字'
              }
            ]
          })(<Input disabled={true} placeholder="请为创建的应用起个名字吧"/>)}
        </Form.Item>
        <Form.Item {...formItemLayout} label="仓库地址">
          <Input.Group compact>
            {getFieldDecorator('git_url', {
              initialValue: data.git_url || '',
              rules: [
                {
                  required: true,
                  message: '请输入仓库地址'
                }, {
                  pattern: /^(.+@.+\.git)|([^@]+\.git(\?.+)?)$/gi,
                  message: '仓库地址不正确'
                }
              ]
            })(<Input
              style={{
              width: 'calc(100% - 100px)'
            }}
              placeholder="请输入仓库地址"/>)}
          </Input.Group>
        </Form.Item>
        <Form.Item
          style={{
          display: (showUsernameAndPass)
            ? ''
            : 'none'
        }}
          {...formItemLayout}
          label="仓库用户名">
          {getFieldDecorator('user_name', {
            initialValue: data.user_name || '',
            rules: [
              {
                required: false,
                message: '请输入仓库用户名'
              }
            ]
          })(<Input placeholder="请输入仓库用户名"/>)}
        </Form.Item>
        <Form.Item
          style={{
          display: (showUsernameAndPass)
            ? ''
            : 'none'
        }}
          {...formItemLayout}
          label="仓库密码">
          {getFieldDecorator('password', {
            initialValue: data.password || '',
            rules: [
              {
                required: false,
                message: '请输入仓库密码'
              }
            ]
          })(<Input type="password" placeholder="请输入仓库密码"/>)}
        </Form.Item>
      </Form>
    </Modal>
  }
}

@connect(({user, appControl}) => ({currUser: user.currentUser}))
export default class CreateCheck extends PureComponent {
  constructor(props) {
    super(props);
    this.state = {
      //failure、checking、success
      status: '',
      check_uuid: '',
      errorInfo: [],
      serviceInfo: [],
      showEdit: false,
      eventId: '',
      appDetail: {},
      showDelete: false,
      modifyUrl: false,
      modifyUserpass: false,
      modifyImageName: false,
      modifyImageCmd: false
    }
    this.mount = false;
    this.socketUrl = '';
    var teamName = globalUtil.getCurrTeamName();
    var regionName = globalUtil.getCurrRegionName();
    var region = userUtil.hasTeamAndRegion(this.props.currUser, teamName, regionName);
    if (region) {
      this.socketUrl = regionUtil.getEventWebSocketUrl(region);
    }

  }
  componentDidMount() {
    this.mount = true;
    this.getDetail();
    this.bindEvent();
  }
  getDetail = () => {
    this
      .props
      .dispatch({
        type: 'appControl/fetchDetail',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.getAppAlias()
        },
        callback: (appDetail) => {
          this.setState({appDetail: appDetail.service});
          this.getCheckuuid();
        }
      })
  }
  getCheckuuid = () => {
    const appAlias = this.getAppAlias();
    const team_name = globalUtil.getCurrTeamName();
    getCheckuuid({team_name: team_name, app_alias: appAlias}).then((data) => {
      if (data) {
        if (!data.bean.check_uuid) {
          this.startCheck();
        } else {
          this.state.check_uuid = data.bean.check_uuid;
          this.loopStatus();
        }
      }
    })
  }
  startCheck = (loopStatus) => {
    const appAlias = this.getAppAlias();
    const team_name = globalUtil.getCurrTeamName();
    var p = getCreateCheckId({
      team_name: team_name,
      app_alias: appAlias
    }, (res) => {
      if (res.status === 404) {
        this
          .props
          .dispatch(routerRedux.replace(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/exception/404`));
      }
    }).then((data) => {
      if (data) {
        this.state.check_uuid = data.bean.check_uuid;
        this.setState({eventId: data.bean.check_event_id, appDetail: data.bean})
        if (loopStatus !== false) {
          this.loopStatus();
        }
      }
    })
  }
  loopStatus = () => {
    if (!this.mount) 
      return;
    const appAlias = this.getAppAlias();
    const team_name = globalUtil.getCurrTeamName();
    getCreateCheckResult({team_name: team_name, app_alias: appAlias, check_uuid: this.state.check_uuid}).then((data) => {
      if (data && this.mount) {
        var status = data.bean.check_status;
        var error_infos = data.bean.error_infos || [];
        var serviceInfo = data.bean.service_info || [];
        this.setState({status: status, errorInfo: error_infos, serviceInfo: serviceInfo})
      }
    }). finally(() => {
      if (this.mount && this.state.status === 'checking') {
        setTimeout(() => {
          this.loopStatus();
        }, 5000)

      }
    })
  }
  componentWillUnmount() {
    this.mount = false;
    this.unbindEvent();

  }
  getAppAlias() {
    return this.props.match.params.appAlias;
  }
  handleCreate = () => {
    const appAlias = this.getAppAlias();
  }
  renderError = () => {
    const errorInfo = this.state.errorInfo;
    const extra = (
      <div>
        {errorInfo.map((item) => {
          return <div style={{
            marginBottom: 16
          }}>
            <Icon
              style={{
              color: '#f5222d',
              marginRight: 8
            }}
              type="close-circle-o"/>
            <span
              dangerouslySetInnerHTML={{
              __html: '<span>' + (item.error_info || '') + ' ' + (item.solve_advice || '') + '</span>'
            }}></span>
          </div>
        })
}
      </div>
    );
    const actions = [< Button onClick = {
        this.showDelete
      }
      type = "default" > 放弃创建 < /Button>, 
        <Button onClick={this.recheck} type="primary">重新检测</Button >];

    return <Result
      type="error"
      title="应用检测未通过"
      description="请核对并修改以下信息后，再重新检测。"
      extra={extra}
      actions={actions}
      style={{
      marginTop: 48,
      marginBottom: 16
    }}/>
  }
  handleSetting = () => {
    const appAlias = this.getAppAlias();
    this
      .props
      .dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/create/create-setting/${appAlias}`));
  }
  handleBuild = () => {
    const appAlias = this.getAppAlias();
    const team_name = globalUtil.getCurrTeamName();
    buildApp({team_name: team_name, app_alias: appAlias}).then((data) => {
      if (data) {
        const appAlias = this.getAppAlias();
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
          .dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/app/${appAlias}/overview`));

      }
    })
  }
  renderSuccessInfo = (item) => {
    if (typeof item.value === 'string') {
      return <div>
        <span
          style={{
          verticalAlign: 'top',
          display: 'inline-block',
          fontWeight: 'bold'
        }}>{item.key}：</span>{item.value}</div>
    } else {
      return <div>
        <span
          style={{
          verticalAlign: 'top',
          display: 'inline-block',
          fontWeight: 'bold'
        }}>{item.key}：</span>
        <div style={{
          display: 'inline-block'
        }}>
          {(item.value || []).map((item) => {
            return <p style={{
              marginBottom: 0
            }}>{item}</p>
          })
}
        </div>
      </div>
    }
  }
  renderSuccess = () => {
    const serviceInfo = this.state.serviceInfo;
    const extra = (
      <div>
        {serviceInfo.map((item) => {
          return <div style={{
            marginBottom: 16
          }}>
            {this.renderSuccessInfo(item)}
          </div>
        })
}
      </div>
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
              title="应用检测通过"
              description="请核对已下信息后开始构建。如信息有误，请点高级设置进行修改"
              extra={extra}
              actions={actions}
              style={{ marginTop: 48, marginBottom: 16 }}
            / >
    }
    renderChecking = () => {
      const actions = <Button onClick={this.showDelete} type="default">放弃创建</Button>;

      const extra = (
        <div>
          {this.state.eventId && <LogProcress socketUrl={this.socketUrl} eventId={this.state.eventId}/>
}
        </div>
      );
      return <Result
        type="ing"
        title="应用检测中..."
        extra={extra}
        description="此过程可能比较耗时，请耐心等待"
        actions={actions}
        style={{
        marginTop: 48,
        marginBottom: 16
      }}/>
    }
    recheck = () => {
      this.setState({
        status: 'checking'
      }, () => {
        this.startCheck();
      })
    }
    cancelModifyImageName = () => {
      this.setState({modifyImageName: false})
    }
    cancelModifyImageCmd = () => {
      this.setState({modifyImageCmd: false})
    }
    handleClick = (e) => {
      var parent = e.target;
      const appDetail = this.state.appDetail;

      while (parent) {
        if (parent === document.body) {
          return;
        }
        var actionType = parent.getAttribute('action_type');
        if (actionType === 'modify_url' || actionType === 'modify_repo') {
          this.setState({modifyUrl: actionType})
          return;
        }

        if (actionType === 'modify_userpass') {
          this.setState({modifyUserpass: true});
          return;
        }

        if (actionType === 'get_publickey') {
          this.setState({showKey: true})
          return;
        }

        if (actionType === 'open_repo') {
          if((appDetail.git_url|| "").indexOf('@') === -1){
            window.open(appDetail.git_url);
          }else{
            Modal.info({title: '仓库地址', content: appDetail.git_url});
          }
          
        }

        //修改镜像名称或dockerrun命令
        if (actionType === 'modify_image') {
          //指定镜像
          if (appDetail.service_source === 'docker_image') {

            this.setState({modifyImageName: true});
            return;
          }
          //docker_run命令
          if (appDetail.service_source === 'docker_run') {
            this.setState({modifyImageCmd: true});
            return;
          }
        }

        parent = parent.parentNode
      }
    }
    handleDelete = () => {
      const appAlias = this.getAppAlias();
      this
        .props
        .dispatch({
          type: 'appControl/deleteApp',
          payload: {
            team_name: globalUtil.getCurrTeamName(),
            app_alias: appAlias,
            is_force: true
          },
          callback: () => {
            this
              .props
              .dispatch(routerRedux.replace(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/index`))
          }
        })
    }
    cancelModifyUrl = () => {
      this.setState({modifyUrl: false})
    }
    handleCancelEdit = () => {
      this.setState({showEdit: false})
    }
    handleCancelShowKey = () => {
      this.setState({showKey: false})
    }
    bindEvent = () => {
      document.addEventListener('click', this.handleClick, false);
    }
    unbindEvent = () => {
      document.removeEventListener('click', this.handleClick);
    }
    cancelModifyUserpass = () => {
      this.setState({modifyUserpass: false})
    }
    handleModifyUserpass = (values) => {
      const appDetail = this.state.appDetail;
      this
        .props
        .dispatch({
          type: 'appControl/editAppCreateInfo',
          payload: {
            team_name: globalUtil.getCurrTeamName(),
            app_alias: appDetail.service_alias,
            user_name: values.user_name,
            password: values.password
          },
          callback: (data) => {
            if (data) {
              this.startCheck(false);
              this.cancelModifyUserpass();
            }
          }
        })
    }
    handleModifyUrl = (values) => {
      const appDetail = this.state.appDetail;
      this
        .props
        .dispatch({
          type: 'appControl/editAppCreateInfo',
          payload: {
            team_name: globalUtil.getCurrTeamName(),
            app_alias: appDetail.service_alias,
            git_url: values.git_url
          },
          callback: (data) => {
            if (data) {
              this.startCheck(false);
              this.handleCancelEdit();
            }
          }
        })
    }
    handleModifyImageName = (values) => {
      const appDetail = this.state.appDetail;
      this
        .props
        .dispatch({
          type: 'appControl/editAppCreateInfo',
          payload: {
            team_name: globalUtil.getCurrTeamName(),
            app_alias: appDetail.service_alias,
            docker_cmd: values.docker_cmd
          },
          callback: (data) => {
            if (data) {
              this.startCheck(false);
              this.cancelModifyImageName();
            }
          }
        })
    }
    handleModifyImageCmd = (values) => {
      const appDetail = this.state.appDetail;
      this
        .props
        .dispatch({
          type: 'appControl/editAppCreateInfo',
          payload: {
            team_name: globalUtil.getCurrTeamName(),
            app_alias: appDetail.service_alias,
            docker_cmd: values.docker_cmd
          },
          callback: (data) => {
            if (data) {
              this.cancelModifyImageCmd();
            }
          }
        })
    }
    handleImageSubmit = (values) => {}
    showDelete = () => {
      this.setState({showDelete: true})
    }

    renderEdit = () => {
      //判断应用创建方式
      const appDetail = this.state.appDetail;
      //源码创建
      if (appDetail.service_source === 'source_code') {
        //指定源码
        if (appDetail.code_from === 'gitlab_manual') {
          return <EditCreateCodeCustom
            data={appDetail}
            onSubmit={this.handleCodeSubmit}
            onCancel={this.handleCancelEdit}/>;
        }
        //源码demo
        if (appDetail.code_from === 'gitlab_demo') {}
        //好雨git仓库
        if (appDetail.code_from === 'gitlab_exit') {}
        //github项目
        if (appDetail.code_from === 'github') {}
      }

      //compose创建
      if (appDetail.service_source === 'docker_compose') {}
      return null;
    }
    render() {
      const status = this.state.status;
      const appDetail = this.state.appDetail;
      return <PageHeaderLayout>
        <Card bordered={false}>
          <div style={{
            minHeight: 400
          }}>
            {(status === 'checking')
              ? this.renderChecking()
              : null}
            {status === 'success'
              ? this.renderSuccess()
              : null}
            {status === 'failure'
              ? this.renderError()
              : null}
          </div>
        </Card>

        {this.state.modifyUrl
          ? <ModifyUrl
              data={appDetail}
              onSubmit={this.handleModifyUrl}
              onCancel={this.cancelModifyUrl}/>
          : null
}

        {this.state.modifyImageName
          ? <ModifyImageName
              data={{
              docker_cmd: appDetail.docker_cmd
            }}
              onSubmit={this.handleModifyImageName}
              onCancel={this.cancelModifyImageName}/>
          : null
}
        {this.state.modifyImageCmd
          ? <ModifyImageCmd
              data={{
              docker_cmd: appDetail.docker_cmd
            }}
              onSubmit={this.handleModifyImageCmd}
              onCancel={this.cancelModifyImageCmd}/>
          : null
}

        {this.state.modifyUserpass
          ? <ModifyUrl
              showUsernameAndPass={true}
              data={appDetail}
              onSubmit={this.handleModifyUserpass}
              onCancel={this.cancelModifyUserpass}/>
          : null
}
        {this.state.showKey
          ? <ShowRegionKey onCancel={this.handleCancelShowKey}/>
          : null}
        {this.state.showDelete && <ConfirmModal
          onOk={this.handleDelete}
          title="放弃创建"
          subDesc="此操作不可恢复"
          desc="确定要放弃创建此应用吗？"
          onCancel={() => {
          this.setState({showDelete: false})
        }}/>}
      </PageHeaderLayout>
    }
  }