import React, {PureComponent, Fragment} from 'react';
import moment from 'moment';
import {connect} from 'dva';
import {Link, Switch, Route} from 'dva/router';
import {
  Row,
  Col,
  Card,
  Form,
  Button,
  Icon,
  Menu,
  Dropdown,
  Select,
  Radio,
  Table,
  Modal,
  Input,
  Tag
} from 'antd';
import {notification, Tooltip} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import {getRoutes} from '../../utils/utils';
import {getRouterData} from '../../common/router'
import DescriptionList from '../../components/DescriptionList';
import ConfirmModal from '../../components/ConfirmModal';
import KVinput from '../../components/KVinput';
import SetMemberAppAction from '../../components/SetMemberAppAction';
import {getCodeBranch, setCodeBranch} from '../../services/app';
import teamUtil from '../../utils/team';
import TeamPermissionSelect from '../../components/TeamPermissionSelect'

import styles from './Index.less';
import globalUtil from '../../utils/global';
import appProbeUtil from '../../utils/appProbe-util';
import appUtil from '../../utils/app';
const {Description} = DescriptionList;
const FormItem = Form.Item;
const Option = Select.Option;
const RadioGroup = Radio.Group;
const CheckableTag = Tag.CheckableTag;

@Form.create()
class EditActions extends PureComponent {
  handleSubmit = (e) => {
    e.preventDefault();
    const {form} = this.props;
    form.validateFields((err, fieldsValue) => {

      if (err) 
        return;
      this
        .props
        .onSubmit(fieldsValue)
    });
  }
  onCancel = () => {
    this
      .props
      .onCancel();
  }
  render() {
    const {getFieldDecorator} = this.props.form;
    const {actions, value} = this.props;

    return (
      <Modal
        title='编辑权限'
        visible={true}
        onOk={this.handleSubmit}
        onCancel={this.onCancel}>
        <Form onSubmit={this.handleSubmit}>

          <FormItem label="">
            {getFieldDecorator('identity', {
              initialValue: value,
              rules: [
                {
                  required: true,
                  message: '不能为空!'
                }
              ]
            })(<TeamPermissionSelect options={actions}/>)}
          </FormItem>

        </Form>
      </Modal>
    )
  }
}

//添加标签
class AddTag extends PureComponent {
  constructor(props) {
    super(props);
    this.state = {
      selected: {}
    }
  }
  handleOk = () => {
    var keys = Object.keys(this.state.selected);
    if (!keys.length) {
      notification.warning({message: '请选择要添加的标签'});
      return;
    }
    this.props.onOk && this
      .props
      .onOk(keys)
  }
  isCheck = (id) => {
    return !!this.state.selected[id];
  }
  handleChange = (id, checked) => {
    if (!checked) {
      delete this.state.selected[id];
    } else {
      this.state.selected[id] = true;
    }
    this.forceUpdate();
  }
  render() {
    const tags = this.props.tags || [];
    const onCancel = this.props.onCancel;
    return (
      <Modal title="点击标签进行选择" visible={true} onOk={this.handleOk} onCancel={onCancel}>
        {(!tags || !tags.length)
          ? <div style={{
              textAlign: 'center'
            }}>暂无可用标签</div>
          : tags.map((tag) => {
            return <CheckableTag
              onChange={(checked) => {
              this.handleChange(tag.label_id, checked)
            }}
              checked={this.isCheck(tag.label_id)}>{tag.label_alias}</CheckableTag>
          })
}
      </Modal>
    )
  }
}

//查看启动时健康监测
class ViewHealthCheck extends PureComponent {
  render() {
    const {title, onCancel} = this.props;
    const data = this.props.data || {};
    const formItemLayout = {
      labelCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 8
        }
      },
      wrapperCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 16
        }
      }
    };
    return (
      <Modal
        title={title}
        visible={true}
        onCancel={onCancel}
        footer={[ < Button onClick = {
          onCancel
        } > 关闭 < /Button> ]}>
        <Form>
          <FormItem {...formItemLayout} label="监测端口">
            <span>{data.port}</span>
          </FormItem>
          <FormItem {...formItemLayout} label="探针使用协议">
            <span>{data.scheme}</span>
          </FormItem>
          {data.scheme === 'http'
            ? <Fragment>
                <FormItem {...formItemLayout} label="http请求头">
                  <span>{appProbeUtil.getHeaders(data)}</span>
                </FormItem>
                <FormItem {...formItemLayout} label="路径">
                  <span>{appProbeUtil.getPath(data)}</span>
                </FormItem>
              </Fragment>
            : null
}

          <FormItem {...formItemLayout} label="初始化等候时间">
            <span>{appProbeUtil.getInitWaitTime(data)}
              <span style={{
                marginLeft: 8
              }}>秒</span>
            </span>
          </FormItem>
          <FormItem {...formItemLayout} label="检测监测时间">
            <span>{appProbeUtil.getIntervalTime(data)}
              <span style={{
                marginLeft: 8
              }}>秒</span>
            </span>
          </FormItem>
          <FormItem {...formItemLayout} label="检测超时时间">
            <span>{appProbeUtil.getTimeoutTime(data)}
              <span style={{
                marginLeft: 8
              }}>秒</span>
            </span>
          </FormItem>
          <FormItem {...formItemLayout} label="连续成功次数">
            <span>{appProbeUtil.getSuccessTimes(data)}</span>
          </FormItem>
        </Form>
      </Modal>
    )
  }
}

//查看运行时健康监测
class ViewRunHealthCheck extends PureComponent {
  render() {
    const {title, onCancel} = this.props;
    const data = this.props.data || {};
    const formItemLayout = {
      labelCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 8
        }
      },
      wrapperCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 16
        }
      }
    };
    return (
      <Modal
        title={title}
        visible={true}
        onCancel={onCancel}
        footer={[ < Button onClick = {
          onCancel
        } > 关闭 < /Button> ]}>
        <Form>
          <FormItem {...formItemLayout} label="监测端口">
            <span>{appProbeUtil.getPort(data)}</span>
          </FormItem>
          <FormItem {...formItemLayout} label="探针使用协议">
            <span>{appProbeUtil.getProtocol(data)}</span>
          </FormItem>
          {data.scheme === 'http'
            ? <Fragment>
                <FormItem {...formItemLayout} label="http请求头">
                  <span>{appProbeUtil.getHeaders(data)}</span>
                </FormItem>
                <FormItem {...formItemLayout} label="路径">
                  <span>{appProbeUtil.getPath(data)}</span>
                </FormItem>
              </Fragment>
            : null
}
          <FormItem {...formItemLayout} label="初始化等候时间">
            <span>{appProbeUtil.getInitWaitTime(data)}
              <span style={{
                marginLeft: 8
              }}>秒</span>
            </span>
          </FormItem>
          <FormItem {...formItemLayout} label="检测监测时间">
            <span>{appProbeUtil.getIntervalTime(data)}
              <span style={{
                marginLeft: 8
              }}>秒</span>
            </span>
          </FormItem>
          <FormItem {...formItemLayout} label="检测超时时间">
            <span>{appProbeUtil.getTimeoutTime(data)}
              <span style={{
                marginLeft: 8
              }}>秒</span>
            </span>
          </FormItem>
          <FormItem {...formItemLayout} label="连续错误次数">
            <span>{appProbeUtil.getFailTimes(data)}</span>
          </FormItem>
        </Form>
      </Modal>
    )
  }
}

//设置、编辑健康监测
@Form.create()
class EditHealthCheck extends PureComponent {

  handleSubmit = (e) => {
    e.preventDefault();
    this
      .props
      .form
      .validateFields({
        force: true
      }, (err, vals) => {
        if (!err) {
          this.props.onOk && this
            .props
            .onOk(vals)
        }
      })
  }
  checkPath = (rule, value, callback) => {
    var visitType = this
      .props
      .form
      .getFieldValue("scheme");
    if (visitType == 'tcp') {
      callback();
      return;
    }

    if (visitType != 'tcp' && value) {
      callback();
      return;
    }
    callback('请填写路径!');
  }
  render() {
    const {title, onCancel, onOk, ports} = this.props;
    const data = this.props.data || {};
    const formItemLayout = {
      labelCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 6
        }
      },
      wrapperCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 16
        }
      }
    };
    const {getFieldDecorator, getFieldValue} = this.props.form;
    const scheme = getFieldValue('scheme') || 'tcp';
    return (
      <Modal
        width={700}
        title={title}
        onOk={this.handleSubmit}
        onCancel={onCancel}
        visible={true}>
        <Form onSubmit={this.handleSubmit}>
          <FormItem {...formItemLayout} label="检测端口">
            {getFieldDecorator('port', {
              initialValue: appProbeUtil.getPort(data) || (ports.length
                ? ports[0].container_port
                : '')
            })(
              <Select>
                {ports.map((port) => {
                  return <Option value={port.container_port}>{port.container_port}</Option>;
                })
}
              </Select>
            )
}
          </FormItem>
          <FormItem {...formItemLayout} label="探针协议">
            {getFieldDecorator('scheme', {
              initialValue: data.scheme || 'tcp'
            })(<RadioGroup
              options={[
              {
                label: 'tcp',
                value: 'tcp'
              }, {
                label: 'http',
                value: 'http'
              }
            ]}/>)
}
          </FormItem>
          <FormItem
            {...formItemLayout}
            label="http请求头"
            style={{
            display: scheme === 'tcp'
              ? 'none'
              : ''
          }}>
            {getFieldDecorator('http_header', {
              initialValue: data.http_header || ''
            })(<KVinput/>)
}
          </FormItem>
          <FormItem
            {...formItemLayout}
            label="路径"
            style={{
            display: scheme === 'tcp'
              ? 'none'
              : ''
          }}>
            {getFieldDecorator('path', {
              initialValue: data.path || '',
              rules: [
                {
                  validator: this.checkPath
                }
              ]
            })(<Input placeholder="响应码2xx、3xx为正常"/>)
}
          </FormItem>
          <FormItem {...formItemLayout} label="初始化等候时间">
            {getFieldDecorator('initial_delay_second', {
              initialValue: data.initial_delay_second || '2',
              rules: [
                {
                  required: true,
                  message: '请填写初始化等候时间'
                }
              ]
            })(<Input type="number" style={{
              width: '80%'
            }}/>)
}
            <span style={{
              marginLeft: 8
            }}>秒</span>
          </FormItem>
          <FormItem {...formItemLayout} label="检测间隔时间">
            {getFieldDecorator('period_second', {
              initialValue: data.period_second || '3',
              rules: [
                {
                  required: true,
                  message: '请填写检测间隔时间'
                }
              ]
            })(<Input type="number" style={{
              width: '80%'
            }}/>)
}
            <span style={{
              marginLeft: 8
            }}>秒</span>
          </FormItem>
          <FormItem {...formItemLayout} label="检测超时时间">
            {getFieldDecorator('timeout_second', {
              initialValue: data.timeout_second || '20',
              rules: [
                {
                  required: true,
                  message: '请填写检测超时时间'
                }
              ]
            })(<Input type="number" style={{
              width: '80%'
            }}/>)
}
            <span style={{
              marginLeft: 8
            }}>秒</span>
          </FormItem>
          <FormItem {...formItemLayout} label="连续成功次数">
            {getFieldDecorator('success_threshold', {
              initialValue: data.success_threshold || '1',
              rules: [
                {
                  required: true,
                  message: '请填写连续成功次数'
                }
              ]
            })(<Input type="number" style={{
              width: '80%'
            }}/>)
}
          </FormItem>
        </Form>
      </Modal>
    )
  }
}

//设置、编辑运行时健康监测
@Form.create()
class EditRunHealthCheck extends PureComponent {

  handleSubmit = (e) => {
    e.preventDefault();
    this
      .props
      .form
      .validateFields({
        force: true
      }, (err, vals) => {
        if (!err) {
          this.props.onOk && this
            .props
            .onOk(vals)
        }
      })
  }
  checkPath = (rule, value, callback) => {
    var visitType = this
      .props
      .form
      .getFieldValue("scheme");
    if (visitType == 'tcp') {
      callback();
      return;
    }

    if (visitType != 'tcp' && value) {
      callback();
      return;
    }

    callback('请填写路径!');
  }
  render() {
    const {title, onCancel, onOk, ports} = this.props;
    const data = this.props.data || {};
    const formItemLayout = {
      labelCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 6
        }
      },
      wrapperCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 16
        }
      }
    };
    const {getFieldDecorator, getFieldValue} = this.props.form;
    const scheme = getFieldValue('scheme') || 'tcp';
    return (
      <Modal
        width={700}
        title={title}
        onOk={this.handleSubmit}
        onCancel={onCancel}
        visible={true}>
        <Form onSubmit={this.handleSubmit}>
          <FormItem {...formItemLayout} label="检测端口">
            {getFieldDecorator('port', {
              initialValue: appProbeUtil.getPort(data) || (ports.length
                ? ports[0].container_port
                : '')
            })(
              <Select>
                {ports.map((port) => {
                  return <Option value={port.container_port}>{port.container_port}</Option>;
                })
}
              </Select>
            )
}
          </FormItem>
          <FormItem {...formItemLayout} label="探针协议">
            {getFieldDecorator('scheme', {
              initialValue: data.scheme || 'tcp'
            })(<RadioGroup
              options={[
              {
                label: 'tcp',
                value: 'tcp'
              }, {
                label: 'http',
                value: 'http'
              }
            ]}/>)
}
          </FormItem>
          <FormItem
            {...formItemLayout}
            label="http请求头"
            style={{
            display: scheme === 'tcp'
              ? 'none'
              : ''
          }}>
            {getFieldDecorator('http_header', {
              initialValue: data.http_header || ''
            })(<KVinput/>)
}
          </FormItem>
          <FormItem
            {...formItemLayout}
            label="路径"
            style={{
            display: scheme === 'tcp'
              ? 'none'
              : ''
          }}>
            {getFieldDecorator('path', {
              initialValue: data.path || '',
              rules: [
                {
                  validator: this.checkPath
                }
              ]
            })(<Input placeholder="响应码2xx、3xx为正常"/>)
}
          </FormItem>
          <FormItem {...formItemLayout} label="初始化等候时间">
            {getFieldDecorator('initial_delay_second', {
              initialValue: data.initial_delay_second || '20',
              rules: [
                {
                  required: true,
                  message: '请填写初始化等候时间'
                }
              ]
            })(<Input type="number" style={{
              width: '80%'
            }}/>)
}
            <span style={{
              marginLeft: 8
            }}>秒</span>
          </FormItem>
          <FormItem {...formItemLayout} label="检测间隔时间">
            {getFieldDecorator('period_second', {
              initialValue: data.period_second || '3',
              rules: [
                {
                  required: true,
                  message: '请填写检测间隔时间'
                }
              ]
            })(<Input type="number" style={{
              width: '80%'
            }}/>)
}
            <span style={{
              marginLeft: 8
            }}>秒</span>
          </FormItem>
          <FormItem {...formItemLayout} label="检测超时时间">
            {getFieldDecorator('timeout_second', {
              initialValue: data.timeout_second || '20',
              rules: [
                {
                  required: true,
                  message: '请填写检测超时时间'
                }
              ]
            })(<Input type="number" style={{
              width: '80%'
            }}/>)
}
            <span style={{
              marginLeft: 8
            }}>秒</span>
          </FormItem>
          <FormItem {...formItemLayout} label="连续错误次数">
            {getFieldDecorator('failure_threshold', {
              initialValue: data.failure_threshold || '3',
              rules: [
                {
                  required: true,
                  message: '请填写连续错误次数'
                }
              ]
            })(<Input type="number" style={{
              width: '80%'
            }}/>)
}
          </FormItem>
        </Form>
      </Modal>
    )
  }
}

//添加、编辑变量
@Form.create()
class AddVarModal extends PureComponent {
  handleSubmit = (e) => {
    e.preventDefault();
    this
      .props
      .form
      .validateFields((err, values) => {
        if (!err) {
          this.props.onSubmit && this
            .props
            .onSubmit(values);
        }
      });
  }
  handleCancel = () => {
    this.props.onCancel && this
      .props
      .onCancel();
  }
  render() {
    const {getFieldDecorator} = this.props.form;
    const data = this.props.data || {};
    const formItemLayout = {
      labelCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 6
        }
      },
      wrapperCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 16
        }
      }
    };
    return (
      <Modal
        title="添加变量"
        onOk={this.handleSubmit}
        onCancel={this.handleCancel}
        visible={true}>
        <Form onSubmit={this.handleSubmit}>
          <FormItem {...formItemLayout} label="变量名">
            {getFieldDecorator('attr_name', {
              initialValue: data.attr_name || '',
              rules: [
                {
                  required: true,
                  message: '请输入变量名称'
                }, {
                  pattern: /^[A-Z][A-Z0-9_]*$/,
                  message: '格式不正确， /^[A-Z][A-Z0-9_]*$/'
                }
              ]
            })(<Input disabled={!!data.attr_name} placeholder="请输入变量名称 格式/^[A-Z][A-Z0-9_]*$/"/>)}
          </FormItem>
          <FormItem {...formItemLayout} label="变量值">
            {getFieldDecorator('attr_value', {
              initialValue: data.attr_value || '',
              rules: [
                {
                  required: true,
                  message: '请输入变量值'
                }
              ]
            })(<Input placeholder="请输入变量值"/>)}
          </FormItem>
          <FormItem {...formItemLayout} label="说明">
            {getFieldDecorator('name', {
              initialValue: data.name || '',
              rules: [
                {
                  required: true,
                  message: '请输入变量说明'
                }
              ]
            })(<Input placeholder="请输入变量说明"/>)}
          </FormItem>
        </Form>
      </Modal>
    )
  }
}

//切换分支组件
class ChangeBranch extends PureComponent {
  constructor(props) {
    super(props);
    this.state = {
      branch: this.props.branch || [],
      curr: ''
    }
  }
  componentDidMount() {
    this.loadBranch();
  }
  loadBranch() {
    getCodeBranch({
      team_name: globalUtil.getCurrTeamName(),
      app_alias: this.props.appAlias
    }).then((data) => {
      if (data) {
        this.setState({branch: data.list, curr: data.bean.current_version});
      }
    })
  }
  handleChange = (val) => {
    this.setState({curr: val})
  }
  handleSubmit = () => {
    const curr = this.state.curr;
    if (curr) {
      setCodeBranch({
        team_name: globalUtil.getCurrTeamName(),
        app_alias: this.props.appAlias,
        branch: curr
      }).then((data) => {
        if (data) {
          notification.success({message: `操作成功，重新部署后生效`});
        }
      })
    }
  }
  render() {
    const branch = this.state.branch;

    const formItemLayout = {
      labelCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 3
        }
      },
      wrapperCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 16
        }
      }
    };
    if (branch.length === 1) {
      return (
        <FormItem {...formItemLayout} label="代码分支">
          {branch[0]}
        </FormItem>
      )
    }
    return (

      <FormItem {...formItemLayout} label="代码分支">
        <Select
          onChange={this.handleChange}
          value={this.state.curr}
          style={{
          width: 120
        }}>
          {branch.map((item) => {
            return <Option value={item}>{item}</Option>
          })
}
        </Select>
        <Button
          onClick={this.handleSubmit}
          style={{
          marginLeft: 10
        }}
          type="primary">确定</Button>
      </FormItem>
    )

  }
}

@connect(({user, appControl, teamControl}) => ({
  currUser: user.currentUser,
  innerEnvs: appControl.innerEnvs,
  startProbe: appControl.startProbe,
  runningProbe: appControl.runningProbe,
  ports: appControl.ports,
  baseInfo: appControl.baseInfo,
  tags: appControl.tags,
  teamControl,
  members: appControl.members
}), null, null, {withRef: true})
export default class Index extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {
      showAddVar: false,
      showEditVar: null,
      deleteVar: null,
      viewStartHealth: null,
      editStartHealth: null,
      viewRunHealth: null,
      editRunHealth: null,
      addTag: false,
      showAddMember: false,
      toEditAction: null,
      toDeleteMember: null
    }
  }
  componentDidMount() {
    const {dispatch} = this.props;
    this
      .props
      .dispatch({type: 'teamControl/fetchAllPerm'})
    this.fetchInnerEnvs();
    this.fetchStartProbe();
    this.fetchRunningProbe();
    this.fetchPorts();
    this.fetchBaseInfo();
    this.fetchTags();
    this.loadMembers();
  }
  componentWillUnmount() {
    const {dispatch} = this.props;
    dispatch({type: 'appControl/clearTags'})
    dispatch({type: 'appControl/clearPorts'})
    dispatch({type: 'appControl/clearInnerEnvs'})
    dispatch({type: 'appControl/clearStartProbe'})
    dispatch({type: 'appControl/clearRunningProbe'})
    dispatch({type: 'appControl/clearMembers'})
  }
  fetchBaseInfo = () => {
    const {dispatch} = this.props;
    dispatch({
      type: 'appControl/fetchBaseInfo',
      payload: {
        team_name: globalUtil.getCurrTeamName(),
        app_alias: this.props.appAlias
      }
    })
  }
  fetchPorts = () => {
    const {dispatch} = this.props;
    dispatch({
      type: 'appControl/fetchPorts',
      payload: {
        team_name: globalUtil.getCurrTeamName(),
        app_alias: this.props.appAlias
      }
    })
  }
  fetchTags = () => {
    const {dispatch} = this.props;
    dispatch({
      type: 'appControl/fetchTags',
      payload: {
        team_name: globalUtil.getCurrTeamName(),
        app_alias: this.props.appAlias
      }
    })
  }
  fetchInnerEnvs = () => {
    this
      .props
      .dispatch({
        type: 'appControl/fetchInnerEnvs',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias
        }
      })
  }
  fetchStartProbe() {
    this
      .props
      .dispatch({
        type: 'appControl/fetchStartProbe',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias
        }
      })
  }
  fetchRunningProbe() {
    this
      .props
      .dispatch({
        type: 'appControl/fetchRunningProbe',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias
        },
        callback: (data, code) => {
          console.log(code)
        }
      })
  }
  loadMembers = () => {
    const {dispatch} = this.props;
    const team_name = globalUtil.getCurrTeamName();
    dispatch({
      type: 'appControl/fetchMember',
      payload: {
        team_name: team_name,
        app_alias: this.props.appAlias
      }
    })
  }
  showAddMember = () => {
    this.setState({showAddMember: true})
  }
  hideAddMember = () => {
    this.setState({showAddMember: false})
  }
  handleAddMember = (values) => {

    this
      .props
      .dispatch({
        type: 'appControl/setMemberAction',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          ...values
        },
        callback: () => {
          this.loadMembers();
          this.hideAddMember();
        }
      })
  }
  handleAddVar = () => {
    this.setState({showAddVar: true})
  }
  handleCancelAddVar = () => {
    this.setState({showAddVar: false})
  }
  handleSubmitAddVar = (vals) => {
    this
      .props
      .dispatch({
        type: 'appControl/addInnerEnvs',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          attr_name: vals.attr_name,
          attr_value: vals.attr_value,
          name: vals.name
        },
        callback: () => {
          this.handleCancelAddVar();
          this.fetchInnerEnvs();
        }
      })
  }
  onDeleteVar = (data) => {
    this.setState({deleteVar: data});
  }
  cancelDeleteVar = () => {
    this.setState({deleteVar: null});
  }
  handleDeleteVar = () => {
    this
      .props
      .dispatch({
        type: 'appControl/deleteEnvs',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          attr_name: this.state.deleteVar.attr_name
        },
        callback: () => {
          this.cancelDeleteVar();
          this.fetchInnerEnvs();
        }
      })
  }
  onEditVar = (data) => {
    this.setState({showEditVar: data});
  }
  cancelEditVar = () => {
    this.setState({showEditVar: null});
  }
  handleEditVar = (vals) => {
    this
      .props
      .dispatch({
        type: 'appControl/editEvns',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          attr_name: vals.attr_name,
          attr_value: vals.attr_value,
          name: vals.name
        },
        callback: () => {
          this.cancelEditVar();
          this.fetchInnerEnvs();
        }
      })
  }
  handleStartProbeStart = (isUsed) => {

    const {startProbe, runningProbe} = this.props;
    this
      .props
      .dispatch({
        type: 'appControl/editStartProbe',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          ...startProbe,
          is_used: isUsed
        },
        callback: () => {
          this.fetchStartProbe();
        }
      })
  }
  handleRunProbeStart = (isUsed) => {
    const {runningProbe} = this.props;
    this
      .props
      .dispatch({
        type: 'appControl/editRunProbe',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          ...runningProbe,
          is_used: isUsed
        },
        callback: () => {
          this.fetchRunningProbe();
        }
      })
  }
  handleEditHealth = (vals) => {

    if (appProbeUtil.isStartProbeUsed(this.state.editStartHealth)) {
      this
        .props
        .dispatch({
          type: 'appControl/editStartProbe',
          payload: {
            team_name: globalUtil.getCurrTeamName(),
            app_alias: this.props.appAlias,
            ...vals
          },
          callback: () => {
            this.onCancelEditStartProbe();
            this.fetchStartProbe();
          }
        })
    } else {
      this
        .props
        .dispatch({
          type: 'appControl/addStartProbe',
          payload: {
            team_name: globalUtil.getCurrTeamName(),
            app_alias: this.props.appAlias,
            ...vals
          },
          callback: () => {
            this.onCancelEditStartProbe();
            this.fetchStartProbe();
          }
        })
    }
  }
  handleEditRunHealth = (vals) => {
    if (appProbeUtil.isRunningProbeUsed(this.state.editRunHealth)) {
      this
        .props
        .dispatch({
          type: 'appControl/editRunProbe',
          payload: {
            team_name: globalUtil.getCurrTeamName(),
            app_alias: this.props.appAlias,
            ...vals
          },
          callback: () => {
            this.onCancelEditRunProbe();
            this.fetchRunningProbe();
          }
        })
    } else {
      this
        .props
        .dispatch({
          type: 'appControl/addRunProbe',
          payload: {
            team_name: globalUtil.getCurrTeamName(),
            app_alias: this.props.appAlias,
            ...vals
          },
          callback: () => {
            this.onCancelEditRunProbe();
            this.fetchRunningProbe();
          }
        })
    }

  }
  showViewStartHealth = (data) => {
    this.setState({viewStartHealth: data});
  }
  hiddenViewStartHealth = (data) => {
    this.setState({viewStartHealth: null});
  }
  showViewRunningHealth = (data) => {
    this.setState({viewRunHealth: data});
  }
  hiddenViewRunningHealth = (data) => {
    this.setState({viewRunHealth: null});
  }
  onCancelEditStartProbe = () => {
    this.setState({editStartHealth: null});
  }
  onCancelEditRunProbe = () => {
    this.setState({editRunHealth: null});
  }
  handleRemoveTag = (tag) => {
    this
      .props
      .dispatch({
        type: 'appControl/deleteTag',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          label_id: tag.label_id
        },
        callback: () => {
          notification.success({message: '删除成功'});
          this.fetchTags();
        }
      })
  }
  onAddTag = () => {
    this.setState({addTag: true})
  }
  cancelAddTag = () => {
    this.setState({addTag: false})
  }
  handleAddTag = (tags) => {
    console.log(tags);
    this
      .props
      .dispatch({
        type: 'appControl/addTag',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          tags: tags
        },
        callback: () => {
          this.cancelAddTag();
          notification.success({message: '添加成功'});
          this.fetchTags();
        }
      })
  }
  onEditAction = (member) => {
    this.setState({toEditAction: member})
  }
  hideEditAction = () => {
    this.setState({toEditAction: null})
  }
  handleEditAction = ({identity}) => {
    const team_name = globalUtil.getCurrTeamName();
    this
      .props
      .dispatch({
        type: 'appControl/editMemberAction',
        payload: {
          team_name: team_name,
          user_id: this.state.toEditAction.user_id,
          app_alias: this.props.appAlias,
          identity: identity
        },
        callback: () => {
          this.loadMembers();
          this.hideEditAction();
        }
      })
  }
  onDelMember = (member) => {

    this.setState({toDeleteMember: member})
  }
  hideDelMember = () => {
    this.setState({toDeleteMember: null})
  }
  handleDelMember = () => {
    const team_name = globalUtil.getCurrTeamName();
    this
      .props
      .dispatch({
        type: 'appControl/deleteMember',
        payload: {
          team_name: team_name,
          app_alias: this.props.appAlias,
          user_id: this.state.toDeleteMember.user_id
        },
        callback: () => {
          this.loadMembers();
          this.hideDelMember();
        }
      })
  }
  render() {
    var self = this;
    const formItemLayout = {
      labelCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 3
        }
      },
      wrapperCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 16
        }
      }
    };

    const {
      innerEnvs,
      runningProbe,
      startProbe,
      ports,
      baseInfo,
      appDetail,
      tags,
      teamControl
    } = this.props;
    const members = this.props.members || [];
    return (
      <Fragment>
        <Card style={{
          marginBottom: 24
        }} title="基础信息">
          <Form>
            {appUtil.isImageApp(appDetail)
              ? <FormItem
                  style={{
                  marginBottom: 0
                }}
                  {...formItemLayout}
                  label="镜像名称">
                  {appDetail.service.image}
                </FormItem>
              : ''
}
            <FormItem
              style={{
              marginBottom: 0
            }}
              {...formItemLayout}
              label="创建时间">
              {baseInfo.create_time || ''}
            </FormItem>
            {tags
              ? <FormItem
                  style={{
                  marginBottom: 0
                }}
                  {...formItemLayout}
                  label="应用特性">
                  {(tags.used_labels || []).map((tag) => {
                    return <Tag
                      closable
                      onClose={(e) => {
                      e.preventDefault();
                      this.handleRemoveTag(tag)
                    }}>{tag.label_alias}</Tag>
                  })
}
                  <Button onClick={this.onAddTag} size="small">添加特性</Button>
                </FormItem>
              : ''
}

            {baseInfo.git_url
              ? <Fragment>
                  <FormItem
                    style={{
                    marginBottom: 0
                  }}
                    {...formItemLayout}
                    label="Git仓库">
                    <a href={baseInfo.git_url} target="_blank">{baseInfo.git_url}</a>
                  </FormItem>
                  <ChangeBranch appAlias={this.props.appAlias}/>
                </Fragment>
              : ''
}

          </Form>
        </Card>

        <Card style={{
          marginBottom: 24
        }} title="自定义环境变量">
          <Table
            columns={[
            {
              title: '变量名',
              dataIndex: 'attr_name'
            }, {
              title: '变量值',
              dataIndex: 'attr_value'
            }, {
              title: '说明',
              dataIndex: 'name'
            }, {
              title: '操作',
              dataIndex: 'action',
              render: (val, data) => {
                return (
                  <Fragment>
                    <a
                      href="javascript:;"
                      onClick={() => {
                      this.onDeleteVar(data)
                    }}>删除</a>
                    {data.is_change
                      ? <a
                          href="javascript:;"
                          onClick={() => {
                          this.onEditVar(data)
                        }}>修改</a>
                      : ''}
                  </Fragment>
                )
              }
            }
          ]}
            pagination={false}
            dataSource={innerEnvs}/>
          <div
            style={{
            textAlign: 'right',
            paddingTop: 20
          }}>
            <Button onClick={this.handleAddVar}><Icon type="plus"/>添加变量</Button>
          </div>
        </Card>
        <Card style={{
          marginBottom: 24
        }} title="健康监测">
          <Table
            columns={[
            {
              title: '监测类型',
              dataIndex: 'type',
              render: (val, data, index) => {
                if (index === 0) {
                  return '启动时检测'
                }
                if (index === 1) {
                  return '运行时检测'
                }
              }
            }, {
              title: '状态',
              dataIndex: 'status',
              render: (val, data, index) => {
                if (index === 0) {
                  if (appProbeUtil.isStartProbeUsed(data)) {
                    if (appProbeUtil.isStartProbeStart(data)) {
                      return '已启用'
                    } else {
                      return '已禁用'
                    }
                  } else {
                    return '未设置'
                  }
                }
                if (index === 1) {
                  if (appProbeUtil.isRunningProbeUsed(data)) {
                    if (appProbeUtil.isRunningProbeStart(data)) {
                      return '已启用'
                    } else {
                      return '已禁用'
                    }
                  } else {
                    return '未设置'
                  }
                }
              }
            }, {
              title: '操作',
              dataIndex: 'action',
              render: (val, data, index) => {
                if (index === 0) {
                  if (appProbeUtil.isStartProbeUsed(data)) {
                    return (
                      <Fragment>
                        <a
                          href="javascript:;"
                          onClick={() => {
                          this.showViewStartHealth(data)
                        }}>查看</a>
                        {< a href = "javascript:;" onClick = {
                          () => {
                            this.setState({editStartHealth: data})
                          }
                        } > 设置 < /a>}
                        {appProbeUtil.isStartProbeStart(data)
                          ? <a
                              onClick={() => {
                              this.handleStartProbeStart(false)
                            }}
                              href="javascript:;">禁用</a>
                          : <a
                            onClick={() => {
                            this.handleStartProbeStart(true)
                          }}
                            href="javascript:;">启用</a>}
                      </Fragment>
                    )
                  } else {
                    return <a
                      href="javascript:;"
                      onClick={() => {
                      this.setState({editStartHealth: {
                          data
                        }})
                    }}>设置</a>
                  }
                }
                if (index === 1) {
                  if (appProbeUtil.isRunningProbeUsed(data)) {
                    return (
                      <Fragment>
                        <a
                          href="javascript:;"
                          onClick={() => {
                          this.showViewRunningHealth(data)
                        }}>查看</a>
                        {< a href = "javascript:;" onClick = {
                          () => {
                            this.setState({editRunHealth: data})
                          }
                        } > 设置 < /a>}
                        {appProbeUtil.isRunningProbeStart(data)
                          ? <a
                              onClick={() => {
                              this.handleRunProbeStart(false)
                            }}
                              href="javascript:;">禁用</a>
                          : <a
                            onClick={() => {
                            this.handleRunProbeStart(true)
                          }}
                            href="javascript:;">启用</a>}
                      </Fragment>
                    )
                  } else {
                    return <a
                      href="javascript:;"
                      onClick={() => {
                      this.setState({editRunHealth: data})
                    }}>设置</a>
                  }
                }
              }
            }
          ]}
            pagination={false}
            dataSource={[startProbe, runningProbe]}/>
        </Card>

        <Card
          style={{
          marginBottom: 24
        }}
          title={< Fragment > 成员应用权限 < Tooltip title = "成员的应用权限高于团队权限" > <Icon type="info-circle-o"/> < /Tooltip></Fragment >}>
          <Table
            columns={[
            {
              title: '用户名',
              dataIndex: 'nick_name'
            }, {
              title: '邮箱',
              dataIndex: 'email'
            }, {
              title: '权限',
              dataIndex: 'identity',
              render(val) {
                return <span>{teamUtil.actionToCN([val])}</span>
              }
            }, {
              title: '操作',
              dataIndex: 'action',
              render(val, data) {
                return <div>
                  <a
                    onClick={() => {
                    self.onEditAction(data)
                  }}
                    href="javascript:;">编辑权限</a>
                  <a
                    onClick={() => {
                    self.onDelMember(data)
                  }}
                    href="javascript:;">移除应用权限</a>
                </div>
              }
            }
          ]}
            pagination={false}
            dataSource={members}/>
          <div
            style={{
            marginTop: 10,
            textAlign: 'right'
          }}>
            <Button onClick={this.showAddMember}><Icon type="plus"/>
              设置成员应用权限</Button>
          </div>
        </Card>

        {this.state.addTag && <AddTag
          tags={tags
          ? tags.unused_labels
          : []}
          onCancel={this.cancelAddTag}
          onOk={this.handleAddTag}/>}
        {this.state.showAddVar && <AddVarModal
          onCancel={this.handleCancelAddVar}
          onSubmit={this.handleSubmitAddVar}/>}
        {this.state.showEditVar && <AddVarModal
          onCancel={this.cancelEditVar}
          onSubmit={this.handleEditVar}
          data={this.state.showEditVar}/>}
        {this.state.deleteVar && <ConfirmModal
          onOk={this.handleDeleteVar}
          onCancel={this.cancelDeleteVar}
          title="删除变量"
          desc="确定要删除此变量吗？"
          subDesc="此操作不可恢复"/>}
        {this.state.viewStartHealth && <ViewHealthCheck
          title="启动时检查查看"
          data={this.state.viewStartHealth}
          onCancel={() => {
          this.setState({viewStartHealth: null})
        }}/>}
        {this.state.editStartHealth && <EditHealthCheck
          ports={ports}
          onOk={this.handleEditHealth}
          title="设置启动时检查"
          data={this.state.editStartHealth}
          onCancel={this.onCancelEditStartProbe}/>}
        {this.state.toEditAction && <EditActions
          onSubmit={this.handleEditAction}
          onCancel={this.hideEditAction}
          actions={teamControl.actions}
          value={this.state.toEditAction.identity}/>}
        {this.state.viewRunHealth && <ViewRunHealthCheck
          title="运行时检查查看"
          data={this.state.viewRunHealth}
          onCancel={() => {
          this.setState({viewRunHealth: null})
        }}/>}
        {this.state.editRunHealth && <EditRunHealthCheck
          ports={ports}
          onOk={this.handleEditRunHealth}
          title="设置运行时检查"
          data={this.state.editRunHealth}
          onCancel={this.onCancelEditRunProbe}/>}
        {this.state.showAddMember && <SetMemberAppAction
          members={members}
          actions={teamControl.actions}
          onOk={this.handleAddMember}
          onCancel={this.hideAddMember}/>}
        {this.state.toDeleteMember && <ConfirmModal
          onOk={this.handleDelMember}
          title="删除成员权限"
          desc="确定要删除此成员的应用权限吗？"
          onCancel={this.hideDelMember}/>}
      </Fragment>
    );
  }
}
