import React, {PureComponent, Fragment} from 'react';
import {connect} from 'dva';
import {Link, Route} from 'dva/router';
import {
  Row,
  Col,
  Card,
  Form,
  Button,
  Icon,
  Switch,
  Alert,
  Select,
  Modal,
  Input,
  notification
} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import {getRoutes} from '../../utils/utils';
import appPortUtil from '../../utils/appPort-util';
import appUtil from '../../utils/app';
import {getRouterData} from '../../common/router';
import DescriptionList from '../../components/DescriptionList';
import ConfirmModal from '../../components/ConfirmModal';
import Port from '../../components/Port';
import AddDomain from '../../components/AddDomain';
const {Description} = DescriptionList;
import ScrollerX from '../../components/ScrollerX';
import AddPort from '../../components/AddPort';

import styles from './port.less';
import globalUtil from '../../utils/global';
const FormItem = Form.Item;
const Option = Select.Option;
const {TextArea} = Input;

@Form.create()
class EditAlias extends PureComponent {
  constructor(props) {
    super(props);
    this.state = {}
  }
  handleSubmit = (e) => {
    e.preventDefault();
    this
      .props
      .form
      .validateFields({
        force: true
      }, (err, values) => {
        if (!err) {
          this.props.onOk && this
            .props
            .onOk(values);
        }
      })
  }
  handleCancel = () => {
    this.props.onCancel && this
      .props
      .onCancel();
  }
  render() {
    const {getFieldDecorator} = this.props.form;
    const formItemLayout = {
      labelCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 5
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
    const port = this.props.port || {};
    return (
      <Modal
        title="编辑别名"
        onOk={this.handleSubmit}
        visible={true}
        onCancel={this.handleCancel}>

        <Form onSubmit={this.handleSubmit}>

          <FormItem {...formItemLayout} label="别名">
            {getFieldDecorator('alias', {
              initialValue: port.port_alias,
              rules: [
                {
                  required: true,
                  message: '请填写端口别名'
                }
              ]
            })(<Input placeholder="请填写端口别名"/>)
}
          </FormItem>
        </Form>

      </Modal>
    )
  }
}

@Form.create()
class AddKey extends PureComponent {
  constructor(props) {
    super(props);
    this.state = {}
  }
  handleSubmit = (e) => {
    e.preventDefault();
    this
      .props
      .form
      .validateFields({
        force: true
      }, (err, values) => {
        if (!err) {

          this.props.onOk && this
            .props
            .onOk(values);
        }
      })
  }
  handleCancel = () => {
    this.props.onCancel && this
      .props
      .onCancel();
  }
  render() {
    const {getFieldDecorator, getFieldValue} = this.props.form;
    const formItemLayout = {
      labelCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 5
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
        title="新建证书"
        onOk={this.handleSubmit}
        visible={true}
        onCancel={this.handleCancel}>

        <Form onSubmit={this.handleSubmit}>

          <FormItem {...formItemLayout} label="证书名称">
            {getFieldDecorator('alias', {
              initialValue: '',
              rules: [
                {
                  required: true,
                  message: '请填写证书名称'
                }
              ]
            })(<Input placeholder="请填写证书名称"/>)
}
          </FormItem>
          <FormItem {...formItemLayout} label="key">
            {getFieldDecorator('private_key', {
              rules: [
                {
                  required: true,
                  message: '请添加key'
                }
              ]
            })(<TextArea placeholder="请添加key"/>)
}
          </FormItem>
          <FormItem {...formItemLayout} label="证书">
            {getFieldDecorator('certificate', {
              rules: [
                {
                  required: true,
                  message: '请添加证书'
                }
              ]
            })(<TextArea placeholder="请添加证书"/>)
}
          </FormItem>
        </Form>

      </Modal>
    )
  }
}


@connect(({user, appControl}) => ({currUser: user.currentUser, ports: appControl.ports, certificates: appControl.certificates}), null, null, {withRef: true})
export default class Index extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {
      showDeletePort: null,
      showDeleteDomain: null,
      showAddPort: false,
      showAddDomain: null,
      showAddKey: false,
      showEditAlias: null
    }
  }

  componentDidMount() {
    const {dispatch} = this.props;
    this.fetchPorts();
    this.fetchCertificates();
  }
  //获取证书
  fetchCertificates() {
    const {dispatch} = this.props;
    dispatch({
      type: 'appControl/fetchCertificates',
      payload: {
        team_name: globalUtil.getCurrTeamName()
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
  handleSubmitProtocol = (protocol, port, callback) => {
    const {dispatch} = this.props;
    dispatch({
      type: 'appControl/changeProtocol',
      payload: {
        team_name: globalUtil.getCurrTeamName(),
        app_alias: this.props.appAlias,
        port: port,
        protocol: protocol
      },
      callback: () => {
        this.fetchPorts();
        callback();
      }
    })
  }
  handleDeletePort = (port) => {
    this.setState({showDeletePort: port})
  }
  cancalDeletePort = () => {
    this.setState({showDeletePort: null})
  }
  handleSubmitDeletePort = () => {
    this
      .props
      .dispatch({
        type: 'appControl/deletePort',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          port: this.state.showDeletePort
        },
        callback: () => {
          this.cancalDeletePort();
          this.fetchPorts();
          notification.success({message: '操作成功，需要重启才能生效'});
          this.props.onshowRestartTips(true)
        }
      })
  }

  handleDeleteDomain = (port) => {
    this.setState({showDeleteDomain: port})
  }
  cancalDeleteDomain = () => {
    this.setState({showDeleteDomain: null})
  }
  handleSubmitDeleteDomain = () => {
    this
      .props
      .dispatch({
        type: 'appControl/unbindDomain',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          port: this.state.showDeleteDomain.port,
          domain: this.state.showDeleteDomain.domain
        },
        callback: () => {
          this.cancalDeleteDomain();
          this.fetchPorts();
          notification.success({message: '操作成功，需要重启才能生效'});
          this.props.onshowRestartTips(true)
        }
      })
  }
  showAddPort = () => {
    this.setState({showAddPort: true})
  }

  onCancelAddPort = () => {
    this.setState({showAddPort: false})
  }
  handleAddPort = (val) => {

    this
      .props
      .dispatch({
        type: 'appControl/addPort',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          protocol: val.protocol,
          port: val.port
        },
        callback: () => {
          this.onCancelAddPort();
          this.fetchPorts();
          notification.success({message: '操作成功，需要重启才能生效'});
          this.props.onshowRestartTips(true)
        }
      })

  }
  onAddDomain = (val) => {
    this.setState({showAddDomain: val})
  }
  onCancelAddDomain = () => {
    this.setState({showAddDomain: null})
  }
  //创建证书
  handleCreateKey = () => {
    this.setState({showAddDomain: null, showAddKey: true})
  }
  cancelCreateKey = () => {
    this.setState({showAddKey: false})
  }
  handleSubmitKey = (vals) => {
    this
      .props
      .dispatch({
        type: 'appControl/addCertificate',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          alias: vals.alias,
          private_key: vals.private_key,
          certificate: vals.certificate
        },
        callback: () => {
          this.cancelCreateKey();
          this.fetchCertificates();
        }
      })
  }
  handleOpenOuter = (port) => {
    this
      .props
      .dispatch({
        type: 'appControl/openPortOuter',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          port: port
        },
        callback: () => {
          this.fetchPorts();
          notification.success({message: '操作成功，需要重启才能生效'});
          this.props.onshowRestartTips(true)
        }
      })
  }
  onCloseOuter = (port) => {
    this
      .props
      .dispatch({
        type: 'appControl/closePortOuter',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          port: port
        },
        callback: () => {
          this.fetchPorts();
          notification.success({message: '操作成功，需要重启才能生效'});
          this.props.onshowRestartTips(true)
        }
      })
  }
  handleOpenInner = (port) => {
    this
      .props
      .dispatch({
        type: 'appControl/openPortInner',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          port: port
        },
        callback: () => {
          this.fetchPorts();
          notification.success({message: '操作成功，需要重启才能生效'});
          this.props.onshowRestartTips(true)
        }
      })
  }
  onCloseInner = (port) => {
    this
      .props
      .dispatch({
        type: 'appControl/closePortInner',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          port: port
        },
        callback: () => {
          this.fetchPorts();
          notification.success({message: '操作成功，需要重启才能生效'});
          this.props.onshowRestartTips(true)
        }
      })
  }
  handleAddDomain = (values) => {
    this
      .props
      .dispatch({
        type: 'appControl/bindDomain',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          port: this.state.showAddDomain.container_port,
          domain: values.domain,
          protocol: values.protocol,
          certificate_id: values.certificate_id
        },
        callback: () => {
          this.fetchPorts();
          this.onCancelAddDomain();
        }
      })
  }
  showEditAlias = (port) => {
    this.setState({showEditAlias: port})
  }
  hideEditAlias = () => {
    this.setState({showEditAlias: null})
  }
  handleEditAlias = (vals) => {
    this
      .props
      .dispatch({
        type: 'appControl/editPortAlias',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          port: this.state.showEditAlias.container_port,
          port_alias: vals.alias
        },
        callback: () => {
          this.fetchPorts();
          this.hideEditAlias();
          notification.success({message: '操作成功，需要重启才能生效'});
          this.props.onshowRestartTips(true)
        }
      })
  }
  render() {
    const {ports, certificates, appDetail} = this.props;
    const isImageApp = appUtil.isImageApp(appDetail);
    const isDockerfile = appUtil.isDockerfile(appDetail);
    return (
      <Fragment>
        <Row>
          <Col span={12}>
            <Alert
              showIcon
              message="域名配置信息发生变化后需要重启应用才能生效"
              type="info"
              style={{
              marginBottom: 24
            }}/>
          </Col>
          <Col span={12} style={{
            textAlign: 'right'
          }}>
            <Button onClick={this.showAddPort} type="primary"><Icon type="plus"/>添加端口</Button>
          </Col>
        </Row>

        {!ports.length
          ? <Card>
              <p
                style={{
                marginTop: 100,
                marginBottom: 100,
                fontSize: 20,
                textAlign: 'center'
              }}>如需要提供访问服务，请<a onClick={this.showAddPort} href="javascript:;">添加端口</a>
              </p>
            </Card>
          : <Card>
            <ScrollerX sm={700}>
            {ports.map((port) => {
              return <Port
                port={port}
                onDelete={this.handleDeletePort}
                onEditAlias={this.showEditAlias}
                onSubmitProtocol={this.handleSubmitProtocol}
                onOpenInner={this.handleOpenInner}
                onCloseInner={this.onCloseInner}
                onOpenOuter={this.handleOpenOuter}
                onCloseOuter={this.onCloseOuter}
                onAddDomain={this.onAddDomain}
                onDeleteDomain={this.handleDeleteDomain}/>
            })
}
          </ScrollerX>
          </Card>
}
        {this.state.showDeletePort && <ConfirmModal
          title="端口删除"
          desc="确定要删除此端口吗？"
          subDesc="此操作不可恢复"
          onOk={this.handleSubmitDeletePort}
          onCancel={this.cancalDeletePort}/>}
        {this.state.showDeleteDomain && <ConfirmModal
          title="域名解绑"
          desc="确定要解绑此域名吗？"
          subDesc={this.state.showDeleteDomain.domain}
          onOk={this.handleSubmitDeleteDomain}
          onCancel={this.cancalDeleteDomain}/>}
        {this.state.showAddPort && <AddPort isImageApp={isImageApp} isDockerfile={isDockerfile} onCancel={this.onCancelAddPort} onOk={this.handleAddPort} />}
        {this.state.showAddDomain && <AddDomain
          certificates={certificates || []}
          onCreateKey={this.handleCreateKey}
          onOk={this.handleAddDomain}
          onCancel={this.onCancelAddDomain}/>}
        {this.state.showAddKey && <AddKey onOk={this.handleSubmitKey} onCancel={this.cancelCreateKey}/>}
        {this.state.showEditAlias && <EditAlias
          port={this.state.showEditAlias}
          onOk={this.handleEditAlias}
          onCancel={this.hideEditAlias}/>}
      </Fragment>
    );
  }
}
