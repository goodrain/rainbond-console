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
import appPortUtil from '../../utils/appPort-util';
import styles from './index.less';
const FormItem = Form.Item;

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
      .onCancel();
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
        <div>
          <FormItem>
            <Button onClick={this.handleSubmit} type="primary" size="small">确定</Button>
          </FormItem>
          <FormItem>
            <Button onClick={this.handleCancel} type="" size="small">取消</Button>
          </FormItem>
        </div>
      </Form>
    )
  }
}

export default class Index extends PureComponent {
  constructor(props) {
    super(props);
    this.state = {
      editProtocol: false,
      showEditAlias: null
    }
  }
  onSubmitProtocol = (protocol) => {
    this.props.onSubmitProtocol && this
      .props
      .onSubmitProtocol(protocol, this.props.port.container_port, () => {
        this.cancelEditProtocol()
      })
  }
  onAddDomain = () => {
    this.props.onAddDomain && this
      .props
      .onAddDomain(this.props.port);
  }
  handleDelete = () => {
    this.props.onDelete && this
      .props
      .onDelete(this.props.port.container_port);
  }
  handleInnerChange = (value) => {
    if (value) {
      this.props.onOpenInner && this
        .props
        .onOpenInner(this.props.port.container_port);
    } else {
      this.props.onCloseInner && this
        .props
        .onCloseInner(this.props.port.container_port);
    }
  }
  handleOuterChange = (value) => {
    if (value) {
      this.props.onOpenOuter && this
        .props
        .onOpenOuter(this.props.port.container_port);
    } else {
      this.props.onCloseOuter && this
        .props
        .onCloseOuter(this.props.port.container_port);
    }
  }
  showEditProtocol = () => {
    this.setState({editProtocol: true})
  }
  cancelEditProtocol = () => {
    this.setState({editProtocol: false})
  }
  render() {
    const port = this.props.port;
    const outerUrl = appPortUtil.getOuterUrl(port);
    const innerUrl = appPortUtil.getInnerUrl(port);
    const showAlias = appPortUtil.getShowAlias(port);
    const domains = appPortUtil.getDomains(port);
    var showDomain = this.props.showDomain;
    //是否显示对外访问地址,创建过程中不显示
    const showOuterUrl = this.props.showOuterUrl === void 0
      ? true
      : this.props.showOuterUrl;
    showDomain = showDomain === void 0
      ? true
      : showDomain;

    return (
      <table
        className={styles.table}
        style={{
        width: '100%',
        marginBottom: 8
      }}>
        <thead>
          <tr>
            <th style={{
              width: 60
            }}>端口号</th>
            <th style={{
              width: 100
            }}>端口协议</th>
            <th style={{
              width: '50%'
            }}>服务信息</th>
            {showDomain && <th style={{
              width: '30%'
            }}>绑定域名</th>}
            <th style={{
              width: 100
            }}>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>{port.container_port}</td>
            <td>
              {this.state.editProtocol
                ? <ChangeProtocol
                    protocol={port.protocol}
                    onSubmit={this.onSubmitProtocol}
                    onCancel={this.cancelEditProtocol}/>
                : <div>
                  {port.protocol}
                  <a onClick={this.showEditProtocol} href="javascript:;"><Icon type="edit"/></a>
                </div>
}
            </td>
            <td>
              <div
                style={{
                borderBottom: '1px solid #e8e8e8',
                marginBottom: 8,
                paddingBottom: 8
              }}>
                <p>
                  <span className={styles.label}>对内服务</span>
                  <Switch
                    checked={appPortUtil.isOpenInner(port)}
                    onChange={this.handleInnerChange}
                    size="small"/></p>
                <p>
                  <span className={styles.label}>访问地址</span>
                  {innerUrl
                    ? innerUrl
                    : '-'}</p>
                <p className={styles.lr}>
                  <span className={styles.label}>使用别名</span>
                  <a
                    href="javascript:;"
                    onClick={() => {
                    this
                      .props
                      .onEditAlias(port)
                  }}>{showAlias}</a>
                </p>
              </div>
              <div>
                <p>
                  <span className={styles.label}>对外服务</span>
                  <Switch
                    checked={appPortUtil.isOpenOuter(port)}
                    onChange={this.handleOuterChange}
                    size="small"/></p>
                <p className={styles.lr}>
                  <span className={styles.label}>访问地址</span>
                  {(showOuterUrl && outerUrl)
                    ? <a href={outerUrl} target={outerUrl} target="_blank">{outerUrl}</a>
                    : '-'}</p>
              </div>
            </td>
            {showDomain && <td>
              {appPortUtil.canBindDomain(port)
                ? <div>
                    {domains.map((domain) => {
                      return <div>
                        <a
                          href={(domain.protocol === 'http'
                          ? 'http'
                          : 'https') + '://' + domain.domain_name}
                          target="_blank">{(domain.protocol === 'http'
                            ? 'http'
                            : 'https') + '://' + domain.domain_name}</a>
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
                    <Button size="small" onClick={this.onAddDomain}>新增域名</Button>
                  </div>
                : null
}

            </td>
}

            <td>
              <p>
                <Button onClick={this.handleDelete} size="small">删除</Button>
              </p>
            </td>
          </tr>
        </tbody>
      </table>
    )
  }
}