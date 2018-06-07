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
    notification,
    Menu
} from 'antd';
import Result from '../../components/Result';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import styles from './Index.less';
import BasicListStyles from '../List/BasicList.less';
import globalUtil from '../../utils/global';
import userUtil from '../../utils/user';
import {routerRedux} from 'dva/router';
import AppList from './AppList';
import PluginList from './PluginList'

const FormItem = Form.Item;
const {Step} = Steps;
const RadioButton = Radio.Button;
const RadioGroup = Radio.Group;
const {Search} = Input;



@connect(({user}) => ({currUser: user.currentUser}))
export default class Index extends PureComponent {
    constructor(arg) {
        super(arg);
        
        let params = this.getParam();
        this.state = {
            isChecked: true,
            loading: false,
            currStep: 0,
            scope: params.type || 'app'
        }
    }
    componentDidMount() {}
    getParam() {
        return this.props.match.params;
    }
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
    handleTabChange = (key) => {
        this.setState({scope: key})
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
        if (currUser.is_enterprise_active === 1) {
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

        if(this.state.scope === 'app'){
            return <AppList {...this.props}/>
        }

        if(this.state.scope === 'plugin'){
            return <PluginList {...this.props}/>
        }

        
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

        const tabList = [
            {
              key: 'app',
              tab: '应用'
            }, {
              key: 'plugin',
              tab: '插件'
            }
        ];

        return (
            <PageHeaderLayout 
                tabList={tabList}
                tabActiveKey={this.state.scope}
                onTabChange={this.handleTabChange}
                content={pageHeaderContent}>
                {this.renderContent()}
            </PageHeaderLayout>
        );
    }
}