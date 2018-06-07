import React, {PureComponent, Fragment} from 'react';
import {connect} from 'dva';
import {Link} from 'dva/router';
import globalUtil from '../../utils/global';
import userUtil from '../../utils/user';
import BasicListStyles from '../List/BasicList.less';
import {
    Row,
    Col,
    Card,
    List,
    Avatar,
    Button,
    Icon,
    Form,
    Input,
    Radio,
    notification,
} from 'antd';
const RadioButton = Radio.Button;
const RadioGroup = Radio.Group;
const {Search} = Input;

export default class CloudApp extends PureComponent {
    constructor(props){
        super(props);
        this.state = {
            pageSize:10,
            total:0,
            page:1,
            sync: false,
            loading: false
        }
    }
    componentDidMount = () => {
        this.handleSync();
    }
    handleClose = () => {
        this.props.onClose && this.props.onClose();
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
    handleSearch = (app_name) => {
        this.setState({
            app_name: app_name,
            page: 1
        }, () => {
            this.loadApps();
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
                        pageSize: this.state.pageSize
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
                    this.props.onSyncSuccess && this.props.onSyncSuccess();
                }
            })
    }
    handlePageChange = (page) => {
        this.setState({
            page: page
        }, () => {
            this.loadApps();
        })
    }
    render(){
        const paginationProps = {
            pageSize: this.state.pageSize,
            total: this.state.total,
            current: this.state.page,
            onChange: (pageSize) => {
                this.handlePageChange(pageSize)
            }
        };
        return <Card
                className={BasicListStyles.listCard}
                bordered={false}
                title={ <div>云端 <Search
                    className={BasicListStyles.extraContentSearch}
                    placeholder="请输入名称进行搜索"
                    onSearch={this.handleSearch}/></div>}
                style={{
            }}
                bodyStyle={{
                padding: '0 32px 40px 32px'
            }}
                extra={
                    <div className={BasicListStyles.extraContent}>
                        <RadioGroup>
                            <RadioButton onClick={this.handleClose}>关闭</RadioButton>
                        </RadioGroup>
                    </div>
                }>
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
                            <span>已同步</span>
                            </Fragment>
                            : <a
                                href="javascript:;"
                                onClick={() => {
                                this.handleLoadAppDetail(item)
                            }}>同步到市场</a>]}>
                        <List.Item.Meta
                            avatar={< Avatar src = {
                            item.pic || require("../../../public/images/app_icon.jpg")
                        }
                        shape = "square" size = "large" />}
                            title={item.group_name}
                            description={item.describe || '-'}/>

                    </List.Item>
                )}/>
            </Card>
    }
}