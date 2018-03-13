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
  Input
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

const ButtonGroup = Button.Group;
const {Option} = Select;
const FormItem = Form.Item;

@connect(({user, groupControl, global}) => ({rainbondInfo: global.rainbondInfo}), null, null, {pure: false})

@Form.create()
export default class Main extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {
      list: [],
      showCreate: null,
      scope: ''
    }
  }
  componentDidMount() {
    this.getApps();
  }
  getApps = (v) => {

    this
      .props
      .dispatch({
        type: 'createApp/getMarketApp',
        payload: {
          app_name: v || '',
          scope: this.state.scope
        },
        callback: ((data) => {
          this.setState({
            list: data.list || []
          })
        })
      })

  }
  reset = () => {
    this
      .props
      .form
      .resetFields();
    setTimeout(() => {
      this.getApps();
    })
  }
  componentWillUnmount() {}
  getDefaulType = () => {
    return ''
  }
  handleTabChange = (key) => {
    this.setState({
      scope: key
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
          this.onCancelCreate();
          this
            .props
            .dispatch(routerRedux.push('/groups/' + vals.group_id))
        }
      })

  }
  render() {

    const {form} = this.props;
    const {getFieldDecorator} = form;
    const list = this.state.list;
    var formItemLayout = {};
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
          dataSource={list}
          renderItem={item => (
          <div>
            <List.Item
              onClick={() => {
              this.showCreate(item)
            }}
              style={{
              margin: '0 12px 0 12px'
            }}>
              <Card
                className={styles.card}
                hoverable
                cover={< img style = {{width: 'auto', margin:' 0 auto'}}alt = {
                item.title
              }
              src = {
                item.src || require('../../../public/images/app_icon.jpg')
              }
              height = {
                154
              } />}>
                <Card.Meta
                  onClick={() => {
                  this.showCreate(item)
                }}
                  title={< a href = "javascript:;" > {
                  item.group_name
                } < /a>}
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
          onSearch={this.getApps}
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
          onSubmit={this.handleCreate}
          onCancel={this.onCancelCreate}/>}
      </PageHeaderLayout>
    );
  }
}
