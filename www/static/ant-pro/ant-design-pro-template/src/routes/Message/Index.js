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
    Tag
} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import BasicListStyles from '../List/BasicList.less';
import styles from '../List/Articles.less';
import globalUtil from '../../utils/global';
import userUtil from '../../utils/user';
import cookie from '../../utils/cookie';
import messageUtil from '../../utils/message';
import {routerRedux} from 'dva/router';
const FormItem = Form.Item;


@connect(({user}) => ({currUser: user.currentUser}))
export default class Index extends PureComponent {
    constructor(arg) {
        super(arg);
        this.state = {
            loading: false,
            page: 1,
            pageSize: 10,
            list:[],
            total:0
        }
    }
    componentDidMount() {
        this.getuserMessage();
    }
    getuserMessage = (page_num,page_size,msg_type,is_read) => {
        this.props.dispatch({
            type: 'global/getuserMessage',
            payload: {
              team_name:globalUtil.getCurrTeamName(),
              page_num:this.state.page,
              page_size:this.state.pageSize,
              msg_type:''
            },
            callback: ((data) => {
                this.setState({list: data.list||[], total: data.total})
            })
          })
    }
    handlePageChange = (page) => {
        this.state.page = page;
        this.getuserMessage();
    }
    render() {
        const {currUser} = this.props;
        const {loading, list} = this.state;
        const team_name = globalUtil.getCurrTeamName();
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
            <PageHeaderLayout 
                breadcrumbList={[{
                    title: "首页",
                    href: `/`
                },{
                    title: `我的消息`,
                    href: ``
                }]}
                >
                <Card
                    style={{ marginTop: 24 }}
                    bordered={false}
                    bodyStyle={{ padding: '8px 32px 32px 32px' }}
                    >
                    <List
                        size="large"
                        pagination={paginationProps}
                        loading={list.length === 0 ? loading : false}
                        rowKey="id"
                        itemLayout="vertical"
                        dataSource={list}
                        renderItem={item => (
                        <List.Item
                            key={item.id}
                            actions={[
                            
                            ]}
                            extra={<div className={styles.listItemExtra} />}
                        >
                            <List.Item.Meta
                            title={(
                                <a className={styles.listItemMetaTitle} href={item.href}>{item.title}</a>
                            )}
                            description={
                                <span>
                                    <Tag>{messageUtil.getTypecn(item.msg_type)}</Tag>
                                </span>
                            }
                            />
                            <div style={{whiteSpace: 'pre-wrap'}} dangerouslySetInnerHTML={{__html: item.content}}></div>
                        </List.Item>
                        )}
                    />
                    </Card>
            </PageHeaderLayout>
        );
    }
}