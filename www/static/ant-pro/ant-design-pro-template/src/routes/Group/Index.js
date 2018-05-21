import React, {PureComponent} from 'react';
import moment from 'moment';
import {connect} from 'dva';
import {Link} from 'dva/router';
import {
  Row,
  Col,
  Card,
  Form,
  Button,
  Input,
  Icon,
  Menu,
  Dropdown,
  Modal,
  notification
} from 'antd';
import {routerRedux} from 'dva/router';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import EditableLinkGroup from '../../components/EditableLinkGroup';
import AppList from './AppList';
import AppShape from './AppShape';
import AppShare from './AppShare';
import ConfirmModal from '../../components/ConfirmModal';
import NoPermTip from '../../components/NoPermTip';
import styles from './Index.less';
import globalUtil from '../../utils/global';
import teamUtil from '../../utils/team';
import userUtil from '../../utils/user';
const FormItem = Form.Item;
const ButtonGroup = Button.Group;

@Form.create()
class EditGroupName extends PureComponent {
  onOk = (e) => {
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
  render() {
    const {title, onCancel, onOk, group_name} = this.props;
    const {getFieldDecorator, getFieldValue} = this.props.form;
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
      <Modal title={title || ''} visible={true} onCancel={onCancel} onOk={this.onOk}>
        <Form onSubmit={this.onOk}>
          <FormItem {...formItemLayout} label="组名称">
            {getFieldDecorator('group_name', {
              initialValue: group_name || '',
              rules: [
                {
                  required: true,
                  message: '请填写组名称'
                }
              ]
            })(<Input placeholder="请填写组名称"/>)
}
          </FormItem>
        </Form>
      </Modal>
    )
  }
}

@connect(({user, groupControl, global}) => ({
  currUser: user.currentUser,
  apps: groupControl.apps,
  groupDetail: groupControl.groupDetail || {},
  groups: global.groups || []
}))
class Main extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {
      type: 'shape',
      toDelete: false,
      toEdit: false,
      toAdd: false
    }
  }
  getGroupId() {
    return this.props.group_id;
  }
  componentDidMount() {
    const {dispatch} = this.props;
    this.fetchGroupDetail();
    this.recordShare()
  }
  componentwillreceiveprops(nextProps) {

  }
  fetchGroupDetail() {
    const {dispatch, form, index} = this.props;
    const team_name = globalUtil.getCurrTeamName();
    const region_name = globalUtil.getCurrRegionName();

    dispatch({
      type: 'groupControl/fetchGroupDetail',
      payload: {
        team_name: team_name,
        region_name: region_name,
        group_id: this.getGroupId()
      },
      handleError: (res) => {
        if (res && res.status === 404) {
          this
            .props
            .dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/exception/404`));
        }
      }
    })
  }

  componentWillUnmount() {
    this
      .props
      .dispatch({type: 'groupControl/clearGroupDetail'})
  }
  handleFormReset = () => {
    const {form, dispatch} = this.props;
    form.resetFields();
    this.loadApps();
  }
  handleSearch = (e) => {
    e.preventDefault();
    this.loadApps();
  }
  changeType = (type) => {
    this.setState({type: type})
  }
  toDelete = () => {
    this.setState({toDelete: true})
  }
  cancelDelete = () => {
    this.setState({toDelete: false})
  }
  handleDelete = () => {
    const {dispatch} = this.props;
    dispatch({
      type: 'groupControl/delete',
      payload: {
        team_name: globalUtil.getCurrTeamName(),
        group_id: this.getGroupId()
      },
      callback: () => {
        location.hash = `/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/index`;
        this.cancelDelete();
        this
          .props
          .dispatch({
            type: 'global/fetchGroups',
            payload: {
              team_name: globalUtil.getCurrTeamName()
            }
          })
      }
    })
  }
  toEdit = () => {
    this.setState({toEdit: true})
  }
  cancelEdit = () => {
    this.setState({toEdit: false})
  }
  handleEdit = (vals) => {
    const {dispatch} = this.props;
    dispatch({
      type: 'groupControl/editGroup',
      payload: {
        team_name: globalUtil.getCurrTeamName(),
        group_id: this.getGroupId(),
        group_name: vals.group_name
      },
      callback: () => {
        this.cancelEdit();
        this.fetchGroupDetail();
        dispatch({
          type: 'global/fetchGroups',
          payload: {
            team_name: globalUtil.getCurrTeamName()
          }
        })
      }
    })
  }
  toAdd = () => {
    this.setState({toAdd: true})
  }
  cancelAdd = () => {
    this.setState({toAdd: false})
  }
  handleAdd = (vals) => {
    const {dispatch} = this.props;
    dispatch({
      type: 'groupControl/addGroup',
      payload: {
        team_name: globalUtil.getCurrTeamName(),
        group_name: vals.group_name
      },
      callback: () => {
        notification.success({message: `添加成功`});
        this.cancelAdd();
        dispatch({
          type: 'global/fetchGroups',
          payload: {
            team_name: globalUtil.getCurrTeamName()
          }
        })
      }
    })
  }

  recordShare = () => {
    const {dispatch} = this.props;
    dispatch({
      type: 'groupControl/recordShare',
      payload: {
        team_name: globalUtil.getCurrTeamName(),
        group_id: this.getGroupId()
      },
      callback: (data) => {
        if (data._code == 20021) {
          this.setState({recordShare: true});
          notification['info']({message: '分享未完成', description: '您有分享未完成，可以点击继续分享'});
        } else {
          this.setState({recordShare: false});
        }
      }
    })
  }

  handleShare = () => {
    const {dispatch} = this.props;
    dispatch({
      type: 'groupControl/ShareGroup',
      payload: {
        team_name: globalUtil.getCurrTeamName(),
        group_id: this.getGroupId()
      },
      callback: (data) => {
        if (data.bean.step === 1) {
          dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/groups/share/one/${data.bean.group_id}/${data.bean.ID}`))
        }
        if (data.bean.step === 2) {
          dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/groups/share/two/${data.bean.group_id}/${data.bean.ID}`))
        }
      }
    })
  }
  render() {
    const {
      index,
      projectLoading,
      activitiesLoading,
      currUser,
      apps,
      groupDetail,
      group_id,
      groups
    } = this.props;

    const team_name = globalUtil.getCurrTeamName();
    const team = userUtil.getTeamByTeamName(currUser, team_name);
    if (!groups.length) 
      return null;
    const currGroup = groups.filter((group) => {
      return group.group_id === Number(group_id);
    })[0];
    var hasService = false;
    if (currGroup && currGroup.service_list && currGroup.service_list.length) {
      hasService = true;
    }

    if (group_id == -1) {
      return (
        <PageHeaderLayout
          content={(
          <div className={styles.pageHeaderContent}>
            <div className={styles.content}>
              <div className={styles.contentTitle}>{groupDetail.group_name || '-'}</div>
            </div>
          </div>
        )}
          extraContent={(
          <Button onClick={this.toAdd} href="javascript:;">新增组</Button>
        )}>
          <AppList groupId={this.getGroupId()}/> {this.state.toAdd && <EditGroupName title="添加新组" onCancel={this.cancelAdd} onOk={this.handleAdd}/>}
        </PageHeaderLayout>
      )
    }

    const pageHeaderContent = (
      <div className={styles.pageHeaderContent}>
        <div className={styles.content}>
          <div className={styles.contentTitle}>{groupDetail.group_name || '-'}</div>
        </div>
      </div>
    );

    const extraContent = (
      <div className={styles.extraContent}>
        <ButtonGroup style={{
          marginRight: 10
        }}>

          {(teamUtil.canShareApp(team) && hasService && this.state.recordShare)
            ? <Button onClick={this.handleShare}>继续分享</Button>
            : ''}
          {(teamUtil.canShareApp(team) && hasService && !this.state.recordShare)
            ? <Button onClick={this.handleShare}>分享</Button>
            : ''}
          <Dropdown
            overlay={(
            <Menu>
              {
                teamUtil.canManageGroup(team) && 
                <Menu.Item>
                  <a onClick={this.toEdit} href="javascript:;">修改组名</a>
                </Menu.Item>
              }
              {
                teamUtil.canManageGroup(team) && 
                <Menu.Item>
                  <a onClick={this.toDelete} href="javascript:;">删除当前组</a>
                </Menu.Item>
              }
              
              
              <Menu.Item>
                <a onClick={this.toAdd} href="javascript:;">新增组</a>
              </Menu.Item>
            </Menu>
          )}>
            <Button>更多<Icon type="ellipsis"/></Button>
          </Dropdown>

        </ButtonGroup>
        <ButtonGroup>
          {hasService && <Button
            onClick={() => {
            this.changeType('shape')
          }}
            type={this.state.type === 'shape'
            ? 'primary'
            : ''}
            active>拓扑图</Button>}
          <Button
            onClick={() => {
            this.changeType('list')
          }}
            type={this.state.type === 'list'
            ? 'primary'
            : ''}>列表</Button>
        </ButtonGroup>
      </div>
    );

    return (
      <PageHeaderLayout content={pageHeaderContent} extraContent={extraContent}>
        {(!hasService || this.state.type === 'list') && <AppList groupId={this.getGroupId()}/>}
        {(hasService && this.state.type === 'shape') && <AppShape group_id={group_id}/>}
        {this.state.toDelete && <ConfirmModal
          title="删除组"
          desc="确定要此删除此分组吗？"
          subDesc="此操作不可恢复"
          onOk={this.handleDelete}
          onCancel={this.cancelDelete}/>}
        {this.state.toEdit && <EditGroupName
          group_name={groupDetail.group_name}
          title="修改组名"
          onCancel={this.cancelEdit}
          onOk={this.handleEdit}/>}
        {this.state.toAdd && <EditGroupName title="添加新组" onCancel={this.cancelAdd} onOk={this.handleAdd}/>}
      </PageHeaderLayout>
    );
  }
}

@connect(({user, groupControl, }) => ({currUser: user.currentUser}), null, null, {pure: false})
export default class Index extends PureComponent {
  constructor(arg) {
    super(arg);
    this.id = '';
    this.state = {
      show: true
    }
  }
  getGroupId() {
    const params = this.props.match.params;
    return params.groupId;
  }
  flash = () => {
    this.setState({
      show: false
    }, () => {
      this.setState({show: true})
    })
  }
  render() {
    const {
      index,
      projectLoading,
      activitiesLoading,
      currUser,
      apps,
      groupDetail,
      groups
    } = this.props;
    const team_name = globalUtil.getCurrTeamName();
    const team = userUtil.getTeamByTeamName(currUser, team_name);
   
    if(!teamUtil.canViewApp(team))  return <NoPermTip />

    if (this.id !== this.getGroupId()) {
      this.id = this.getGroupId();
      this.flash();
      return null;
    }

    if (!this.state.show) {
      return null;
    }

    return (<Main group_id={this.getGroupId()}/>);
  }
}
