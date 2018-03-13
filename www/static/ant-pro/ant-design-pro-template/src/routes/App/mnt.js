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
  Input,
  Alert,
  Dropdown,
  Table,
  Modal,
  Radio,
  Tooltip,
  notification
} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import {getRoutes} from '../../utils/utils';
import {getRouterData} from '../../common/router';
import ConfirmModal from '../../components/ConfirmModal';
import {getMnt, addMnt} from '../../services/app';
import styles from './Index.less';
import globalUtil from '../../utils/global';
import AddRelationMnt from '../../components/AddRelationMnt';
const FormItem = Form.Item;
const RadioButton = Radio.Button;
const RadioGroup = Radio.Group;

@Form.create()
class AddVolumes extends PureComponent {
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
    const {data} = this.props;
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
        title="添加持久化"
        onOk={this.handleSubmit}
        onCancel={this.handleCancel}
        visible={true}>
        <Form onSubmit={this.handleSubmit}>
          <FormItem {...formItemLayout} label="名称">
            {getFieldDecorator('volume_name', {
              initialValue: data.volume_name || '',
              rules: [
                {
                  required: true,
                  message: '请输入持久化名称'
                }
              ]
            })(<Input placeholder="请输入持久化名称"/>)}
          </FormItem>
          <FormItem {...formItemLayout} label="目录">
            {getFieldDecorator('volume_path', {
              initialValue: data.volume_path || '',
              rules: [
                {
                  required: true,
                  message: '请输入持久化目录'
                }
              ]
            })(<Input placeholder="请输入持久化目录"/>)}
          </FormItem>
          <FormItem {...formItemLayout} label="类型">

            {getFieldDecorator('volume_type', {
              initialValue: data.volume_type || '',
              rules: [
                {
                  required: true,
                  message: '请选择持久化类型'
                }
              ]
            })(
              <RadioGroup>
                <Radio value="share-file">
                  <Tooltip title="分布式文件存储，可租户内共享挂载，适用于所有类型应用">共享存储（文件）</Tooltip>
                </Radio>
                <Radio value="memoryfs">
                  <Tooltip title="基于内存的存储设备，容量由内存量限制。应用重启数据即丢失，适用于高速暂存数据">内存文件存储</Tooltip>
                </Radio>
                <Radio value="local">
                  <Tooltip title="本地高速块存储设备，适用于有状态数据库服务">本地存储</Tooltip>
                </Radio>
              </RadioGroup>
            )}

          </FormItem>
        </Form>
      </Modal>
    )
  }
}

@connect(({user, appControl}) => ({currUser: user.currentUser, volumes: appControl.volumes}), null, null, {withRef: true})
export default class Index extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {
      showAddVar: null,
      showAddRelation: false,
      selfPathList: [],
      mntList: [],
      toDeleteMnt: null,
      toDeleteVolume: null
    }
  }

  componentDidMount() {
    const {dispatch} = this.props;
    this.loadMntList();
    this.fetchVolumes();

  }
  fetchVolumes = () => {
    this
      .props
      .dispatch({
        type: 'appControl/fetchVolumes',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias
        }
      })
  }
  loadMntList = () => {
    getMnt({
      team_name: globalUtil.getCurrTeamName(),
      app_alias: this.props.appAlias,
      page: 1,
      page_size: 1000
    }).then((data) => {
      if (data) {
        this.setState({
          mntList: data.list || []
        })
      }
    })
  }
  handleAddVar = () => {
    this.setState({
      showAddVar: {
        new: true
      }
    })
  }
  handleCancelAddVar = () => {
    this.setState({showAddVar: null})
  }
  handleSubmitAddVar = (vals) => {
    this
      .props
      .dispatch({
        type: 'appControl/addVolume',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          ...vals
        },
        callback: () => {
          this.fetchVolumes();
          this.handleCancelAddVar();
        }
      })
  }
  showAddRelation = () => {
    this.setState({showAddRelation: true})
  }
  handleCancelAddRelation = () => {
    this.setState({showAddRelation: false})
  }
  handleSubmitAddMnt = (mnts) => {
    addMnt({
      team_name: globalUtil.getCurrTeamName(),
      app_alias: this.props.appAlias,
      body: mnts
    }).then((data) => {
      if (data) {
        this.handleCancelAddRelation();
        this.loadMntList()
      }
    })
  }
  onDeleteMnt = (mnt) => {
    this.setState({toDeleteMnt: mnt})
  }
  onDeleteVolume = (data) => {
    this.setState({toDeleteVolume: data})
  }
  onCancelDeleteVolume = () => {
    this.setState({toDeleteVolume: null})
  }
  handleDeleteVolume = () => {
    this
      .props
      .dispatch({
        type: 'appControl/deleteVolume',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          volume_id: this.state.toDeleteVolume.ID
        },
        callback: () => {
          this.onCancelDeleteVolume();
          this.fetchVolumes();
        }
      })
  }
  handleDeleteMnt = () => {
    this
      .props
      .dispatch({
        type: 'appControl/deleteMnt',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: this.props.appAlias,
          dep_vol_id: this.state.toDeleteMnt.dep_vol_id
        },
        callback: () => {
          this.cancelDeleteMnt();
          this.loadMntList();
        }
      })
  }
  cancelDeleteMnt = () => {
    this.setState({toDeleteMnt: null})
  }
  render() {
    const {mntList} = this.state;
    const {volumes} = this.props;
    return (
      <Fragment>
        <Row>
          <Col span={12}>
            <Alert
              showIcon
              message="配置信息发生变化后需要重启应用才能生效"
              type="info"
              style={{
              marginBottom: 24
            }}/>
          </Col>
        </Row>
        <Card
          style={{
          marginBottom: 24
        }}
          title={< span > 持久化设置 < /span>}>
          <Table
            pagination={false}
            columns={[
            {
              title: '持久化名称',
              dataIndex: 'volume_name'
            }, {
              title: '持久化目录',
              dataIndex: 'volume_path'
            }, {
              title: '持久化类型',
              dataIndex: 'volume_type'
            }, {
              title: '操作',
              dataIndex: 'action',
              render: (val, data) => {
                return <a
                  onClick={() => {
                  this.onDeleteVolume(data)
                }}
                  href="javascript:;">删除</a>
              }
            }
          ]}
            dataSource={volumes}/>
          <div
            style={{
            marginTop: 10,
            textAlign: 'right'
          }}>
            <Button onClick={this.handleAddVar}><Icon type="plus"/>添加持久化</Button>
          </div>
        </Card>
        <Card title={< span > 文件存储 < /span>}>
          <Table
            pagination={false}
            columns={[
            {
              title: '本地持久化目录',
              dataIndex: 'local_vol_path'
            }, {
              title: '目标持久化名称',
              dataIndex: 'dep_vol_name'
            }, {
              title: '目标持久化目录',
              dataIndex: 'dep_vol_path'
            }, {
              title: '目标持久化类型',
              dataIndex: 'dep_vol_type'
            }, {
              title: '目标所属应用',
              dataIndex: 'dep_app_name',
              render: (v, data) => {
                return <Link to={'/app/' + data.dep_app_alias + '/overview'}>{v}</Link>
              }
            }, {
              title: '目标应用所属组',
              dataIndex: 'dep_app_group',
              render: (v, data) => {
                return <Link to={'/groups/' + data.dep_group_id}>{v}</Link>
              }
            }, {
              title: '操作',
              dataIndex: 'action',
              render: (val, data) => {
                return <a
                  onClick={() => {
                  this.onDeleteMnt(data)
                }}
                  href="javascript:;">取消挂载</a>
              }
            }
          ]}
            dataSource={mntList}/>
          <div
            style={{
            marginTop: 10,
            textAlign: 'right'
          }}>
            <Button onClick={this.showAddRelation}><Icon type="plus"/>
              挂载目录</Button>
          </div>
        </Card>
        {this.state.showAddVar && <AddVolumes
          onCancel={this.handleCancelAddVar}
          onSubmit={this.handleSubmitAddVar}
          data={this.state.showAddVar}/>}
        {this.state.showAddRelation && <AddRelationMnt
          appAlias={this.props.appAlias}
          onCancel={this.handleCancelAddRelation}
          onSubmit={this.handleSubmitAddMnt}/>}
        {this.state.toDeleteMnt && <ConfirmModal
          title="取消挂载"
          desc="确定要取消此挂载目录吗?"
          onCancel={this.cancelDeleteMnt}
          onOk={this.handleDeleteMnt}/>}
        {this.state.toDeleteVolume && <ConfirmModal
          title="删除持久化目录"
          desc="确定要删除此持久化目录吗?"
          onCancel={this.onCancelDeleteVolume}
          onOk={this.handleDeleteVolume}/>}
      </Fragment>
    );
  }
}
