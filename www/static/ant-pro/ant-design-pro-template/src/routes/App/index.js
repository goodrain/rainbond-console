import React, {PureComponent, Fragment} from 'react';
import moment from 'moment';
import PropTypes from 'prop-types';
import {connect} from 'dva';
import {Link, Switch, Route, routerRedux} from 'dva/router';
import {
    Row,
    Col,
    Card,
    Form,
    Button,
    Icon,
    Menu,
    Dropdown,
    notification,
    Modal,
    Input,
    Select
} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import {getRoutes} from '../../utils/utils';
import {getRouterData} from '../../common/router';
import Overview from './overview';
import Monitor from './monitor';
import Log from './log';
import Expansion from './expansion';
import Relation from './relation';
import Mnt from './mnt';
import Port from './port';
import Plugin from './plugin';
import Setting from './setting';
import ConfirmModal from '../../components/ConfirmModal';
import styles from './Index.less';
import globalUtil from '../../utils/global';
import appUtil from '../../utils/app';
import appStatusUtil from '../../utils/appStatus-util';
import VisitBtn from '../../components/VisitBtn';
import httpResponseUtil from '../../utils/httpResponse';
const FormItem = Form.Item;
const Option = Select.Option;
const ButtonGroup = Button.Group;
import {
    deploy,
    restart,
    start,
    stop,
    rollback,
    getDetail,
    getStatus
} from '../../services/app';

/*转移到其他应用组*/
@Form.create()
class MoveGroup extends PureComponent {
    handleSubmit = (e) => {
        e.preventDefault();
        const {form, currGroup} = this.props;
        form.validateFields((err, fieldsValue) => {
            if (err) 
                return;
            if (fieldsValue.group_id === currGroup) {
                notification.warning({message: "不能选择当前所在组"})
                return;
            }

            this
                .props
                .onOk(fieldsValue)
        });
    }
    onCancel = () => {
        this
            .props
            .onCancel();
    }
    render() {
        const {getFieldDecorator} = this.props.form;
        const initValue = this.props.currGroup;
        const groups = this.props.groups || [];
        return (
            <Modal
                title='修改应用所属组'
                visible={true}
                onOk={this.handleSubmit}
                onCancel={this.onCancel}>
                <Form onSubmit={this.handleSubmit}>

                    <FormItem label="">
                        {getFieldDecorator('group_id', {
                            initialValue: initValue || '',
                            rules: [
                                {
                                    required: true,
                                    message: '不能为空!'
                                }
                            ]
                        })(
                            <Select>
                                {groups.map((group) => {
                                    return <Option value={group.group_id}>{group.group_name}</Option>
                                })}
                            </Select>
                        )}
                    </FormItem>

                </Form>
            </Modal>
        )
    }
}

/*修改应用名称*/
@Form.create()
class EditName extends PureComponent {
    handleSubmit = (e) => {
        e.preventDefault();
        const {form} = this.props;
        form.validateFields((err, fieldsValue) => {
            if (err) 
                return;
            this
                .props
                .onOk(fieldsValue)
        });
    }
    onCancel = () => {
        this
            .props
            .onCancel();
    }
    render() {
        const {getFieldDecorator} = this.props.form;
        const initValue = this.props.name;
        return (
            <Modal
                title='修改应用名称'
                visible={true}
                onOk={this.handleSubmit}
                onCancel={this.onCancel}>
                <Form onSubmit={this.handleSubmit}>

                    <FormItem label="">
                        {getFieldDecorator('service_cname', {
                            initialValue: initValue || '',
                            rules: [
                                {
                                    required: true,
                                    message: '不能为空!'
                                }
                            ]
                        })(<Input placeholder="请输入新的应用名称"/>)}
                    </FormItem>
                </Form>
            </Modal>
        )
    }
}

/* 管理容器 */
@connect(({user, appControl, global}) => ({pods: appControl.pods}))
class ManageContainer extends PureComponent {
    componentDidMount() {}
    fetchPods = () => {
        const appAlias = this.props.app_alias;
        this
            .props
            .dispatch({
                type: 'appControl/fetchPods',
                payload: {
                    team_name: globalUtil.getCurrTeamName(),
                    app_alias: appAlias
                }
            })
    }
    handlePodClick = (item) => {
        var key = item.key;
        var podName = key.split('_')[0];
        var manageName = key.split('_')[1];
        var adPopup = window.open('about:blank');
        const appAlias = this.props.app_alias;
        if (podName && manageName) {
            this
                .props
                .dispatch({
                    type: 'appControl/managePod',
                    payload: {
                        team_name: globalUtil.getCurrTeamName(),
                        app_alias: appAlias,
                        pod_name: podName,
                        manage_name: manageName
                    },
                    callback: () => {
                        adPopup.location.href = "/console/teams/" + globalUtil.getCurrTeamName() + "/apps/" + appAlias + "/docker_console/";
                    }
                })
        }
    }
    handleVisibleChange = (visible) => {
        if (visible) {
            this.fetchPods();
        }
    }
    render() {
        const pods = this.props.pods || [];
        const renderPods = (
            <Menu onClick={this.handlePodClick}>
                {(pods || []).map((item, index) => {
                    return <Menu.Item key={item.pod_name + '_' + item.manage_name}>节点{index + 1}</Menu.Item>
                })
}

            </Menu>
        )
        return (
            <Dropdown
                onVisibleChange={this.handleVisibleChange}
                overlay={renderPods}
                placement="bottomRight">
                <Button>管理容器</Button>
            </Dropdown>
        )
    }
}

@connect(({user, appControl, global}) => ({currUser: user.currentUser, appDetail: appControl.appDetail, pods: appControl.pods, groups: global.groups}))
class Main extends PureComponent {
    constructor(arg) {
        super(arg);
        this.state = {
            actionIng: false,
            appDetail: {},
            status: {},
            showDeleteApp: false,
            pageStatus: '',
            showEditName: false,
            showMoveGroup: false
        }
        this.timer = null;
    }
    static childContextTypes = {
        isActionIng: PropTypes.func,
        appRolback: PropTypes.func
    }
    getChildContext() {
        return {
            isActionIng: (res) => {
                //this.setState({actionIng: res})
            },
            appRolback: (version) => {
                this.handleRollback(version)
            }
        };
    }
    componentDidMount() {
        const {dispatch} = this.props;
        this.loadDetail();
    }
    componentWillUnmount() {
        clearInterval(this.timer);
        this
            .props
            .dispatch({type: 'appControl/clearPods'})
        this
            .props
            .dispatch({type: 'appControl/clearDetail'})

    }

    loadDetail = () => {
        this
            .props
            .dispatch({
                type: 'appControl/fetchDetail',
                payload: {
                    team_name: globalUtil.getCurrTeamName(),
                    app_alias: this.getAppAlias()
                },
                callback: (appDetail) => {

                    if (!appUtil.isCreateComplete(appDetail)) {
                        if (!appUtil.isCreateFromCompose(appDetail)) {
                            this
                                .props
                                .dispatch(routerRedux.replace('/create/create-check/' + appDetail.service.service_alias));
                        } else {
                            this
                                .props
                                .dispatch(routerRedux.replace('/create/create-compose-check/' + appDetail.service.group_id + '/' + appDetail.service.compose_id));
                        }
                    } else {
                        this.getStatus();
                        this.timer = setInterval(() => {
                            this.getStatus();
                        }, 6000)
                    }

                },
                handleError: (data) => {
                    var code = httpResponseUtil.getCode(data);

                    if (code) {
                        //应用不存在
                        if (code === 404) {
                            this
                                .props
                                .dispatch(routerRedux.push('/exception/404'));
                        }

                        //访问的应用不在当前的数据中心里
                        if (code === 10404) {}

                        //访问的应用不在当前团队里
                        if (code === 10403) {}

                    }

                }
            })
    }
    getStatus = () => {
        getStatus({
            team_name: globalUtil.getCurrTeamName(),
            app_alias: this.getAppAlias()
        }).then((data) => {
            if (data) {
                this.setState({status: data.bean})
            }
        })
    }
    handleTabChange = (key) => {
        const {dispatch, match} = this.props;
        const {appAlias} = this.props.match.params;
        dispatch(routerRedux.push(`/app/${appAlias}/${key}`));
    }
    getChildCom = () => {
        if (this.ref) {
            return this
                .ref
                .getWrappedInstance()
        }
        return null;
    }
    getAppAlias() {
        return this.props.match.params.appAlias;
    }
    handleDeploy = () => {
        if (this.state.actionIng) {
            notification.warning({message: `正在执行操作，请稍后`});
            return;
        }
        deploy({
            team_name: globalUtil.getCurrTeamName(),
            app_alias: this.getAppAlias()
        }).then((data) => {
            if (data) {

                notification.success({message: `操作成功，部署中`});

                var child = this.getChildCom();
                if (child && child.onAction) {
                    child.onAction(data.bean);
                }
            }

        })
    }
    handleRollback = (version) => {
        if (this.state.actionIng) {
            notification.warning({message: `正在执行操作，请稍后`});
            return;
        }
        rollback({
            team_name: globalUtil.getCurrTeamName(),
            app_alias: this.getAppAlias(),
            deploy_version: version
        }).then((data) => {
            if (data) {
                notification.success({message: `操作成功，回滚中`});
                var child = this.getChildCom();
                if (child && child.onAction) {
                    child.onAction(data.bean);
                }
            }

        })
    }
    handleRestart = () => {
        if (this.state.actionIng) {
            notification.warning({message: `正在执行操作，请稍后`});
            return;
        }
        restart({
            team_name: globalUtil.getCurrTeamName(),
            app_alias: this.getAppAlias()
        }).then((data) => {
            if (data) {
                notification.success({message: `操作成功，重启中`});
                var child = this.getChildCom();
                if (child && child.onAction) {
                    child.onAction(data.bean);
                }
            }

        })
    }
    handleStart = () => {
        if (this.state.actionIng) {
            notification.warning({message: `正在执行操作，请稍后`});
            return;
        }
        start({
            team_name: globalUtil.getCurrTeamName(),
            app_alias: this.getAppAlias()
        }).then((data) => {
            if (data) {
                notification.success({message: `操作成功，启动中`});
                var child = this.getChildCom();
                if (child && child.onAction) {
                    child.onAction(data.bean);
                }
            }

        })
    }
    handleStop = () => {
        if (this.state.actionIng) {
            notification.warning({message: `正在执行操作，请稍后`});
            return;
        }
        stop({
            team_name: globalUtil.getCurrTeamName(),
            app_alias: this.getAppAlias()
        }).then((data) => {
            if (data) {
                notification.success({message: `操作成功，关闭中`});
                var child = this.getChildCom();
                if (child && child.onAction) {
                    child.onAction(data.bean);
                }
            }
        })
    }
    saveRef = (ref) => {
        this.ref = ref;
    }
    handleDropClick = (item) => {
        if (item.key === 'deleteApp') {
            this.onDeleteApp();
        }

        if (item.key === 'moveGroup') {
            this.showMoveGroup();
        }
    }
    onDeleteApp = () => {
        this.setState({showDeleteApp: true})
    }
    cancelDeleteApp = () => {
        this.setState({showDeleteApp: false})
    }
    handleDeleteApp = () => {
        const team_name = globalUtil.getCurrTeamName()
        this
            .props
            .dispatch({
                type: 'appControl/deleteApp',
                payload: {
                    team_name: team_name,
                    app_alias: this.getAppAlias()
                },
                callback: () => {
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
                        .dispatch(routerRedux.replace('/index'));
                }

            })
    }

    showEditName = () => {
        this.setState({showEditName: true})
    }
    hideEditName = () => {
        this.setState({showEditName: false})
    }
    handleEditName = (data) => {
        const team_name = globalUtil.getCurrTeamName();
        const appDetail = this.props.appDetail;
        const serviceAlias = appDetail.service.service_alias
        this
            .props
            .dispatch({
                type: 'appControl/editName',
                payload: {
                    team_name,
                    app_alias: serviceAlias,
                    ...data
                },
                callback: () => {
                    this.loadDetail();
                    this.hideEditName();
                }
            })
    }
    showMoveGroup = () => {
        this.setState({showMoveGroup: true})
    }
    hideMoveGroup = () => {
        this.setState({showMoveGroup: false})
    }
    handleMoveGroup = (data) => {

        const team_name = globalUtil.getCurrTeamName();
        const appDetail = this.props.appDetail;
        const serviceAlias = appDetail.service.service_alias
        this
            .props
            .dispatch({
                type: 'appControl/moveGroup',
                payload: {
                    team_name,
                    app_alias: serviceAlias,
                    ...data
                },
                callback: () => {
                    this.hideMoveGroup();
                    this.loadDetail();
                    this
                        .props
                        .dispatch({
                            type: 'global/fetchGroups',
                            payload: {
                                team_name: team_name
                            }
                        })

                    notification.success({message: '操作成功'})
                }
            })
    }
    renderTitle(name) {
        return <Fragment>
            {name || '-'}
            <Icon
                style={{
                cursor: 'pointer'
            }}
                onClick={this.showEditName}
                type="edit"/>
        </Fragment>
    }
    render() {
        const {index, projectLoading, activitiesLoading, currUser} = this.props;

        const team_name = globalUtil.getCurrTeamName();
        const appDetail = this.props.appDetail;
        const status = this.state.status || {};
        const groups = this.props.groups || [];

        if (!appDetail.service) {
            return null;
        }

        const menu = (
            <Menu onClick={this.handleDropClick}>
                <Menu.Item
                    key="moveGroup"
                    disabled={groups.length <= 1 || !appUtil.canMoveGroup(appDetail)}>修改所属组</Menu.Item>
                <Menu.Item key="deleteApp" disabled={!appUtil.canDelete(appDetail)}>删除</Menu.Item>
            </Menu>
        );

        const action = (
            <div>
                <ButtonGroup>
                    {(appStatusUtil.canVisit(status))
                        ? <VisitBtn app_alias={this.getAppAlias()}/>
                        : null}

                    {(appUtil.canManageApp(appDetail)) && !appStatusUtil.canStart(status)
                        ? <Button disabled={!appStatusUtil.canStop(status)} onClick={this.handleStop}>关闭</Button>
                        : null}
                    {(appUtil.canManageApp(appDetail)) && !appStatusUtil.canStop(status)
                        ? <Button disabled={!appStatusUtil.canStart(status)} onClick={this.handleStart}>启动</Button>
                        : null}
                    {(appUtil.canManageApp(appDetail))
                        ? <Button
                                disabled={!appStatusUtil.canRestart(status)}
                                onClick={this.handleRestart}>重启</Button>
                        : null
}
                    {(appUtil.canManageApp(appDetail)) && appStatusUtil.canManageDocker(status)
                        ? <ManageContainer app_alias={appDetail.service.service_alias}/>
                        : null
}

                    <Dropdown overlay={menu} placement="bottomRight">
                        <Button>其他操作<Icon type="ellipsis"/></Button>
                    </Dropdown>
                </ButtonGroup>
                {(appUtil.canManageApp(appDetail) && appStatusUtil.canDeploy(status))
                    ? <Button onClick={this.handleDeploy} type="primary">重新部署</Button>
                    : ''}

            </div>
        );

        const tabList = [
            {
                key: 'overview',
                tab: '总览'
            }, {
                key: 'monitor',
                tab: '监控'
            }, {
                key: 'log',
                tab: '日志'
            }, {
                key: 'expansion',
                tab: '伸缩'
            }, {
                key: 'relation',
                tab: '依赖'
            }, {
                key: 'mnt',
                tab: '存储'
            }, {
                key: 'port',
                tab: '端口'
            }, {
                key: 'plugin',
                tab: '扩展'
            }, {
                key: 'setting',
                tab: '设置'
            }
        ];

        const map = {
            overview: Overview,
            monitor: Monitor,
            log: Log,
            expansion: Expansion,
            relation: Relation,
            mnt: Mnt,
            port: Port,
            plugin: Plugin,
            setting: Setting
        }

        const {match, routerData, location} = this.props;
        var type = this.props.match.params.type;
        if (!type) {
            type = 'overview';
        }
        const Com = map[type];
        return (
            <PageHeaderLayout
                action={action}
                title={this.renderTitle(appDetail.service.service_cname)}
                onTabChange={this.handleTabChange}
                tabActiveKey={type}
                tabList={tabList}>

                {Com
                    ? <Com
                            status={this.state.status}
                            ref={this.saveRef}
                            {...this.props.match.params}
                            {...this.props}/>
                    : '参数错误'
}

                {this.state.showDeleteApp && <ConfirmModal
                    onOk={this.handleDeleteApp}
                    onCancel={this.cancelDeleteApp}
                    title="删除应用"
                    desc="确定要删除此应用吗？"
                    subDesc="此操作不可恢复"/>}
                {this.state.showEditName && <EditName
                    name={appDetail.service.service_cname}
                    onOk={this.handleEditName}
                    onCancel={this.hideEditName}
                    title="修改应用名称"/>}
                {this.state.showMoveGroup && <MoveGroup
                    currGroup={appDetail.service.group_id}
                    groups={groups}
                    onOk={this.handleMoveGroup}
                    onCancel={this.hideMoveGroup}/>}
            </PageHeaderLayout>
        );
    }
}

@connect(({user, groupControl}) => ({}), null, null, {pure: false})
export default class Index extends PureComponent {
    constructor(arg) {
        super(arg);
        this.id = '';
        this.state = {
            show: true
        }
    }
    getAlias = () => {
        return this.props.match.params.appAlias;
    }
    flash = () => {
        this.setState({
            show: false
        }, () => {
            this.setState({show: true})
        })
    }
    render() {
        if (this.id !== this.getAlias()) {
            this.id = this.getAlias();
            this.flash();
            return null;
        }

        if (!this.state.show) {
            return null;
        }

        return (<Main {...this.props}/>);
    }
}
