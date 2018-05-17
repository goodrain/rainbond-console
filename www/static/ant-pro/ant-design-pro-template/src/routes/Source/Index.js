import React, {PureComponent, Fragment} from 'react';
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
    Input,
    Spin,
    Steps,
    Radio,
    notification
} from 'antd';
import ConfirmModal from '../../components/ConfirmModal';
import Result from '../../components/Result';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import styles from './Index.less';
import BasicListStyles from '../List/BasicList.less';
import globalUtil from '../../utils/global';
import userUtil from '../../utils/user';
import cookie from '../../utils/cookie';
import {routerRedux} from 'dva/router';
const FormItem = Form.Item;
const {Step} = Steps;
const RadioButton = Radio.Button;
const RadioGroup = Radio.Group;
const {Search} = Input;

@Form.create()
class AuthForm extends PureComponent {
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
    render() {
        const formItemLayout = {
            labelCol: {
                span: 6
            },
            wrapperCol: {
                span: 18
            }
        };
        const {getFieldDecorator} = this.props.form;
        return (

            <Form
                style={{
                textAlign: 'left'
            }}
                layout="horizontal"
                hideRequiredMark>
                <Form.Item {...formItemLayout} label="企业ID">
                    {getFieldDecorator('market_client_id', {
                        initialValue: '',
                        rules: [
                            {
                                required: true,
                                message: '请输入您的企业ID'
                            }
                        ]
                    })(<Input placeholder="请输入您的企业ID"/>)}
                </Form.Item>
                <Form.Item {...formItemLayout} label="企业Token">
                    {getFieldDecorator('market_client_token', {
                        initialValue: '',
                        rules: [
                            {
                                required: true,
                                message: '请输入您的企业Token'
                            }
                        ]
                    })(<Input placeholder="请输入您的企业Token"/>)}
                </Form.Item>
                <Row>
                    <Col span="6"></Col>
                    <Col span="18" style={{}}>
                        <Button onClick={this.handleSubmit} type="primary">提交认证</Button>
                    </Col>
                </Row>
            </Form>
        )
    }
}

@connect()
class AppList extends PureComponent {
    constructor(props) {
        super(props);
        this.state = {
            sync: false,
            page: 1,
            pageSize: 10,
            app_name: '',
            apps: [],
            loading: true,
            total: 0,
            type: "",
            showOfflineApp: null
        }
    }
    componentDidMount = () => {
        this.loadApps();
    }
    handleSync = () => {
        this.setState({
            sync: true
        }, () => {
            this
                .props
                .dispatch({
                    type: 'global/syncMarketApp',
                    payload: {
                        team_name: globalUtil.getCurrTeamName()
                    }
                }).then(()=>{
                    this.setState({
                        sync: false
                    }, () => {
                        this.loadApps();
                    })
                })
        })
    }
    loadApps = () => {
        this.setState({
            loading: true
        }, () => {
            this
                .props
                .dispatch({
                    type: 'global/getMarketApp',
                    payload: {
                        app_name: this.state.app_name,
                        page: this.state.page,
                        pageSize: this.state.pageSize,
                        is_complete: this.state.type
                    },
                    callback: (data) => {
                        this.setState({
                            apps: data.list || [],
                            loading: false,
                            total: data.total
                        })
                    }
                })
        })
    }
    handlePageChange = (page) => {
        this.setState({
            page: page
        }, () => {
            this.loadApps();
        })
    }
    handleSearch = (app_name) => {
        this.setState({
            app_name: app_name,
            page: 1
        }, () => {
            this.loadApps();
        })
    }
    handleLoadAppDetail = (data) => {
        this
            .props
            .dispatch({
                type: 'global/syncMarketAppDetail',
                payload: {
                    team_name: globalUtil.getCurrTeamName(),
                    body: [
                        {
                            group_key: data.group_key,
                            version: data.version,
                            template_version: data.template_version

                        }
                    ]
                },
                callback: (data) => {
                    notification.success({message: '操作成功'});
                    this.loadApps();
                }
            })
    }
    handleTypeChange = (e) => {
        this.setState({type: e.target.value, page: 1}, () => {
            this.loadApps();
        })
    }
    handleOfflineApp = () => {
        const app = this.state.showOfflineApp;
        this.props.dispatch({
            type: 'global/offlineMarketApp',
            payload:{
                app_id: app.ID
            },
            callback: () => {
                notification.success({
                    message: '卸载成功'
                })
                this.hideOfflineApp();
                this.loadApps();
            }
        })
    }
    showOfflineApp = (app) => {
        this.setState({showOfflineApp: app})
    }
    hideOfflineApp = () => {
        this.setState({showOfflineApp: null})
    }
    render() {
        const extraContent = (
            <div className={BasicListStyles.extraContent}>
                <RadioGroup onChange={this.handleTypeChange} defaultValue={this.state.type}>
                    <RadioButton value="">全部</RadioButton>
                    <RadioButton value={true}>已下载</RadioButton>
                    <RadioButton value={false}>未下载</RadioButton>
                </RadioGroup>
                <Search
                    className={BasicListStyles.extraContentSearch}
                    placeholder="请输入名称进行搜索"
                    onSearch={this.handleSearch}/>
            </div>
        );

        const paginationProps = {
            pageSize: this.state.pageSize,
            total: this.state.total,
            current: this.state.page,
            onChange: (pageSize) => {
                this.handlePageChange(pageSize)
            }
        };

        const ListContent = ({
            data: {
                owner,
                createdAt,
                percent,
                status
            }
        }) => (
            <div className={BasicListStyles.listContent}></div>
        );

        return (
            <div className={BasicListStyles.standardList}>
                <Card
                    className={BasicListStyles.listCard}
                    bordered={false}
                    title="云市应用列表"
                    style={{
                    marginTop: 24
                }}
                    bodyStyle={{
                    padding: '0 32px 40px 32px'
                }}
                    extra={extraContent}>
                    <Button
                        disabled={this.state.sync}
                        onClick={this.handleSync}
                        type="dashed"
                        style={{
                        width: '100%',
                        marginBottom: 8
                    }}><Icon
                        className={this.state.sync
                ? 'roundloading'
                : ''}
                        type="sync"/>从好雨云市同步应用信息</Button>
                    <List
                        size="large"
                        rowKey="id"
                        loading={this.state.loading}
                        pagination={paginationProps}
                        dataSource={this.state.apps}
                        renderItem={item => (
                        <List.Item
                            actions={[item.is_complete
                                ? <Fragment>
                                 <a
                                    style={{marginRight: 8}}
                                        href="javascript:;"
                                        onClick={() => {
                                        this.handleLoadAppDetail(item)
                                    }}>更新应用</a>
                                    <a
                                        href="javascript:;"
                                        onClick={() => {
                                        this.showOfflineApp(item)
                                    }}>卸载应用</a>
                                 </Fragment>
                                : <a
                                    href="javascript:;"
                                    onClick={() => {
                                    this.handleLoadAppDetail(item)
                                }}>下载应用</a>]}>
                            <List.Item.Meta
                                avatar={< Avatar src = {
                                item.pic || require("../../../public/images/app_icon.jpg")
                            }
                            shape = "square" size = "large" />}
                                title={item.group_name}
                                description={item.describe || '-'}/>
                            <ListContent data={item}/>
                        </List.Item>
                    )}/>

                </Card>
                {this.state.showOfflineApp && <ConfirmModal onOk={this.handleOfflineApp} desc={`确定要卸载才应用吗?`} subDesc="卸载后其他人将无法安装此应用" title={'卸载应用'} onCancel={this.hideOfflineApp} />}
            </div>
        )
    }
}
@connect(({user}) => ({currUser: user.currentUser}))export default class Index extends PureComponent {
    constructor(arg) {
        super(arg);
        this.state = {
            isChecked: true,
            loading: false,
            currStep: 0
        }
    }
    componentDidMount() {}
    handleTakeInfo = () => {
        const {currUser} = this.props;
        this.setState({
            currStep: 1
        }, () => {
            window.open(`https://www.goodrain.com/spa/#/check-console/${currUser.enterprise_id}`)
        })
    }
    handleAuthEnterprise = (vals) => {
        const {currUser} = this.props;
        this
            .props
            .dispatch({
                type: 'global/authEnterprise',
                payload: {
                    team_name: globalUtil.getCurrTeamName(),
                    enterprise_id: currUser.enterprise_id,
                    ...vals
                },
                callback: () => {

                    this
                        .props
                        .dispatch({type: 'user/fetchCurrent'})
                }
            })
    }
    renderContent = () => {
        const {currUser} = this.props;
        const {loading, isChecked} = this.state;

        //不是系统管理员
        if (!userUtil.isSystemAdmin(currUser)) {
            this
                .props
                .dispatch(routerRedux.replace(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/Exception/403`))
            return null;
        }

        //如果未进行平台验证
        if (currUser.is_enterprise_active !== 1) {
            const step = this.state.currStep;
            const extra = (
                <div>
                    <Steps
                        style={{
                        margin: '0 auto',
                        width: 'calc(100% - 80px)'
                    }}
                        progressDot
                        current={step}>
                        <Step title={"获取认证信息"}>yyy</Step>
                        <Step title={"填写认证信息"}></Step>
                    </Steps>
                    <div
                        style={{
                        textAlign: 'center',
                        padding: '80px 0',
                        display: step === 0
                            ? 'block'
                            : 'none'
                    }}>
                        <p>到好雨官方获取您企业的认证信息，如未登录需要先进行登录</p>
                        <Button onClick={this.handleTakeInfo} type="primary">去获取</Button>
                    </div>

                    <div
                        style={{
                        textAlign: 'center',
                        padding: '80px 0',
                        width: '350px',
                        margin: '0 auto',
                        display: step === 1
                            ? 'block'
                            : 'none'
                    }}>
                        <AuthForm onSubmit={this.handleAuthEnterprise}/>
                    </div>
                </div>
            );

            return (
                <Card>
                    <Result
                        type="error"
                        title="需要进行互联认证"
                        description="请按以下步骤提示进行平台认证"
                        extra={extra}
                        style={{
                        marginTop: 48,
                        marginBottom: 16
                    }}/>
                </Card>
            )
        }

        return <AppList/>
    }
    render() {
        const {currUser} = this.props;
        const {loading} = this.state;

        const team_name = globalUtil.getCurrTeamName();

        const pageHeaderContent = (
            <div className={styles.pageHeaderContent}>
                <div className={styles.content}>
                    <div>将当前云帮平台和好雨云市进行互联，同步应用，插件，数据中心等资源</div>
                    <div>应用下载完成后，方可在 创建应用->从应用市场安装 中看到</div>
                </div>
            </div>
        );

        return (
            <PageHeaderLayout content={pageHeaderContent}>
                {this.renderContent()}
                
            </PageHeaderLayout>
        );
    }
}