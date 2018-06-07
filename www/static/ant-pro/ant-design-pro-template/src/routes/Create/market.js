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

const token = cookie.get('token');
let myheaders = {}
if (token) {
   myheaders.Authorization = `GRJWT ${token}`;  
   myheaders['X_REGION_NAME'] = globalUtil.getCurrRegionName();
   myheaders['X_TEAM_NAME'] = globalUtil.getCurrTeamName();
}

const appstatus ={
	'pending':'等待中',
	'importing':'导入中',
	'success':'成功',
	'failed':'失败'
}


//上传文件
@connect(({user, groupControl, global, loading}) => ({rainbondInfo: global.rainbondInfo, loading: loading}), null, null, {pure: false})
@Form.create()
class UploadFile extends PureComponent {
    constructor(props){
      super(props);
      this.state={
        fileList: []
      }
    }
    handleOk = () => {
         const file = this.state.fileList;
         if(file.length == 0){
            notification.info({
              message: '您还没有上传文件'
            })
            return;
         }
         if(file[0].status != 'done'){
              notification.info({
                message: '正在上传请稍后'
              })
              return;
         }
         const file_name = file[0].name;
         const event_id = file[0].response.data.bean.event_id;
        this
        .props
        .dispatch({
            type: 'createApp/importApp',
            payload: {
                team_name: globalUtil.getCurrTeamName(),
                scope: 'enterprise',
                event_id: event_id,
                file_name: file_name
            },
            callback: ((data) => {
              notification.success({message: `操作成功，正在导入`});
              this.props.onOk && this.props.onOk(data);
            })
        })
    } 
  
    // onChange= ({ fileList }) => {
    //     this.setState({fileList})
    // }

    onChange = (info) => {
      let fileList = info.fileList;
  
      // // 1. Limit the number of uploaded files
      // //    Only to show two recent uploaded files, and old ones will be replaced by the new
      // fileList = fileList.slice(-2);
  
      // 2. read from response and show file link
      // fileList = fileList.map((file) => {
      //   if (file.response) {
      //     // Component will show file.url as link
      //     file.file_name = file.name;
      //   }
      //   return file;
      // });
  
      // 3. filter successfully uploaded files according to response from server
      fileList = fileList.filter((file) => {
        if (file.response) {
          return file.response.msg === 'success';
        }
        return true;
      });
  
      this.setState({ fileList });
    }

    onRemove = ()=>{
       this.setState({fileList:[]})
    }
    render(){
      const form = this.props.form;
      const {getFieldDecorator} = form;
      const team_name = globalUtil.getCurrTeamName();
      const uploadUrl = config.baseUrl + '/console/teams/'+ team_name +'/apps/upload';
      const fileList = this.state.fileList;
      
      return (
         <Modal
           visible={true}
           onOk={this.handleOk}
           onCancel={this.props.onCancel}
           title="请上传应用模板"
           okText="确定上传"
         >
            <Upload 
               action={uploadUrl}
               fileList={fileList}
               onChange={this.onChange}
               onRemove={this.onRemove}
               headers = {myheaders}
            >
                
                {fileList.length > 0? null: <Button>请选择文件</Button>}
            </Upload>
         </Modal>
      )
    }
}

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
      showUpload: false,
      target: 'searchWrap',
      visiblebox:{},
      querydatabox:{},
      exportTit:{},
      is_public:this.props.rainbondInfo.is_public,
      showBatchImport:false,
      showBatchImportList:false,
      source_dir:'',
      importEvent_id:'',
      importNameList:[],
      importingList:[]
    }
    this.mount = false;
    this.mountquery = false;
  }
  componentDidMount() {
    this.mount = true;
    this.mountquery = true;
    this.queryImportingApp();
    this.getApps();
    setTimeout(()=>{
      this.setState({target: 'importApp'});
    }, 3000)
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
    var datavisible = {};
    var dataquery = {};
    var dataexportTit = {}
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
            total: data.total,
            visiblebox:datavisible,
            querydatabox:dataquery,
            exportTit:dataexportTit,
            importingList:data.list || []
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
 
  handleCancelUpload = () => {
     this.setState({showUpload: false})
  }
  handleUploadOk =()=>{
    this.setState({showUpload: false})
    this.getApps();
  }
  handleCancelBatchImport = () => {
    this.setState({showBatchImport: false})
 }
 handleBatchImportOk = (data) => {
   this.setState({showBatchImport: false,showBatchImportList:true,importNameList:data})
}
 
handleCancelBatchImportList = () => {
  this.setState({showBatchImportList: false})
  this.queryImportingApp();
}
handleOKBatchImportList = () => {
    this.setState({showBatchImportList: false})
}
  
  handleVisibleChange = (item,flag) =>{
    var newvisible = this.state.visiblebox;
    const ID = item.ID
    newvisible[ID] = flag;
    this.setState({ visiblebox: newvisible });
    this.queryExport(item);
  }
  handleImportMenuClick = (e)=>{
    if(e.key == '1'){
       this.setState({showUpload:true})
    }
    if(e.key == '2'){
      this.setState({showBatchImport:true})
      this
        .props
        .dispatch({
            type: 'createApp/importDir',
            payload: {
                team_name: globalUtil.getCurrTeamName()
            },
            callback: ((data) => {
                this.setState({
                   source_dir:data.bean.source_dir,
                   importEvent_id:data.bean.event_id
                })
            })
        })
    }
  }

  queryImportingApp = ()=>{
    if (!this.mountquery) 
    return;
    this
        .props
        .dispatch({
            type: 'createApp/queryImportingApp',
            payload: {
                team_name: globalUtil.getCurrTeamName()
            },
            callback: ((data) => {
                if(data.list.length == [] ){
                   this.getApps();
                }else{
                  var applist = data.list
                  const list = this.state.list
                  const imList = applist.concat(list)
                  this.setState({importingList:imList},function(){
                    setTimeout(()=>{
                      this.queryImportingApp();
                    }, 3000)
                  })
              }
           })
      })
  }

  renderApp = (item) => {
    const ismarket = item.source;
    const itemID= item.ID;
    const querydata = this.state.querydatabox;
    const exportStatus = item.export_status;
    const exportText = this.state.exportTit[itemID];
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
      ismarket == 'market' ? 
      [<span onClick={() => {
       this.showCreate(item)
     }}>安装</span>
     ]
     :
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
         <Ellipsis className={PluginStyles.item} lines={3}><span style={{ display: 'block',color:'rgb(200, 200, 200)', marginBottom:8, fontSize: 12}} > 
           版本: {item.version} 
           <br />
           内存: {sourceUtil.unit(item.min_memory||128, 'MB')}
         < /span><span title={item.describe}>{item.describe}</span></Ellipsis>
       )}/>
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
    const importingList = this.state.importingList;
      
    const cardList = importingList
      ? (

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
          dataSource={importingList}
          renderItem={item => (
            <List.Item
              style={{border: 'none'}}
              >
              {
                item.ID ?
                this.renderApp(item)
                :
                <Card  className={PluginStyles.card} style={{height:'200px',overflowY:'auto'}}>
                     {
                       item.map((order)=>{
                         return(
                            <p>{order.file_name}<span>{appstatus[order.status]}</span></p>
                         )
                       })
                     }
                </Card>
              }
              
            </List.Item>
        )}/>
      )
      : null;


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
          {this.state.showUpload && <UploadFile onOk={this.handleUploadOk} onCancel={this.handleCancelUpload}  />}
          {this.state.showBatchImport && <BatchImportForm  onOk={this.handleBatchImportOk} onCancel={this.handleCancelBatchImport} source_dir={this.state.source_dir} event_id={this.state.importEvent_id}/>}
          {this.state.showBatchImportList && <BatchImportListForm  onOk={this.handleOKBatchImportList} onCancel={this.handleCancelBatchImportList} event_id={this.state.importEvent_id} file_name={this.state.importNameList} source_dir={this.state.source_dir} />}
          
          {/* <GuideManager /> */}
      </PageHeaderLayout>
    );
  }
}
