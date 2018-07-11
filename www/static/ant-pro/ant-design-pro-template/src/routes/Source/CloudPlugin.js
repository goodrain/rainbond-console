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

export default class CloudPlugin extends PureComponent {
    constructor(props){
        super(props);
        this.state = {
            pageSize:10,
            total:0,
            page:1,
            loading: false,
            plugins: []
        }
    }
    componentDidMount = () => {
        this.handleSync();
    }
    handleSync = () => {
        this.setState({
            sync: true
        }, () => {
            this
            .props
            .dispatch({
                type: 'global/syncMarketPlugins',
                payload: {
                    team_name: globalUtil.getCurrTeamName()
                },
                callback: (data) => {
                    this.setState({
                        sync: false,
                        plugins: data.list || [],
                        loading: false,
                        total: data.total
                    })
                }
            })
        })
    }
    handleClose = () => {
        this.props.onClose && this.props.onClose();
    }
    handleSearch = (app_name) => {
        this.setState({
            app_name: app_name,
            page: 1
        }, () => {
            this.loadPlugins();
        })
    }
    handleLoadPluginDetail = (data) => {
        this
            .props
            .dispatch({
                type: 'global/syncMarketPluginTmp',
                payload: {
                    plugin_key: data.plugin_key,
                    version: data.version
                },
                callback: (data) => {
                    notification.success({message: '操作成功'});
                    this.handleSync();
                    this.props.onSyncSuccess && this.props.onSyncSuccess();
                }
            })
    }
    handlePageChange = (page) => {
        this.setState({
            page: page
        }, () => {
            this.handleSync();
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
                    dataSource={this.state.plugins}
                    renderItem={item => (
                    <List.Item
                        actions={[item.is_complete
                            ? <Fragment>
                            <span>已同步</span>
                            </Fragment>
                            : <a
                                href="javascript:;"
                                onClick={() => {
                                this.handleLoadPluginDetail(item)
                            }}>同步到市场</a>]}>
                        <List.Item.Meta
                            avatar={< Avatar src = {
                            item.pic || require("../../../public/images/app_icon.jpg")
                        }
                        shape = "square" size = "large" />}
                            title={item.plugin_name}
                            description={item.desc || '-'}/>

                    </List.Item>
                )}/>
            </Card>
    }
}