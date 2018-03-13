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
  Input
} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import {getRoutes} from '../../utils/utils';
import appPortUtil from '../../utils/appPort-util';
import {getRouterData} from '../../common/router';
import DescriptionList from '../../components/DescriptionList';
import ConfirmModal from '../../components/ConfirmModal';
import Port from '../../components/Port';
import AddDomain from '../../components/AddDomain';
const {Description} = DescriptionList;

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

@Form.create()
class AddDomain2 extends PureComponent {
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
  checkKey = (rule, value, callback) => {
    var visitType = this
      .props
      .form
      .getFieldValue("protocol");
    if (visitType == 'http') {
      callback();
      return;
    }

    if (visitType != 'http' && value) {
      callback();
      return;
    }

    callback('请选择证书!');
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
    const protocol = getFieldValue('protocol') || 'http';
    const certificates = this.props.certificates || [];

    return (
      <Modal
        title="绑定域名"
        onOk={this.handleSubmit}
        visible={true}
        onCancel={this.handleCancel}>

        <Form onSubmit={this.handleSubmit}>

          <FormItem {...formItemLayout} label="协议">
            {getFieldDecorator('protocol', {
              initialValue: 'http',
              rules: [
                {
                  required: true,
                  message: '请添加端口'
                }
              ]
            })(
              <Select>
                <Option value="http">HTTP</Option>
                <Option value="https">HTTPS</Option>
                <Option value="httptohttps">HTTP转HTTPS</Option>
                <Option value="httpandhttps">HTTP与HTTPS共存</Option>
              </Select>
            )
}
          </FormItem>
          <FormItem {...formItemLayout} label="域名">
            {getFieldDecorator('domain', {
              rules: [
                {
                  required: true,
                  message: '请添加域名'
                }
              ]
            })(<Input placeholder="请填写域名"/>)
}
          </FormItem>
          <FormItem
            style={{
            display: protocol == 'http'
              ? 'none'
              : ''
          }}
            {...formItemLayout}
            label="选择证书">
            {getFieldDecorator('certificate_id', {
              initialValue: '',
              rules: [
                {
                  validator: this.checkKey
                }
              ]
            })(
              <Select>
                {certificates.map((item) => {
                  return (
                    <Option value={item.id}>{item.alias}</Option>
                  )
                })
}
              </Select>
            )}
            <p>无可用证书？
              <a
                onClick={() => {
                this
                  .props
                  .onCreateKey()
              }}
                href="javascript:;">去新建</a>
            </p>
          </FormItem>
        </Form>

      </Modal>
    )
  }
}

@Form.create()
class AddPort extends PureComponent {
  componentWillMount() {}
  handleSubmit = (e) => {
    e.preventDefault();
    this
      .props
      .form
      .validateFields((err, values) => {
        if (!err) {
          this.props.onOk && this
            .props
            .onOk(values);
        }
      })
  }
  render() {
    const {getFieldDecorator} = this.props.form;
    const formItemLayout = {
      labelCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 4
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
        title="添加端口"
        onOk={this.handleSubmit}
        onCancel={this.props.onCancel}
        visible={true}>
        <Form onSubmit={this.handleSubmit}>
          <FormItem {...formItemLayout} label="端口">
            {getFieldDecorator('port', {
              rules: [
                {
                  required: true,
                  message: '请添加端口'
                }
              ]
            })(<Input type="number" placeholder="请填写端口"/>)
}
          </FormItem>
          <FormItem {...formItemLayout} label="协议">
            {getFieldDecorator('protocol', {
              initialValue: 'http',
              rules: [
                {
                  required: true,
                  message: '请添加端口'
                }
              ]
            })(
              <Select>
                <Option value="http">http</Option>
                <Option value="tcp">tcp</Option>
                <Option value="udp">udp</Option>
                <Option value="mysql">mysql</Option>
              </Select>
            )
}
          </FormItem>
        </Form>
      </Modal>
    )
  }
}

class ChangeProtocol extends PureComponent {
  constructor(props) {
    super(props);
    this.state = {
      value: this.props.protocol || 'http'
    }
  }
  onChange = (value) => {
    this.setState({value: value});
  }
  handleCancel = () => {
    this.props.onCancel && this
      .props
      .onCancel()
  }
  handleSubmit = () => {
    this.props.onSubmit && this
      .props
      .onSubmit(this.state.value)
  }
  render() {

    return (
      <Form
        layout="inline"
        style={{
        position: 'relative',
        top: -8
      }}>
        <FormItem>
          <Select
            onChange={this.onChange}
            size="small"
            value={this.state.value}
            style={{
            width: 80
          }}>
            <Option value="http">http</Option>
            <Option value="tcp">tcp</Option>
            <Option value="udp">udp</Option>
            <Option value="mysql">mysql</Option>
          </Select>
        </FormItem>
        <FormItem>
          <Button onClick={this.handleSubmit} type="primary" size="small">确定</Button>
        </FormItem>
        <FormItem>
          <Button onClick={this.handleCancel} type="" size="small">取消</Button>
        </FormItem>
      </Form>
    )
  }
}

class Port2 extends PureComponent {
  constructor(props) {
    super(props);
    this.state = {
      editProtocol: false
    }
  }
  handleOuterChange = (val) => {
    this
      .props
      .onOuterChange(this.props.port.container_port, val);
  }
  handleInnerChange = (val) => {
    this
      .props
      .onInnerChange(this.props.port.container_port, val);
  }
  showEditProtocol = () => {
    this.setState({editProtocol: true})
  }
  cancelEditProtocol = () => {
    this.setState({editProtocol: false})
  }
  onSubmitProtocol = (val) => {
    this.props.onChangeProtocol && this
      .props
      .onChangeProtocol(this.props.port.container_port, val);
    this.cancelEditProtocol();
  }
  render() {

    const {port} = this.props;
    const outerUrl = appPortUtil.getOuterUrl(port);
    const innerUrl = appPortUtil.getInnerUrl(port);
    const showAlias = appPortUtil.getShowAlias(port);
    const domains = appPortUtil.getDomains(port);

    return (
      <Card
        style={{
        marginBottom: 24
      }}
        className={styles.portCard}
        title={< DescriptionList > <Description term="端口">{port.container_port}</Description> < Description term = "协议" > {
        this.state.editProtocol
          ? <ChangeProtocol
              protocol={port.protocol}
              onSubmit={this.onSubmitProtocol}
              onCancel={this.cancelEditProtocol}/>
          : <div>
              {port.protocol}
              <a onClick={this.showEditProtocol} href="javascript:;"><Icon type="edit"/></a>
            </div>
      } < /Description> <Description term=""><a href="javascript:;" onClick={()=>{this.props.onDeletePort(port.container_port)}} style={{float: 'right', fontWeight: 'normal', fontSize: 14, flaot: 'right'}}>删除端口</a > </Description> < /DescriptionList>}>
        <DescriptionList style={{
          marginBottom: 24
        }}>
          <Description term="内部访问"><Switch
            checked={appPortUtil.isOpenInner(port)}
            onChange={this.handleInnerChange}/></Description>
          <Description term="服务地址">{innerUrl
              ? innerUrl
              : '-'}</Description>
          <Description term="使用别名">
            <div>{showAlias}
              <a
                href="javascript:;"
                onClick={() => {
                this
                  .props
                  .onEditAlias(port)
              }}><Icon type="edit"/></a>
            </div>
          </Description>
        </DescriptionList>
        <DescriptionList style={{
          marginBottom: 24
        }}>
          <Description term="外部访问"><Switch
            checked={appPortUtil.isOpenOuter(port)}
            onChange={this.handleOuterChange}/></Description>
          <Description term="访问地址">{outerUrl
              ? <a href={outerUrl} target={outerUrl} target="_blank">{outerUrl}</a>
              : '-'}</Description>

          <Description
            term="绑定域名"
            style={{
            display: appPortUtil.canBindDomain(port)
              ? ''
              : 'none'
          }}>
            <div className={styles.domainList}>
              {domains.map((domain) => {
                return <div>
                  <a href={domain.domain_name} target="_blank">{domain.domain_name}</a>
                  <a
                    title="解绑"
                    onClick={() => {
                    this
                      .props
                      .onDeleteDomain({port: port.container_port, domain: domain.domain_name})
                  }}
                    className={styles.removePort}
                    href="javascript:;"><Icon type="close"/></a>
                </div>
              })
}
            </div>
            <Button
              onClick={() => {
              this
                .props
                .onAddDomain(port.container_port)
            }}
              size="small"
              type="dashed"><Icon type="plus"/></Button>
          </Description>

        </DescriptionList>

      </Card>
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
        }
      })
  }
  render() {
    const {ports, certificates} = this.props;
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
        {this.state.showAddPort && <AddPort onCancel={this.onCancelAddPort} onOk={this.handleAddPort}/>}
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
