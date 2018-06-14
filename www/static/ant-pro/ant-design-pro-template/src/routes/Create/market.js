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
  List,
  Select,
  Input,
  Pagination,
  Modal,
  Upload,
  message
} from 'antd';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import {getRoutes} from '../../utils/utils';
import {getRouterData} from '../../common/router';
import ConfirmModal from '../../components/ConfirmModal';
import styles from './Projects.less';
import globalUtil from '../../utils/global';
import sourceUtil from '../../utils/source-unit';
import CodeCustom from './code-custom';
import CodeDemo from './code-demo';
import CodeGoodrain from './code-goodrain';
import CodeGithub from './code-github';
import rainbondUtil from '../../utils/rainbond';
import StandardFormRow from '../../components/StandardFormRow';
import TagSelect from '../../components/TagSelect';
import AvatarList from '../../components/AvatarList';
import CreateAppFromMarketForm from '../../components/CreateAppFromMarketForm';
import BatchImportForm from '../../components/BatchImportForm';
import BatchImportListForm from '../../components/BatchImportmListForm';
import Ellipsis from '../../components/Ellipsis';
import PluginStyles from '../Plugin/Index.less';
import config from '../../config/config';
import cookie from '../../utils/cookie';


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
      pageSize: 9,
      total: 0,
      target: 'searchWrap'
    }
    this.mount = false;
  }
  componentDidMount() {
    this.mount = true;
    this.getApps();
  }
  componentWillUnmount() {
    this.mount = false;
    this.mountquery = false;
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
  
  handleVisibleChange = (item,flag) =>{
    var newvisible = this.state.visiblebox;
    const ID = item.ID
    newvisible[ID] = flag;
    this.setState({ visiblebox: newvisible });
    this.queryExport(item);
  }

  renderApp = (item) => {
    const ismarket = item.source;
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

     return <Card
     className={PluginStyles.card}
     actions={
      [<span onClick={() => {
       this.showCreate(item)
     }}>安装</span>
     ]
    }>
     <Card.Meta
         style={{height: 112, overflow: 'hidden'}}
         avatar={< img style = {{width: 110, height: 110, margin:' 0 auto'}}alt = {
           item.title
         }
         src = {
           item.pic || require('../../../public/images/app_icon.jpg')
         }
         height = {
           154
         } />}
         title={title(item)}
         description={(
        <Fragment>
          <span style={{ display: 'block',color:'rgb(200, 200, 200)', marginBottom:8, fontSize: 12}} > 
           版本: {item.version} 
           <br />
           内存: {sourceUtil.unit(item.min_memory||128, 'MB')}
         </span>
         <Ellipsis className={PluginStyles.item} lines={3}>
            <span title={item.describe}>{item.describe}</span>
         </Ellipsis>
         </Fragment>
       )}
       />
   </Card>
  }
  render() {

    const {form} = this.props;
    const {getFieldDecorator} = form;
    const list = this.state.list;
   
    var formItemLayout = {};

    const paginationProps = {
      current: this.state.page,
      pageSize: this.state.pageSize,
      total: this.state.total,
      onChange: (v) => {
        this.hanldePageChange(v);
      }
    };
      
    const cardList = (

        <List
          bordered={false}
          grid={{
          gutter: 24,
            lg: 3,
            md: 2,
            sm: 1,
            xs: 1
        }}
          pagination={paginationProps}
          dataSource={list}
          renderItem={item => (
            <List.Item
              style={{border: 'none'}}
              >
              {this.renderApp(item)}
              
            </List.Item>
        )}/>
      )


    const mainSearch = (
      <div style={{
        textAlign: 'center'
        
      }}>
        <span id="searchWrap" style={{display: 'inline-block'}}>
        <Input.Search
          
          placeholder="请输入应用名称"
          enterButton="搜索"
          size="large"
          defaultValue={this.state.app_name}
          
          onSearch={this.handleSearch}
          style={{
          width: 522
        }}/>
        </span>
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
          {/* <div className="btns" style={{marginTop: -10, marginBottom: 16, textAlign: 'right'}}>
            <Button id="importApp" onClick={this.onUpload} type="primary">导入应用</Button>
          </div> */}
          <div className={PluginStyles.cardList}>
            {cardList}
          </div>
        {this.state.showCreate && <CreateAppFromMarketForm
          disabled={loading.effects['createApp/installApp']}
          onSubmit={this.handleCreate}
          onCancel={this.onCancelCreate}/>}
          
          {/* <GuideManager /> */}
      </PageHeaderLayout>
    );
  }
}
