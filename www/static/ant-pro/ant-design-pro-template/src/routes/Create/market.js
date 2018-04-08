import React, {PureComponent} from 'react';
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
  List,
  Select,
  Input,
  Pagination
} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import {getRoutes} from '../../utils/utils';
import {getRouterData} from '../../common/router';
import ConfirmModal from '../../components/ConfirmModal';
import styles from './Projects.less';
import globalUtil from '../../utils/global';
import CodeCustom from './code-custom';
import CodeDemo from './code-demo';
import CodeGoodrain from './code-goodrain';
import CodeGithub from './code-github';
import rainbondUtil from '../../utils/rainbond';
import StandardFormRow from '../../components/StandardFormRow';
import TagSelect from '../../components/TagSelect';
import AvatarList from '../../components/AvatarList';
import CreateAppFromMarketForm from '../../components/CreateAppFromMarketForm';
import Ellipsis from '../../components/Ellipsis';

const ButtonGroup = Button.Group;
const {Option} = Select;
const FormItem = Form.Item;

@connect(({user, groupControl, global, loading}) => ({rainbondInfo: global.rainbondInfo, loading: loading}), null, null, {pure: false})

@Form.create()
export default class Main extends PureComponent {
  constructor(arg) {
    super(arg);
    const appName = decodeURIComponent(this.props.match.params.keyword||'');
    this.state = {
      list: [],
      showCreate: null,
      scope: '',
      app_name: appName,
      page: 1,
      pageSize: 8,
      total: 0
    }
  }
  componentDidMount() {
    this.getApps();
  }
  handleChange = (v) => {

  }
  handleSearch = (v) => {
    this.setState({
      app_name: v,
      page: 1
    }, () => {
      this.getApps();
    })
  }
  getApps = (v) => {
    this
      .props
      .dispatch({
        type: 'createApp/getMarketApp',
        payload: {
          app_name: this.state.app_name || '',
          scope: this.state.scope,
          page_size: this.state.pageSize,
          page: this.state.page
        },
        callback: ((data) => {
          this.setState({
            list: data.list || [],
            total: data.total
          })
        })
      })
  }
  hanldePageChange = (page) => {
    this.setState({
      page: page
    }, () => {
      this.getApps();
    })
  }
  componentWillUnmount() {}
  getDefaulType = () => {
    return ''
  }
  handleTabChange = (key) => {
    this.setState({
      scope: key,
      page: 1
    }, () => {
      this.getApps();
    })
  }
  onCancelCreate = () => {
    this.setState({showCreate: null})
  }
  showCreate = (app) => {
    this.setState({showCreate: app})
  }
  handleCreate = (vals) => {

    const app = this.state.showCreate;
    this
      .props
      .dispatch({
        type: 'createApp/installApp',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          ...vals,
          app_id: app.ID
        },
        callback: () => {

          //刷新左侧按钮
          this.props.dispatch({
            type: 'global/fetchGroups',
            payload: {
              team_name: globalUtil.getCurrTeamName()
            }
          })

          //关闭弹框
          this.onCancelCreate();
          this
            .props
            .dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/groups/${vals.group_id}`))
        }
      })

  }
  render() {

    const {form} = this.props;
    const {getFieldDecorator} = form;
    const list = this.state.list;
    const title = (item) => {
      return <div
        title={item.group_name || ''}
        style={{
        maxWidth: '200px',
        overflow: 'hidden'
      }}>
        {item.group_name || ''}
      </div>
    }
    var formItemLayout = {};

    const paginationProps = {
      current: this.state.page,
      pageSize: this.state.pageSize,
      total: this.state.total,
      onChange: (v) => {
        this.hanldePageChange(v);
      }
    };
    const cardList = list
      ? (
        <List
          rowKey="id"
          grid={{
          gutter: 24,
          lg: 4,
          md: 3,
          sm: 2,
          xs: 1
        }}
          pagination={paginationProps}
          dataSource={list}
          renderItem={item => (
          <div>
            <List.Item
              onClick={() => {
              this.showCreate(item)
            }}
              style={{
              margin: '0 12px 16px 12px'
            }}>
              <Card
                className={styles.card}
                hoverable
                cover={< img style = {{maxWidth: 254, width: 'auto', margin:' 0 auto'}}alt = {
                item.title
              }
              src = {
                item.pic || require('../../../public/images/app_icon.jpg')
              }
              height = {
                154
              } />}>
                <Card.Meta
                  onClick={() => {
                  this.showCreate(item)
                }}
                  title={title(item)}
                  description={item.describe}/>
              </Card>
            </List.Item>
          </div>
        )}/>
      )
      : null;

    const mainSearch = (
      <div style={{
        textAlign: 'center'
      }}>
        <Input.Search
          placeholder="请输入应用名称"
          enterButton="搜索"
          size="large"
          defaultValue={this.state.app_name}
          
          onSearch={this.handleSearch}
          style={{
          width: 522
        }}/>
      </div>
    );

    const tabList = [
      {
        key: '',
        tab: '全部'
      }, {
        key: 'goodrain',
        tab: '云市'
      }, {
        key: 'enterprise',
        tab: '本公司'
      }, {
        key: 'team',
        tab: '本团队'
      }
    ];
    const loading = this.props.loading;
    return (
      <PageHeaderLayout
        content={mainSearch}
        tabList={tabList}
        tabActiveKey={this.state.scope}
        onTabChange={this.handleTabChange}>

        <div className={styles.coverCardList}>
          <div className={styles.cardList}>
            {cardList}
          </div>
        </div>
        {this.state.showCreate && <CreateAppFromMarketForm
          disabled={loading.effects['createApp/installApp']}
          onSubmit={this.handleCreate}
          onCancel={this.onCancelCreate}/>}
      </PageHeaderLayout>
    );
  }
}
