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
    Upload,
    Tooltip
} from 'antd';
import ConfirmModal from '../../components/ConfirmModal';
import Result from '../../components/Result';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import styles from './Index.less';
import BasicListStyles from '../List/BasicList.less';
import globalUtil from '../../utils/global';
import userUtil from '../../utils/user';
import {routerRedux} from 'dva/router';
import CreateAppFromMarketForm from '../../components/CreateAppFromMarketForm';
import BatchImportForm from '../../components/BatchImportForm';
import BatchImportListForm from '../../components/BatchImportmListForm';
import config from '../../config/config'
import CloudApp from './CloudApp';
import UploadFile from './UploadFile';
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
class ExportBtn extends PureComponent {
    constructor(props){
        super(props);
        this.state = {
            docker_compose: null,
            rainbond_app: null,
            is_docker_compose_exporting: false,
            is_rainbond_app_exporting: false

        }
    }
    componentDidMount(){
        this.mounted = true;
    }
    componentWillUnmount(){
        this.mounted = false
    }
    download = (path) => {
        var aEle = document.querySelector("#down-a-element");
        if(!aEle){
            aEle = document.createElement('a');
            aEle.setAttribute('download',"filename");
            document.body.appendChild(aEle);
        }
        aEle.href=path;
        if(document.all) {
            aEle.click();
        }else {
            var e = document.createEvent("MouseEvents");
            e.initEvent("click", true, true);
            aEle.dispatchEvent(e);
        }  
    }
    appExport = (format) => {
        const app = this.props.app;
        const app_id = app.ID;
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
                if(format === 'rainbond-app'){
                    this.setState({is_rainbond_app_exporting: true})
                }else{
                    this.setState({is_docker_compose_exporting: true})
                } 
            })
        })
    }
    queryExport = (type) => {
        const item = this.props.app || {}
          this
            .props
            .dispatch({
              type: 'createApp/queryExport',
              payload: {
                 app_id:item.ID,
                 team_name:globalUtil.getCurrTeamName()
              },
              callback: ((data) => {
                    //点击导出平台应用
                    if(type === 'rainbond-app'){
                        var rainbond_app = data.bean.rainbond_app || {};
                        if(rainbond_app.file_path){
                            this.setState({is_rainbond_app_exporting: false})
                            this.download(rainbond_app.file_path);
                            return;
                        }

                        //导出中
                        if(rainbond_app.status === 'exporting'){
                            this.setState({is_rainbond_app_exporting: true});
                            if(this.mounted){
                                setTimeout(()=>{
                                    this.queryExport(type)
                                }, 5000)
                            }
                        }
                           
                        if(rainbond_app.is_export_before === false){
                            this.appExport(type);
                            return;
                        }
                        
                    //点击导出compose
                    }else{
                        var docker_compose = data.bean.docker_compose || {};
                        if(docker_compose.file_path){
                            this.setState({is_docker_compose_exporting: false})
                            this.download(docker_compose.file_path);
                            return;
                        }

                        //导出中
                        if(docker_compose.status === 'exporting'){
                            this.setState({is_docker_compose_exporting: true});
                            if(this.mounted){
                                setTimeout(()=>{
                                    this.queryExport(type)
                                }, 5000)
                            }
                        }

                        if(docker_compose.is_export_before === false){
                            this.appExport(type);
                            return;
                        }

                    }
              })
        })
    }
    render(){
        const app = this.props.app || {};
        return (
            <Fragment>
                {
                    app.source !== 'market' ? 
                    <Tooltip title="导出后的文件可直接在Rainbond平台及其他容器平台安装">
                    <a onClick={() => {this.queryExport('docker-compose')}} style={{marginRight: 8}} href="javascript:;">导出Compose包{this.state.is_docker_compose_exporting ? '(导出中)': ''}</a>
                    </Tooltip>
                    :null
                }
                <Tooltip title="导出后的文件可直接在Rainbond平台安装">
                <a  onClick={() => {this.queryExport('rainbond-app')}} style={{marginRight: 8}} href="javascript:;">导出平台应用{this.state.is_rainbond_app_exporting ? '(导出中)': ''}</a>
                </Tooltip>
             </Fragment>
        )
    }
}


@connect()
export default class AppList extends PureComponent {
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
                                                <ExportBtn app={item} />
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