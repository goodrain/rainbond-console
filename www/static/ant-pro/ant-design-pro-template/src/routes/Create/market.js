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
import Ellipsis from '../../components/Ellipsis';
import PluginStyles from '../Plugin/Index.less';
import config from '../../config/config';


const ButtonGroup = Button.Group;
const {Option} = Select;
const FormItem = Form.Item;
//上传文件

@Form.create()
class UploadFile extends PureComponent {
    constructor(props){
      super(props);
      this.state={
        fileList: []
      }
    }
    handleOk = () => {
       this.props.form.validateFields({force: true}, (err, values)=>{
           if(err) return;
           this.props.onOk && this.props.onOk(values)
       },)
    }
    handleUpload = () => {
      const { fileList } = this.state;
      const formData = new FormData();
      fileList.forEach((file) => {
        formData.append('files[]', file);
      });
  
      this.setState({
        uploading: true,
      });
  
      // You can use any AJAX library you like
      reqwest({
        url: '//jsonplaceholder.typicode.com/posts/',
        method: 'post',
        processData: false,
        data: formData,
        success: () => {
          this.setState({
            fileList: [],
            uploading: false,
          });
          message.success('upload successfully.');
        },
        error: () => {
          this.setState({
            uploading: false,
          });
          message.error('upload failed.');
        },
      });
    }
    handleCheck = (rule, value, callback) => {
        if(!this.state.fileList.length){
              callback("请选择应用模板文件")
              return;
        }
        callback();
    }
    render(){
      const form = this.props.form;
      const {getFieldDecorator} = form;
      const props = {
        action: '//jsonplaceholder.typicode.com/posts/',
        onRemove: (file) => {
          this.setState(({ fileList }) => {
            const index = fileList.indexOf(file);
            const newFileList = fileList.slice();
            newFileList.splice(index, 1);
            return {
              fileList: newFileList,
            };
          });
        },
        beforeUpload: (file) => {
          this.setState(({ fileList }) => ({
            fileList: [file],
          }));
          return false;
        },
        fileList: this.state.fileList,
      };
      return (
         <Modal
           visible={true}
           onOk={this.handleOk}
           onCancel={this.props.onCancel}
           title="请上传应用模板"
           okText="确定上传"
         >
              <Form.Item>
              {
                getFieldDecorator('file', {
                  initialValue: '',
                  rules:[{validator: this.handleCheck}]
                })(
                  <Upload {...props}>
                     <Button>请选择文件</Button>
                  </Upload>
                )
              }
              </Form.Item>
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
      exportTit:{}
    }
    this.mount = false;
  }
  componentDidMount() {
    this.mount = true;
    this.getApps();
    setTimeout(()=>{
      this.setState({target: 'importApp'});
    }, 3000)
  }
  componentWillUnmount() {
    this.mount = false;
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
          if(data.list.length != 0){
            data.list.map((app)=>{
              datavisible[app.ID] = false;
              dataquery[app.ID] = {};
              if(app.export_status == 'exporting'){
                dataexportTit[app.ID] = '导出中'
                // this.queryExport(app);
              }else if(app.export_status ==  'success'){
                dataexportTit[app.ID] = '导出(可下载)'
              }else{
                dataexportTit[app.ID] = '导出'
              }
            })
          }
          this.setState({
            list: data.list || [],
            total: data.total,
            visiblebox:datavisible,
            querydatabox:dataquery,
            exportTit:dataexportTit
          })
        })
      })
  }


  appExport = (app_id,format) => {
    this
      .props
      .dispatch({
        type: 'createApp/appExport',
        payload: {
          team_name:globalUtil.getCurrTeamName(),
           app_id:app_id,
           format:format
        },
        callback: ((data) => {
          notification.success({message: `操作成功，开始导出，请稍等！`});
        })
      })
  }

  getExport = (app_id,format) => {
    this
      .props
      .dispatch({
        type: 'createApp/getExport',
        payload: {
          team_name:globalUtil.getCurrTeamName(),
           app_id:app_id,
           format:format
        },
        callback: ((data) => {
          // message.success('操作成功，开始导出，请稍等！');
        })
      })
  }
  

 queryExport = (item) => {
  if (!this.mount) 
  return;
    this
      .props
      .dispatch({
        type: 'createApp/queryExport',
        payload: {
           app_id:item.ID,
           team_name:globalUtil.getCurrTeamName()
        },
        callback: ((data) => {
          var newexportTit = this.state.exportTit;
          var newquerydata = this.state.querydatabox;
           var querydataid = data.bean;
           newquerydata[item.ID] = querydataid;
           if(data.bean.docker_compose.is_export_before && data.bean.rainbond_app.is_export_before){
               if((data.bean.docker_compose.status == "exporting" && data.bean.rainbond_app.status != "success") || (data.bean.rainbond_app.status == "exporting" && data.bean.docker_compose.status != "success")){
                   newexportTit[item.ID] = '导出中'
                  //  setTimeout(() => {
                  //     this.queryExport(item);
                  //   }, 5000)
               }else if(data.bean.docker_compose.status == "success" || data.bean.rainbond_app.status == "success"){
                  newexportTit[item.ID] = '导出(可下载)'
               }else{
                  newexportTit[item.ID] = '导出' 
               }
           }else if(data.bean.docker_compose.is_export_before && !data.bean.rainbond_app.is_export_before){
              if(data.bean.docker_compose.status == "exporting"){
                    newexportTit[item.ID] = '导出中'
                    // setTimeout(() => {
                    //   this.queryExport(item);
                    // }, 5000)
                }else if(data.bean.docker_compose.status == "success"){
                  newexportTit[item.ID] = '导出(可下载)'
                }else{
                  newexportTit[item.ID] = '导出' 
                }
           }else if(!data.bean.docker_compose.is_export_before && data.bean.rainbond_app.is_export_before){
              if(data.bean.rainbond_app.status == "exporting"){
                newexportTit[item.ID] = '导出中'
                // setTimeout(() => {
                //   this.queryExport(item);
                // }, 5000)
              }else if(data.bean.rainbond_app.status == "success"){
                 newexportTit[item.ID] = '导出(可下载)'
              }else{
                newexportTit[item.ID] = '导出' 
              }
           }else{
               newexportTit[item.ID] = '导出' 
           }
          
           this.setState({querydatabox:newquerydata})
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
  onUpload = () => {
     this.setState({showUpload: true})
  }
  handleCancelUpload = () => {
     this.setState({showUpload: false})
  }
 
  handleMenuClick = (e) => {
     var key = e.key;
     var keyArr  = key.split("||");
     console.log(keyArr);
     var format = keyArr[0];
     var id = keyArr[1];
     var isexport = keyArr[2];
     var team_name = globalUtil.getCurrTeamName()
     if(isexport =='success'){
        // var newurl = config.baseUrl + '/console/teams/'+ team_name +'/apps/export/down?app_id='+ id +'&format=' + format;
        // window.open(newurl);
        console.log("00")
     }else if(isexport == 'loading'){
        notification.info({message: `正在导出，请稍后！`});
     }else{
       this.appExport(id,format);
     }
    
  }

  renderSubMenu = (item,querydata) => {
    const id = item.ID;
    const exportbox  = querydata[id];
    const appquery = exportbox.rainbond_app;
    const composequery = exportbox.docker_compose;
    var apptext ='rainbond-app(点击导出)';
    var composetext = 'docker_compose(点击导出)';
    var appurl='javascript:;';
    var composeurl ='javascript:;';
    var appisSuccess = 'none';
    var composeisSuccess = 'none';
    const export_status = item.export_status;
    if(appquery){
      //
      
       if(appquery.is_export_before)  {
          if(appquery.status== 'success'){
            apptext = 'rainbond-app(点击下载)';
            appisSuccess = 'success';
            appurl = appquery.file_path ;
          }else if(appquery.status  == 'exporting'){
            apptext = 'rainbond-app(导出中)';
            appisSuccess = 'loading';
          }else{
            apptext = 'rainbond-app(导出失败)';
          }
       }else{
        apptext = 'rainbond-app(点击导出)';
       }
       //
       if(composequery.is_export_before)  {
        if(composequery.status== 'success'){
          composetext = 'docker_compose(点击下载)';
          composeisSuccess = 'success';
          composeurl = composequery.file_path ;
        }else if(composequery.status  == 'exporting'){
          composetext = 'docker_compose(导出中)';
          composeisSuccess = 'loading';
        }else{
          composetext = 'docker_compose(导出失败)';
        }
     }else{
        composetext = 'docker_compose(点击导出)';
     }
       //

       //
       
    }else{
      composetext = 'docker_compose(点击下载)';
      apptext = 'rainbond-app(点击下载)';
    }

    return <Menu onClick={this.handleMenuClick}>
            <Menu.Item key={ 'rainbond-app||' +  id  + '||' + appisSuccess}>
              <a target="_blank"  href={appurl} download="filename">{apptext}</a>
            </Menu.Item>
            <Menu.Item key={'docker-compose||' + id  + '||' + composeisSuccess}>
              <a target="_blank" href={composeurl}  download="filename">{composetext}</a>
            </Menu.Item>
      </Menu>
		
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
    // ,
    // <Dropdown overlay={this.renderSubMenu(item,querydata)}  visible={this.state.visiblebox[itemID]} onVisibleChange={this.handleVisibleChange.bind(this,item)}>
    //    <a  className="ant-dropdown-link" href="javascript:;" >
    //      {exportText}<Icon type="down" />
    //    </a>
    //  </Dropdown>
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
    const cardList = list
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
          dataSource={list}
          renderItem={item => (
            <List.Item
              style={{border: 'none'}}
              >
              {this.renderApp(item)}
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
          {this.state.showUpload && <UploadFile onOk={this.handleUploadOk} onCancel={this.handleCancelUpload} />}
          {/* <GuideManager /> */}
      </PageHeaderLayout>
    );
  }
}
