import React, {PureComponent} from 'react';
import moment from 'moment';
import {connect} from 'dva';
import {Link} from 'dva/router';
import {
  Row,
  Col,
  Card,
  List,
  Avatar,
  Button,
  Icon,
  Modal,
  Form,
  Input
} from 'antd';
import TeamMemberTable from '../../components/TeamMemberTable';
import TeamRoleTable from '../../components/TeamRoleTable';
import ConfirmModal from '../../components/ConfirmModal';
import AddMember from '../../components/AddMember';
import AddRole from '../../components/AddRole';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import TeamPermissionSelect from '../../components/TeamPermissionSelect';
import styles from './index.less';
import globalUtil from '../../utils/global';
import userUtil from '../../utils/user';
import teamUtil from '../../utils/team';
import OpenRegion from '../../components/OpenRegion';
import cookie from '../../utils/cookie';
import {routerRedux} from 'dva/router';
import ScrollerX from '../../components/ScrollerX';
const FormItem = Form.Item;
@Form.create()
class MoveTeam extends PureComponent {
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
    const initValue = this.props.teamAlias;
    return (
      <Modal
        title='修改团队名称'
        visible={true}
        onOk={this.handleSubmit}
        onCancel={this.onCancel}>
        <Form onSubmit={this.handleSubmit}>

          <FormItem label="">
            {getFieldDecorator('new_team_alias', {
              initialValue: initValue || '',
              rules: [
                {
                  required: true,
                  message: '不能为空!'
                }
              ]
            })(<Input placeholder="请输入新的团队名称"/>)}
          </FormItem>

        </Form>
      </Modal>
    )
  }
}

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

@connect(({user, teamControl, loading}) => ({currUser: user.currentUser, teamControl, projectLoading: loading.effects['project/fetchNotice'], activitiesLoading: loading.effects['activities/fetchList'], regions: teamControl.regions}))
export default class Index extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {
      showEditName: false,
      showDelTeam: false,
      showAddMember: false,
      toDeleteMember: null,
      toEditAction: null,
      toMoveTeam: null,
      openRegion: false,
      showExitTeam: false,
      page: 1,
      pageSize: 8,
      total: 0,
      members: [],
      roles:[],
      rolePage: 1,
      roleTotal: 0,
      rolePageSize: 8,
      showAddRole: false,
      deleteRole: null,
      editRole: null
    }
  }
  componentDidMount() {
    this.loadMembers();
    this.loadRoles();
    this
      .props
      .dispatch({type: 'teamControl/fetchAllPerm'})
    this.fetchRegions();
  }
  loadRoles = () => {
    const {dispatch} = this.props;
    const team_name = globalUtil.getCurrTeamName();
    const region_name = globalUtil.getCurrRegionName();
    dispatch({
      type: 'teamControl/getRoles',
      payload: {
        team_name: team_name,
        page_size: this.state.rolePageSize,
        page: this.state.rolePage
      },
      callback: (data) => {
        this.setState({
          roles: data.list || [],
          roleTotal: data.total
        })
      }
    })
  }
  loadMembers = () => {
    const {dispatch} = this.props;
    const team_name = globalUtil.getCurrTeamName();
    const region_name = globalUtil.getCurrRegionName();
    dispatch({
      type: 'teamControl/fetchMember',
      payload: {
        team_name: team_name,
        region_name: region_name,
        page_size: this.state.pageSize,
        page: this.state.page
      },
      callback: (data) => {
        this.setState({
          members: data.list || [],
          total: data.total
        })
      }
    })
  }
  fetchRegions = () => {
    const {dispatch} = this.props;
    const team_name = globalUtil.getCurrTeamName();

    dispatch({
      type: 'teamControl/fetchRegions',
      payload: {
        team_name: team_name
      }
    })
  }
  componentWillUnmount() {}
  showEditName = () => {
    this.setState({showEditName: true})
  }
  hideEditName = () => {
    this.setState({showEditName: false})
  }
  showAddMember = () => {
    this.setState({showAddMember: true})
  }
  hideAddMember = () => {
    this.setState({showAddMember: false})
  }
  showAddRole = () => {
    this.setState({showAddRole: true})
  }
  hideAddRole = () => {
    this.setState({showAddRole: false})
  }
  handleAddRole = (values) => {
    const team_name = globalUtil.getCurrTeamName();
    this
      .props
      .dispatch({
        type: 'teamControl/createRole',
        payload: {
          team_name,
          ...values
        },
        callback: () => {
          this.loadRoles();
          this.hideAddRole();
        }
      })
  }
  showExitTeam = () => {
    this.setState({showExitTeam: true})
  }
  hideExitTeam = () => {
    this.setState({showExitTeam: false})
  }
  handleExitTeam = () => {
    const team_name = globalUtil.getCurrTeamName();
    this
      .props
      .dispatch({
        type: 'teamControl/exitTeam',
        payload: {
          team_name
        },
        callback: () => {
          cookie.remove('team');
          cookie.remove('region_name');
          this
            .props
            .dispatch(routerRedux.replace(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/index`))
          location.reload();
        }
      })
  }
  showDelTeam = () => {
    this.setState({showDelTeam: true})
  }
  hideDelTeam = () => {
    this.setState({showDelTeam: false})
  }
  handleEditName = (data) => {
    const team_name = globalUtil.getCurrTeamName();
    this
      .props
      .dispatch({
        type: 'teamControl/editTeamAlias',
        payload: {
          team_name,
          ...data
        },
        callback: () => {
          this
            .props
            .dispatch({type: 'user/fetchCurrent'})
          this.hideEditName();
        }
      })
  }
  handleDelTeam = () => {
    const team_name = globalUtil.getCurrTeamName();
    this
      .props
      .dispatch({
        type: 'teamControl/delTeam',
        payload: {
          team_name
        },
        callback: () => {
          location.hash = "/index";
          location.reload();
        }
      })
  }
  handleAddMember = (values) => {

    this
      .props
      .dispatch({
        type: 'teamControl/addMember',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          user_ids: values
            .user_ids
            .map((item) => {
              return item.key
            })
            .join(','),
          role_ids: values.role_ids.join(',')
        },
        callback: () => {
          this.loadMembers();
          this.hideAddMember();
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
        type: 'teamControl/delMember',
        payload: {
          team_name: team_name,
          user_ids: this.state.toDeleteMember.user_id
        },
        callback: () => {

          this.loadMembers();
          this.hideDelMember();
        }
      })
  }
  onEditAction = (member) => {
    this.setState({toEditAction: member})
  }
  hideEditAction = () => {
    this.setState({toEditAction: null})
  }
  handleEditAction = (data) => {
    const team_name = globalUtil.getCurrTeamName();
    this
      .props
      .dispatch({
        type: 'teamControl/editMember',
        payload: {
          team_name: team_name,
          user_name: data.user_name,
          role_ids: data.role_ids.join(',')
        },
        callback: () => {
          this.loadMembers();
          this.hideEditAction();
        }
      })
  }
  onMoveTeam = (member) => {
    this.setState({toMoveTeam: member})
  }
  hideMoveTeam = () => {
    this.setState({toMoveTeam: null})
  }
  handleMoveTeam = ({identity}) => {
    const team_name = globalUtil.getCurrTeamName();
    this
      .props
      .dispatch({
        type: 'teamControl/moveTeam',
        payload: {
          team_name: team_name,
          user_name: this.state.toMoveTeam.user_name
        },
        callback: () => {
          this.loadMembers();
          this.hideMoveTeam();
        }
      })
  }
  onOpenRegion = () => {
    this.setState({openRegion: true})
  }
  cancelOpenRegion = () => {
    this.setState({openRegion: false})
  }
  handleOpenRegion = (regions) => {
    const team_name = globalUtil.getCurrTeamName();
    this
      .props
      .dispatch({
        type: 'teamControl/openRegion',
        payload: {
          team_name: team_name,
          region_names: regions.join(',')
        },
        callback: () => {
          this.fetchRegions();
          this
            .props
            .dispatch({type: 'user/fetchCurrent'})
        }
      })
  }
  hanldePageChange = (page) => {
    this.setState({
      page: page
    }, () => {
      this.loadMembers();
    })
  }
  hanldeRolePageChange = (page) => {
    this.setState({
      rolePage: page
    }, () => {
      this.loadRoles();
    })
  }
  onEditRole = (item) => {
    this.setState({editRole: item})
  }
  handleEditRole = (values) => {
    const team_name = globalUtil.getCurrTeamName();
    this
      .props
      .dispatch({
        type: 'teamControl/editRole',
        payload: {
          team_name: team_name,
          role_id: this.state.editRole.role_id,
          ...values
        },
        callback: () => {
           this.hideEditRole();
           this.loadRoles();
        }
      })
  }
  hideEditRole = () => {
    this.setState({editRole: null})
  }
  onDelRole = (item) => {
    this.setState({deleteRole: item})
  }
  handleDelRole = () => {
    const team_name = globalUtil.getCurrTeamName();
    this
      .props
      .dispatch({
        type: 'teamControl/removeRole',
        payload: {
          team_name: team_name,
          role_id: this.state.deleteRole.role_id
        },
        callback: () => {
           this.hideDelRole();
           this.loadRoles();
        }
      })
  }
  hideDelRole = () => {
    this.setState({deleteRole: null})
  }
  render() {
    const {
      index,
      projectLoading,
      activitiesLoading,
      currUser,
      teamControl,
      regions
    } = this.props;

    const team_name = globalUtil.getCurrTeamName();
    const team = userUtil.getTeamByTeamName(currUser, team_name);
    const roles = this.state.roles;

    const pageHeaderContent = (
      <div className={styles.pageHeaderContent}>
        <div className={styles.avatar}>
          <Avatar size="large" src={require("../../../public/images/team-icon.png")}/>
        </div>
        <div className={styles.content}>
          <div className={styles.contentTitle}>{team.team_alias} {teamUtil.canEditTeamName(team) && <Icon onClick={this.showEditName} type="edit"/>}</div>
          <div>创建于 {moment(team.create_time).format("YYYY-MM-DD")}</div>
        </div>
      </div>
    );
    const extraContent = (
      <div className={styles.extraContent}>
        <div className={styles.extraBtns}>
          <Button onClick={this.showExitTeam} type="dashed">退出团队</Button>
          {< Button disabled = {
            !teamUtil.canDeleteTeam(team)
          }
          onClick = {
            this.showDelTeam
          }
          type = "dashed" > 删除团队 < /Button>}
        </div>
      </div>
    );
    const members = this.state.members;

    const pagination = {
      current: this.state.page,
      pageSize: this.state.pageSize,
      total: this.state.total,
      onChange: (v) => {
        this.hanldePageChange(v);
      }
    };

    const RolePagination = {
      current: this.state.rolePage,
      pageSize: this.state.rolePageSize,
      total: this.state.roleTotal,
      onChange: (v) => {
        this.hanldeRolePageChange(v);
      }
    };

    return (
      
      <PageHeaderLayout content={pageHeaderContent} extraContent={extraContent}>
        <Card
          className={styles.projectList}
          style={{
          marginBottom: 24
        }}
          title="已开通数据中心"
          bordered={false}
          extra={teamUtil.canAddRegion(team) ? < a href = "javascript:;" onClick = {
          this.onOpenRegion
        } > 开通数据中心 < /a> : null}
          loading={projectLoading}
          bodyStyle={{
          padding: 0
        }}>
          {(regions || []).map(item => (
            <Card.Grid className={styles.projectGrid} key={item.id}>
              <Card bodyStyle={{
                padding: 0
              }} bordered={false}>
                <Card.Meta
                  title={(
                  <div className={styles.cardTitle}>
                    <Avatar size="small" src={item.logo}/>
                    <a href="javascript:;">{item.region_alisa}</a>
                  </div>
                )}
                  description={item.desc || '-'}/>
                <div className={styles.projectItemContent}>
                  <span className={styles.datetime}>
                    开通于 {moment(item.create_time).format("YYYY年-MM月-DD日")}
                  </span>

                </div>
              </Card>
            </Card.Grid>
          ))
}
          {(!regions || !regions.length)
            ? <p
                style={{
                textAlign: 'center',
                paddingTop: 20
              }}>暂无数据中心</p>
            : ''
}
        </Card>

        <Card
          style={{
            marginBottom: 24
          }}
          bodyStyle={{
          paddingTop: 12
        }}
          bordered={false}
          title="团队成员"
          extra={teamUtil.canAddMember(team)
          ? <a href="javascript:;" onClick={this.showAddMember}>添加成员</a>
          : null}>
          <ScrollerX sm={600}>
            <TeamMemberTable
              pagination={pagination}
              team={team}
              onMoveTeam={this.onMoveTeam}
              onDelete={this.onDelMember}
              onEditAction={this.onEditAction}
              list={members}/>
          </ScrollerX>
        </Card>

        <Card
        bodyStyle={{
        paddingTop: 12
        }}
        bordered={false}
        title="角色管理 "
        extra={teamUtil.canAddRole(team) && <a href="javascript:;" onClick={this.showAddRole}>添加角色</a>}>
        <ScrollerX sm={600}>
          <TeamRoleTable
            pagination={RolePagination}
            team={team}
            onDelete={this.onDelRole}
            onEdit={this.onEditRole}
            list={roles}/>
        </ScrollerX>
        </Card>

        {this.state.showEditName && <MoveTeam
          teamAlias={team.team_alias}
          onSubmit={this.handleEditName}
          onCancel={this.hideEditName}/>}
        {this.state.showDelTeam && <ConfirmModal
          onOk={this.handleDelTeam}
          title="删除团队"
          subDesc="此操作不可恢复"
          desc="确定要删除此团队吗？"
          onCancel={this.hideDelTeam}/>}
        {this.state.showExitTeam && <ConfirmModal
          onOk={this.handleExitTeam}
          title="退出团队"
          subDesc="此操作不可恢复"
          desc="确定要退出此团队吗?"
          onCancel={this.hideExitTeam}/>}
        {this.state.toDeleteMember && <ConfirmModal
          onOk={this.handleDelMember}
          title="删除成员"
          subDesc="此操作不可恢复"
          desc="确定要删除此成员吗？"
          onCancel={this.hideDelMember}/>}
        {this.state.toMoveTeam && <ConfirmModal
          onOk={this.handleMoveTeam}
          title="移交团队"
          subDesc="移交后您将失去所有权"
          desc={"确定要把团队移交给 " + this.state.toMoveTeam.user_name + " 吗？"}
          onCancel={this.hideMoveTeam}/>}

        {this.state.showAddMember && <AddMember
          roles={this.state.roles}
          onOk={this.handleAddMember}
          onCancel={this.hideAddMember}/>}

          {this.state.toEditAction && <AddMember
            roles={this.state.roles}
            data={this.state.toEditAction}
            onOk={this.handleEditAction}
            onCancel={this.hideEditAction}/>}


          {this.state.showAddRole && <AddRole
            actions={teamControl.actions}
            onOk={this.handleAddRole}
            onCancel={this.hideAddRole}/>}

            {this.state.editRole && <AddRole
              title="修改角色"
              data={this.state.editRole}
              actions={teamControl.actions}
              onOk={this.handleEditRole}
              onCancel={this.hideEditRole}/>}

            {this.state.deleteRole && <ConfirmModal
              onOk={this.handleDelRole}
              title="删除角色"
              subDesc="此操作不可恢复"
              desc={"确定要删除角色 （" + this.state.deleteRole.role_name + "） 吗？"}
              onCancel={this.hideDelRole}/>}


        {this.state.openRegion && <OpenRegion onSubmit={this.handleOpenRegion} onCancel={this.cancelOpenRegion}/>}
      </PageHeaderLayout>
    );
  }
}
