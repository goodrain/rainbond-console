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
  Form,
  Input,
  Select,
  Button,
  Icon
} from 'antd';
import IndexTable from '../../components/IndexTable';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import EditableLinkGroup from '../../components/EditableLinkGroup';

import {Radar} from '../../components/Charts';
import styles from './Index.less';
import globalUtil from '../../utils/global';
import userUtil from '../../utils/user';

const FormItem = Form.Item;
const Option = Select.Option;

const links = [
  {
    title: '自定义源码',
    href: '/create/code/custom'
  }, {
    title: '好雨代码仓库',
    href: '/create/code/goodrain'
  }, {
    title: 'github项目',
    href: '/create/code/github'
  }, {
    title: '指定镜像',
    href: '/create/image/custom'
  }, {
    title: 'DockerRun命令',
    href: '/create/image/dockerrun'
  }, {
    title: 'Dockercompose',
    href: '/create/image/Dockercompose'
  }
];

@connect(({user, index, loading}) => ({
  currUser: user.currentUser,
  index,
  events: index.events,
  pagination: index.pagination,
  projectLoading: loading.effects['project/fetchNotice'],
  activitiesLoading: loading.effects['activities/fetchList']
}))
@Form.create()
export default class Index extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {}
  }
  componentDidMount() {

    this.loadOverview();
    this.loadApps();
    this.loadEvents();
    this.timer = setInterval(() => {
      this.loadApps();
      this.loadOverview();
    }, 10000)
  }
  loadOverview = () => {
    const {dispatch, index} = this.props;
    const team_name = globalUtil.getCurrTeamName();
    const region_name = globalUtil.getCurrRegionName();
    dispatch({
      type: 'index/fetchOverview',
      payload: {
        team_name: team_name,
        region_name: region_name

      }
    });
  }
  loadEvents = () => {
    const team_name = globalUtil.getCurrTeamName();
    this
      .props
      .dispatch({
        type: 'index/fetchEvents',
        payload: {
          team_name: team_name
        }
      });
  }
  loadApps = () => {
    const {dispatch, form, index} = this.props;
    const team_name = globalUtil.getCurrTeamName();
    const region_name = globalUtil.getCurrRegionName();

    const pagination = index.pagination;
    let searchKey = {
      searchKey: '',
      service_status: ''
    }
    //获取搜索信息
    form.validateFields((err, fieldsValue) => {
      searchKey = fieldsValue;
    });

    let payload = {
      team_name: team_name,
      region_name: region_name,
      page: index.pagination.currentPage,
      page_size: index.pagination.pageSize,
      order: (index.pagination.order || '').replace('end', ''),
      fields: index.pagination.fields,
      ...searchKey
    }

    dispatch({type: 'index/fetchApps', payload: payload});

  }
  componentWillUnmount() {
    clearInterval(this.timer)
  }
  renderSimpleForm() {
    const {getFieldDecorator} = this.props.form;
    const status = [
      {
        value: 'all',
        text: '全部'
      }, {
        value: 'running',
        text: '运行中'
      }, {
        value: 'closed',
        text: '已关闭'
      }
    ]
    return (
      <Form onSubmit={this.handleSearch} layout="inline">
        <Row gutter={{
          md: 8,
          lg: 24,
          xl: 48
        }}>
          <Col md={8} sm={24}>
            <FormItem label="应用名称">
              {getFieldDecorator('query_key')(<Input placeholder="请输入"/>)}
            </FormItem>
          </Col>
          <Col md={8} sm={24}>
            <FormItem label="应用状态">
              {getFieldDecorator('service_status', {initialValue: 'all'})(
                <Select placeholder="请选择">
                  {status.map((item) => {
                    return <Option value={item.value}>{item.text}</Option>
                  })
}
                </Select>
              )}
            </FormItem>
          </Col>
          <Col md={8} sm={24}>
            <span className={styles.submitButtons}>
              <Button type="primary" htmlType="submit">查询</Button>
              <Button
                style={{
                marginLeft: 8
              }}
                onClick={this.handleFormReset}>重置</Button>
            </span>
          </Col>
        </Row>
      </Form>
    );
  }
  handleFormReset = () => {
    const {form, dispatch} = this.props;
    form.resetFields();
    dispatch({
      type: 'index/savePage',
      payload: {
        currentPage: 1
      }
    })
    setTimeout(() => {
      this.loadApps();
    })
  }
  handleSearch = (e) => {
    e.preventDefault();
    this.loadApps();
    const {dispatch} = this.props;
    dispatch({
      type: 'index/savePage',
      payload: {
        currentPage: 1
      }
    })
    setTimeout(() => {
      this.loadApps();
    })

  }
  handleListChange = (pagination, filtersArg, sorter) => {
    const {dispatch} = this.props;
    dispatch({
      type: 'index/savePage',
      payload: {
        currentPage: pagination.current,
        pageSize: pagination.pageSize,
        order: sorter.field
          ? sorter.order
          : '',
        fields: sorter.field
          ? sorter.field
          : ''
      }
    })
    setTimeout(() => {
      this.loadApps();
    })

  }
  renderActivities() {
    const list = this.props.events || [];

    if (!list.length) {
      return <p
        style={{
        textAlign: 'center',
        color: 'ccc',
        paddingTop: 20
      }}>暂无动态</p>
    }

    return list.map((item) => {
      const linkTo = "/app/" + item.service_alias + "/overview";
      return (
        <List.Item key={item.id}>
          <List.Item.Meta
            title={< span > <a className={styles.username}>{item.nick_name}&nbsp;</a> < span className = {
            styles.event
          } > {
            item.type_cn
          } < /span> &nbsp; <Link to={linkTo} className={styles.event}>{item.service_cname}&nbsp;</Link > 应用 < /span>}
            description={< span className = {
            styles.datetime
          }
          title = {
            item.updatedAt
          } > {
            moment(item.start_time).fromNow()
          } < /span>}/>
        </List.Item>
      );
    });
  }
  render() {
    const {index, projectLoading, activitiesLoading, currUser, pagination} = this.props;

    const team_name = globalUtil.getCurrTeamName();

    const team = userUtil.getTeamByTeamName(currUser, team_name);

    const pageHeaderContent = (
      <div className={styles.pageHeaderContent}>
        <div className={styles.avatar}>
          <Avatar size="large" src={require("../../../public/images/team-icon.png")}/>
        </div>
        <div className={styles.content}>
          <div className={styles.contentTitle}>{team.team_alias}</div>
          <div>创建于 {moment(team.create_time).format('YYYY-MM-DD')}</div>
        </div>
      </div>
    );

    const extraContent = (
      <div className={styles.extraContent}>
        <div className={styles.statItem}>
          <p>应用数</p>
          <p>{index.overviewInfo.team_service_num || 0}</p>
        </div>
        <div className={styles.statItem}>
          <p>团队成员</p>
          <p>{index.overviewInfo.user_nums || 0}</p>
        </div>
        <div className={styles.statItem}>
          <p>使用内存资源</p>
          <p>{index.overviewInfo.team_service_memory_count || 0}
            MB</p>
        </div>
      </div>
    );

    return (
      <PageHeaderLayout content={pageHeaderContent} extraContent={extraContent}>
        <Row gutter={24}>
          <Col xl={16} lg={24} md={24} sm={24} xs={24}>
            <Card bordered={false}>
              <div className={styles.tableList}>
                <div className={styles.tableListForm}>
                  {this.renderSimpleForm()}
                </div>
                <IndexTable
                  list={index.apps}
                  pagination={pagination}
                  onChange={this.handleListChange}/>
              </div>
            </Card>
          </Col>
          <Col xl={8} lg={24} md={24} sm={24} xs={24}>
            <Card
              style={{
              marginBottom: 24
            }}
              title="快速创建应用"
              bordered={false}
              bodyStyle={{
              padding: 0
            }}>
              <EditableLinkGroup onAdd={() => {}} links={links} linkElement={Link}/>
            </Card>

            <Card
              bodyStyle={{
              padding: 0
            }}
              bordered={false}
              className={styles.activeCard}
              title="动态"
              loading={activitiesLoading}>
              <List loading={activitiesLoading} size="large">
                <div className={styles.activitiesList}>
                  {this.renderActivities()}
                </div>
              </List>
            </Card>

          </Col>
        </Row>

      </PageHeaderLayout>
    );
  }
}
