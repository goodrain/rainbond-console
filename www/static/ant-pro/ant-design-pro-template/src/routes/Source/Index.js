import React, {PureComponent} from 'react';
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
    Radio
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

class AppList extends PureComponent {
    render() {
        const extraContent = (
            <div className={BasicListStyles.extraContent}>
                <RadioGroup defaultValue="all">
                    <RadioButton value="all">全部</RadioButton>
                    <RadioButton value="progress">已同步</RadioButton>
                    <RadioButton value="waiting">未同步</RadioButton>
                </RadioGroup>
                <Search
                    className={BasicListStyles.extraContentSearch}
                    placeholder="请输入名称进行搜索"
                    onSearch={() => ({})}/>
            </div>
        );

        const paginationProps = {
            pageSize: 5,
            total: 0
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

                    <List
                        size="large"
                        rowKey="id"
                        loading={false}
                        pagination={paginationProps}
                        dataSource={[{}]}
                        renderItem={item => (
                        <List.Item actions={[ < a > 编辑 < /a>]}>
                            <List.Item.Meta
                                avatar={< Avatar src = {
                                item.logo
                            }
                            shape = "square" size = "large" />}
                                title={"这是标题"}
                                description={"这是描述"}/>
                            <ListContent data={item}/>
                        </List.Item>
                    )}/>

                </Card>
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
    handleTakeInfo = () => {
        const {currUser} = this.props;
        this.setState({
            currStep: 1
        }, () => {
            window.open(`https://www.goodrain.com/#/check-console/${currUser.enterprise_id}`)
        })
    }
    renderContent = () => {
        const {currUser} = this.props;
        const {loading, isChecked} = this.state;

        if (loading) {
            return (
                <Card
                    style={{
                    padding: '100px 0',
                    textAlign: 'center'
                }}>
                    <Spin/>
                </Card>
            )
        }

        //如果未进行平台验证
        if (!isChecked) {
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
                        <AuthForm/>
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