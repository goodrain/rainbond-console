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
  Upload
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
<<<<<<< HEAD
import GuideManager from '../../components/Guide/guideManager';
=======
>>>>>>> b9a20d48de0914837196de5486c1ea098ffeb5a4

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
        console.log(this.state.fileList)
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
      target: 'searchWrap'
    }
  }
  componentDidMount() {
    this.getApps();
    setTimeout(()=>{
      this.setState({target: 'importApp'});
    }, 3000)
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
  onUpload = () => {
     this.setState({showUpload: true})
  }
  handleCancelUpload = () => {
     this.setState({showUpload: false})
  }
  renderApp = (item) => {

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
     actions={[<span onClick={() => {
       this.showCreate(item)
     }}>安装</span>
    //  ,<span onClick={() => {
    //    this.onUpload()
    //  }}>导出</span>
     ]}>
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
<<<<<<< HEAD

=======
>>>>>>> b9a20d48de0914837196de5486c1ea098ffeb5a4
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
          <GuideManager />
      </PageHeaderLayout>
    );
  }
}
