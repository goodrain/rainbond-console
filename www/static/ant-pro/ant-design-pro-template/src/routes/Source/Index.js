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
    Menu,
    Dropdown,
    Upload
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
import CreateAppFromMarketForm from '../../components/CreateAppFromMarketForm';
import BatchImportForm from '../../components/BatchImportForm';
import BatchImportListForm from '../../components/BatchImportmListForm';
import config from '../../config/config'
import CloudPlugin from './CloudPlugin';
const FormItem = Form.Item;
const {Step} = Steps;
const RadioButton = Radio.Button;
const RadioGroup = Radio.Group;
const {Search} = Input;

const appstatus ={
	'pending':'等待中',
	'importing':'导入中',
	'success':'成功',
	'failed':'失败'
}
const token = cookie.get('token');
let myheaders = {}
if (token) {
   myheaders.Authorization = `GRJWT ${token}`;  
   myheaders['X_REGION_NAME'] = globalUtil.getCurrRegionName();
   myheaders['X_TEAM_NAME'] = globalUtil.getCurrTeamName();
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
    onChange = (info) => {
      let fileList = info.fileList;
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





class CloudApp extends PureComponent {
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

class ImportingApps extends PureComponent {
    render(){
        var list = this.props.data || [];
        
        return <List.Item
            actions={[]}>
            <List.Item.Meta
                avatar={null}
                shape = "square" 
                size = "large"
                title={null}
                description={<div>
                    {
                        list.map((item) => {
                            return item.map((file) => {
                                return <p>{file.file_name}--{appstatus[file.status]}</p>
                            })
                            
                        })
                    }
                </div>}/>
        </List.Item>
    }
}


@connect()
class AppList extends PureComponent {
    constructor(props) {
        super(props);
        this.state = {
            page: 1,
            pageSize: 10,
            app_name: '',
            apps: [],
            loading: true,
            total: 0,
            type: "",
            showOfflineApp: null,
            showCloudApp: false,
            importingApps:null
        }
    }
    componentDidMount = () => {
        this.mounted = true;
        this.queryImportingApp();
        this.getApps();
        
    }
    componentWillUnmount(){
        this.mounted = false;
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
                    this.queryExport(app);
                  }else if(app.export_status ==  'success'){
                    dataexportTit[app.ID] = '导出(可下载)'
                  }else{
                    dataexportTit[app.ID] = '导出'
                  }
                })
              }
              this.setState({
                apps: data.list || [],
                total: data.total,
                visiblebox:datavisible,
                querydatabox:dataquery,
                exportTit:dataexportTit,
                importingList:data.list || [],
                loading: false
              })
            })
          })
    }
    queryImportingApp = ()=>{
        this
            .props
            .dispatch({
                type: 'createApp/queryImportingApp',
                payload: {
                    team_name: globalUtil.getCurrTeamName()
                },
                callback: ((data) => {
                      if(data.list && data.list.length){
                         this.setState({importingApps: data.list});
                         if(this.mounted){
                            setTimeout(() => {
                                this.queryImportingApp();
                            }, 6000)
                         }
                      }else{
                        this.setState({importingApps:null})
                        this.getApps();
                      }
                      
               })
        })
    }
    handlePageChange = (page) => {
        this.state.page = page;
        this.getApps();
    }
    handleSearch = (app_name) => {
        this.setState({
            app_name: app_name,
            page: 1
        }, () => {
            this.getApps();
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
                }
            })
    }
    handleTypeChange = (e) => {
        this.setState({type: e.target.value, page: 1}, () => {
            this.loadApps();
        })
    }
    handleOfflineApp = () => {
        const app = this.state.showOfflineApp;
        this.props.dispatch({
            type: 'global/offlineMarketApp',
            payload:{
                app_id: app.ID
            },
            callback: () => {
                notification.success({
                    message: '删除成功'
                })
                this.hideOfflineApp();
                this.getApps();
            }
        })
    }
    showOfflineApp = (app) => {
        this.setState({showOfflineApp: app})
    }
    hideOfflineApp = () => {
        this.setState({showOfflineApp: null})
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
    handleCancelUpload = () => {
        this.setState({showUpload: false})
    }
    handleCancelBatchImportList = () => {
        this.setState({showBatchImportList: false})
        this.queryImportingApp();
        this.getApps();
    }
    handleUploadOk =()=>{
       this.setState({showUpload: false});
       this.queryImportingApp();
       this.handlePageChange(1);
    }
    handleCancelBatchImport = () => {
       this.setState({showBatchImport: false})
    }
    handleBatchImportOk = (data) => {
      this.setState({showBatchImport: false,showBatchImportList:true,importNameList:data})
    }
    handleOKBatchImportList = () => {
        this.setState({showBatchImportList: false})
        this.queryImportingApp();
        this.getApps();
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
                         setTimeout(() => {
                            this.queryExport(item);
                          }, 5000)
                     }else if(data.bean.docker_compose.status == "success" || data.bean.rainbond_app.status == "success"){
                        newexportTit[item.ID] = '导出(可下载)'
                     }else{
                        newexportTit[item.ID] = '导出' 
                     }
                 }else if(data.bean.docker_compose.is_export_before && !data.bean.rainbond_app.is_export_before){
                    if(data.bean.docker_compose.status == "exporting"){
                          newexportTit[item.ID] = '导出中'
                          setTimeout(() => {
                            this.queryExport(item);
                          }, 5000)
                      }else if(data.bean.docker_compose.status == "success"){
                        newexportTit[item.ID] = '导出(可下载)'
                      }else{
                        newexportTit[item.ID] = '导出' 
                      }
                 }else if(!data.bean.docker_compose.is_export_before && data.bean.rainbond_app.is_export_before){
                    if(data.bean.rainbond_app.status == "exporting"){
                      newexportTit[item.ID] = '导出中'
                      setTimeout(() => {
                        this.queryExport(item);
                      }, 5000)
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
    handleVisibleChange = (item,flag) =>{
        var newvisible = this.state.visiblebox;
        const ID = item.ID
        newvisible[ID] = flag;
        this.setState({ visiblebox: newvisible });
        this.queryExport(item);
    }
    render() {
        const ImportMenu = (
            <Menu onClick={this.handleImportMenuClick}>
              <Menu.Item key="1">文件上传</Menu.Item>
              <Menu.Item key="2">批量导入</Menu.Item>
            </Menu>
          );
        const extraContent = (
            <div className={BasicListStyles.extraContent}>
                <RadioGroup value="">
                    <Dropdown overlay={ImportMenu}>
                        <RadioButton>
                            导入应用
                        </RadioButton>
                    </Dropdown>
                    <RadioButton value="test" onClick={()=>{this.setState({showCloudApp: true})}}>云端同步</RadioButton>
                </RadioGroup>
            </div>
        );

        const paginationProps = {
            pageSize: this.state.pageSize,
            total: this.state.total,
            current: this.state.page,
            onChange: (pageSize) => {
                this.handlePageChange(pageSize)
            }
        };

        return (
            <div className={BasicListStyles.standardList} style={{display: this.state.showCloudApp ? 'flex' : 'block',position:'relative', overflow: 'hidden'}}>
                <Card
                    className={BasicListStyles.listCard}
                    bordered={false}
                    title={<div>{this.state.showCloudApp && <span>内部市场</span>}<Search
                        className={BasicListStyles.extraContentSearch}
                        placeholder="请输入名称进行搜索"
                        onSearch={this.handleSearch}/></div>}
                    style={{
                    transition: 'all .8s',
                    width: this.state.showCloudApp ? '50%' : '100%',
                    display: 'inline-block'
                }}
                    bodyStyle={{
                    padding: '0 32px 40px 32px'
                }}
                    extra={this.state.showCloudApp ? null : extraContent}>
                    <List
                        size="large"
                        rowKey="ID"
                        loading={this.state.loading}
                        pagination={paginationProps}
                        dataSource={this.state.apps}
                        renderItem={(item, index) => {
                            const itemID= item.ID;
                            const querydata = this.state.querydatabox;
                            const exportStatus = item.export_status;
                            const exportText = this.state.exportTit[itemID];
                            var renderItem = <List.Item
                                            actions={this.state.showCloudApp ? null : [item.is_complete
                                                ? <Fragment>
                                                <Dropdown overlay={this.renderSubMenu(item,querydata)}  visible={this.state.visiblebox[itemID]} onVisibleChange={this.handleVisibleChange.bind(this,item)}>
                                                <a style={{marginRight: 8}} className="ant-dropdown-link" href="javascript:;" >
                                                    {exportText}<Icon type="down" />
                                                </a>
                                                </Dropdown>
                                                <a
                                                    style={{marginRight: 8}}
                                                        href="javascript:;"
                                                        onClick={() => {
                                                        this.handleLoadAppDetail(item)
                                                    }}>云端更新</a>
                                                    <a
                                                        href="javascript:;"
                                                        onClick={() => {
                                                        this.showOfflineApp(item)
                                                    }}>删除</a>
                                                </Fragment>
                                                : <a
                                                    href="javascript:;"
                                                    onClick={() => {
                                                    this.handleLoadAppDetail(item)
                                                }}>下载应用</a>]}>
                                            <List.Item.Meta
                                                avatar={< Avatar src = {
                                                item.pic || require("../../../public/images/app_icon.jpg")
                                            }
                                            shape = "square" size = "large" />}
                                                title={item.group_name}
                                                description={item.describe || '-'}/>
                                        </List.Item>
                        if(index === 0 && this.state.importingApps && this.state.importingApps.length) {
                            return <Fragment>
                                 <ImportingApps data={this.state.importingApps} dispatch={this.props.dispatch} />
                                {renderItem}
                            </Fragment>
                        }else{
                            return renderItem
                        }
                        
                    }}/>

                </Card>
                <div style={{
                    transition: 'all .8s',
                    transform: this.state.showCloudApp ? 'translate3d(0, 0, 0)' : 'translate3d(100%, 0, 0)',
                    marginLeft:8,
                    width: '49%'
                }}>
                    {this.state.showCloudApp ? <CloudApp onSyncSuccess={() => {this.handlePageChange(1)}} onClose={()=>{this.setState({showCloudApp: false})}} dispatch={this.props.dispatch} /> : null}
                </div>
                {this.state.showOfflineApp && <ConfirmModal onOk={this.handleOfflineApp} desc={`确定要删除此应用吗?`} subDesc="删除后其他人将无法安装此应用" title={'删除应用'} onCancel={this.hideOfflineApp} />}
                {this.state.showUpload && <UploadFile onOk={this.handleUploadOk} onCancel={this.handleCancelUpload}  />}
                {this.state.showBatchImport && <BatchImportForm  onOk={this.handleBatchImportOk} onCancel={this.handleCancelBatchImport} source_dir={this.state.source_dir} event_id={this.state.importEvent_id}/>}
                {this.state.showBatchImportList && <BatchImportListForm  onOk={this.handleOKBatchImportList} onCancel={this.handleCancelBatchImportList} event_id={this.state.importEvent_id} file_name={this.state.importNameList} source_dir={this.state.source_dir} />}
            </div>
        )
    }
}



@connect()
class PluginList extends PureComponent {
    constructor(props) {
        super(props);
        this.state = {
            sync: false,
            page: 1,
            pageSize: 10,
            app_name: '',
            plugins: [],
            loading: true,
            total: 0,
            type: "",
            showOfflinePlugin: null,
            showCloudPlugin: false
        }
    }
    componentDidMount = () => {
        this.loadPlugins();
    }
    handleSync = () => {
        this.setState({
            sync: true
        }, () => {
            this
                .props
                .dispatch({
                    type: 'global/syncMarketPlugins'
                }).then(()=>{
                    this.setState({
                        sync: false
                    }, () => {
                        this.loadPlugins();
                    })
                })
        })
    }
    loadPlugins = () => {
        this.setState({
            loading: true
        }, () => {
            this
                .props
                .dispatch({
                    type: 'global/getMarketPlugins',
                    payload: {
                        plugin_name: this.state.app_name,
                        page: this.state.page,
                        limit: this.state.pageSize,
                        is_complete: this.state.type
                    },
                    callback: (data) => {
                        this.setState({
                            plugins: data.list || [],
                            loading: false,
                            total: data.total
                        })
                    }
                })
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
                    this.loadPlugins();
                }
            })
    }
    handlePageChange = (page) => {
        this.state.page = page;
        this.loadPlugins();
    }
    handleSearch = (app_name) => {
        this.setState({
            app_name: app_name,
            page: 1
        }, () => {
            this.loadPlugins();
        })
    }
    
    handleTypeChange = (e) => {
        this.setState({type: e.target.value, page: 1}, () => {
            this.loadPlugins();
        })
    }
    handleOfflinePlugin = () => {
        const plugin = this.state.showOfflinePlugin;
        this.props.dispatch({
            type: 'global/deleteMarketPlugin',
            payload:{
                plugin_id: plugin.id
            },
            callback: () => {
                notification.success({
                    message: '卸载成功'
                })
                this.hideOfflinePlugin();
                this.loadPlugins();
            }
        })
    }
    showOfflinePlugin = (plugin) => {
        this.setState({showOfflinePlugin: plugin})
    }
    hideOfflinePlugin = () => {
        this.setState({showOfflinePlugin: null})
    }
    render() {
        const extraContent = (
            <div className={BasicListStyles.extraContent}>
                <RadioGroup value="">
                    <RadioButton onClick={()=>{this.setState({showCloudPlugin: true})}} value="">云端同步</RadioButton>
                </RadioGroup>
            </div>
        );

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
            <div className={BasicListStyles.standardList} style={{display: this.state.showCloudPlugin ? 'flex' : 'block',position:'relative', overflow: 'hidden'}}>
                <Card
                    className={BasicListStyles.listCard}
                    bordered={false}
                    title={<div>{this.state.showCloudPlugin && <span>内部市场</span>}<Search
                        className={BasicListStyles.extraContentSearch}
                        placeholder="请输入名称进行搜索"
                        onSearch={this.handleSearch}/></div>}
                    style={{
                    transition: 'all .8s',
                    width: this.state.showCloudPlugin ? '50%' : '100%',
                    display: 'inline-block'
                }}
                    bodyStyle={{
                    padding: '0 32px 40px 32px'
                }}
                    extra={this.state.showCloudPlugin ? null : extraContent}>
                    <List
                        size="large"
                        rowKey="id"
                        loading={this.state.loading}
                        pagination={paginationProps}
                        dataSource={this.state.plugins}
                        renderItem={item => (
                        <List.Item
                            actions={this.state.showCloudPlugin ? null : [item.is_complete
                                ? <Fragment>
                                 <a
                                    style={{marginRight: 8}}
                                        href="javascript:;"
                                        onClick={() => {
                                        this.handleLoadPluginDetail(item)
                                    }}>云端更新</a>
                                    <a
                                        href="javascript:;"
                                        onClick={() => {
                                        this.showOfflinePlugin(item)
                                    }}>删除</a>
                                 </Fragment>
                                : <a
                                    href="javascript:;"
                                    onClick={() => {
                                    this.handleLoadAppDetail(item)
                                }}>下载应用</a>]}>
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
                <div style={{
                    transition: 'all .8s',
                    transform: this.state.showCloudPlugin ? 'translate3d(0, 0, 0)' : 'translate3d(100%, 0, 0)',
                    marginLeft:8,
                    width: '49%'
                }}>
                    {this.state.showCloudPlugin ? <CloudPlugin onSyncSuccess={() => {this.handlePageChange(1)}} onClose={()=>{this.setState({showCloudPlugin: false})}} dispatch={this.props.dispatch} /> : null}
                </div>
                {this.state.showOfflinePlugin && <ConfirmModal onOk={this.handleOfflinePlugin} desc={`确定要删除此插件吗?`} subDesc="删除后其他人将无法安装此插件" title={'删除插件'} onCancel={this.hideOfflinePlugin} />}
            </div>
        )
    }
}


@connect(({user}) => ({currUser: user.currentUser}))
export default class Index extends PureComponent {
    constructor(arg) {
        super(arg);
        
        let params = this.getParam();
        this.state = {
            isChecked: true,
            loading: false,
            currStep: 0,
            scope: params.type || 'app'
        }
    }
    componentDidMount() {}
    getParam() {
        return this.props.match.params;
    }
    handleTakeInfo = () => {
        const {currUser} = this.props;
        this.setState({
            currStep: 1
        }, () => {
            window.open(`https://www.goodrain.com/spa/#/check-console/${currUser.enterprise_id}`)
        })
    }
    handleAuthEnterprise = (vals) => {
        const {currUser} = this.props;
        this
            .props
            .dispatch({
                type: 'global/authEnterprise',
                payload: {
                    team_name: globalUtil.getCurrTeamName(),
                    enterprise_id: currUser.enterprise_id,
                    ...vals
                },
                callback: () => {

                    this
                        .props
                        .dispatch({type: 'user/fetchCurrent'})
                }
            })
    }
    handleTabChange = (key) => {
        this.setState({scope: key})
    }
    renderContent = () => {
        const {currUser} = this.props;
        const {loading, isChecked} = this.state;

        //不是系统管理员
        if (!userUtil.isSystemAdmin(currUser)) {
            this
                .props
                .dispatch(routerRedux.replace(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/Exception/403`))
            return null;
        }

        //如果未进行平台验证
        if (currUser.is_enterprise_active !== 1) {
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
                        <AuthForm onSubmit={this.handleAuthEnterprise}/>
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

        if(this.state.scope === 'app'){
            return <AppList/>
        }

        if(this.state.scope === 'plugin'){
            return <PluginList/>
        }

        
    }
    render() {
        const {currUser} = this.props;
        const {loading} = this.state;

        const team_name = globalUtil.getCurrTeamName();

        const pageHeaderContent = (
            <div className={styles.pageHeaderContent}>
                <div className={styles.content}>
                    <div>将当前云帮平台和好雨云市进行互联，同步应用，插件，数据中心等资源</div>
                    <div>应用下载完成后，方可在 创建应用->从应用市场安装 中看到</div>
                </div>
            </div>
        );

        const tabList = [
            {
              key: 'app',
              tab: '应用'
            }, {
              key: 'plugin',
              tab: '插件'
            }
        ];

        return (
            <PageHeaderLayout 
                tabList={tabList}
                tabActiveKey={this.state.scope}
                onTabChange={this.handleTabChange}
                content={pageHeaderContent}>
                {this.renderContent()}
            </PageHeaderLayout>
        );
    }
}