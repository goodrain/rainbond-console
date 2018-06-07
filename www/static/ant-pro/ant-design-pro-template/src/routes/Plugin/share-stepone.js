import React, {PureComponent, Fragment} from 'react';
import moment from 'moment';
import {connect} from 'dva';
import {Link} from 'dva/router';
import {
  Row,
  Col,
  Card,
  Form,
  Button,
  Input,
  Icon,
  Menu,
  Dropdown,
  Modal,
  notification,
  Select,
  Radio,
  Checkbox,
  List,
  Switch,
  Tabs,
  Divider,
  InputNumber,
  Upload
} from 'antd';
import {routerRedux} from 'dva/router';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import ConfirmModal from '../../components/ConfirmModal';
import Ellipsis from '../../components/Ellipsis';
import FooterToolbar from '../../components/FooterToolbar';
import config from '../../config/config';
import cookie from '../../utils/cookie';
import globalUtil from '../../utils/global';
import userUtil from '../../utils/user';
import styles from '../../components/PageHeader/index.less';
const FormItem = Form.Item;
const {TextArea} = Input;
const ButtonGroup = Button.Group;
const RadioGroup = Radio.Group;
const {Option} = Select;
const {SubMenu} = Menu;
const formItemLayout = {
  labelCol: {
    span: 8
  },
  wrapperCol: {
    span: 16
  }
};
const tailFormItemLayout = {
  wrapperCol: {
    xs: {
      span: 24,
      offset: 0
    },
    sm: {
      span: 14,
      offset: 6
    }
  }
};

const token = cookie.get('token');
let myheaders = {}
if (token) {
   myheaders.Authorization = `GRJWT ${token}`;
   myheaders['X_REGION_NAME'] = globalUtil.getCurrRegionName();
   myheaders['X_TEAM_NAME'] = globalUtil.getCurrTeamName();
}

const uploadButton = (
  <div>
    <Icon type="plus" />
    <div className="ant-upload-text">上传图标</div>
  </div>
);

@connect(({user, groupControl, loading}) => ({
  currUser: user.currentUser,
  apps: groupControl.apps,
  groupDetail: groupControl.groupDetail || {},
  loading: loading
}))
@Form.create()
export default class Main extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {
      toDelete: false,
      recordShare: false,
      checkShare: true,
      ShareStep: 0,
      ID: 0,
      info: null,
      key: '',
      fileList:[]
    }
  }
  getParams() {
    return {pluginId: this.props.match.params.pluginId, shareId: this.props.match.params.shareId}
  }
  componentDidMount() {
    this.getShareInfo();
  }
  getShareInfo() {
    const {dispatch, form, index} = this.props;
    const team_name = globalUtil.getCurrTeamName();
    const region_name = globalUtil.getCurrRegionName();
    const params = this.getParams();
    dispatch({
      type: 'plugin/getPluginShareInfo',
      payload: {
        team_name: team_name,
        ...params
      },
      callback: (data) => {
        this.setState({info: data.bean.share_plugin_info})
        if(data.bean.share_plugin_info.pic){
          this.setState({fileList:[{
             uid: -1,
             name: data.bean.share_plugin_info.pic,
             status: 'done',
             url: data.bean.share_plugin_info.pic
          }]})
        }
      },
      handleError: (res) => {
        if (res && res.status === 404) {
            
        }
      }
    })
  }

  handleSubmit = (e) => {
    const {dispatch} = this.props;
    var newinfo = {}
    this
      .props
      .form
      .validateFields((err, values) => {
        
        
        var url = (values.pic && values.pic.file && values.pic.file.response && values.pic.file.response.data && values.pic.file.response.data.bean) ? values.pic.file.response.data.bean.file_url : '';
        const share_plugin_info = {
          ...this.state.info,
          ...values,
          pic: url ? url : this.state.info.pic
        };
        if (!err) {
          const {dispatch} = this.props;
          const param = this.getParams();
          dispatch({
            type: 'plugin/submitSharePlugin',
            payload: {
              team_name: globalUtil.getCurrTeamName(),
              shareId: param.shareId,
              share_plugin_info
            },
            callback: (data) => {
              dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/shareplugin/step-two/${param.pluginId}/${param.shareId}`))
            }
          })
        }
      });
  }

  handleGiveup = () => {
    var pluginId = this.props.match.params.pluginId;
    const {dispatch} = this.props;
    dispatch({
      type: 'plugin/giveupSharePlugin',
      payload: {
        team_name: globalUtil.getCurrTeamName(),
        share_id: this.props.match.params.shareId
      },
      callback: (data) => {
        dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/myplugns/${pluginId}`))
      }
    })
  }
  handleLogoChange = ({ fileList }) =>{
      this.setState({ fileList })
  }
  handleLogoRemove = () => {
    this.setState({fileList: []})
  }
  componentWillUnmount() {}
  render() {
    const info = this.state.info;
    const {getFieldDecorator, getFieldValue} = this.props.form;
    const loading = this.props.loading;
    const fileList = this.state.fileList;
    if(info === null) return null;
    return (
      <PageHeaderLayout>
        <div>
          <Card
            style={{
            marginBottom: 24
          }}
            title="基本信息"
            bordered={false}
            bodyStyle={{
            padding: 0
          }}>
            <div style={{
              padding: "24px"
            }}>
              <Form layout="horizontal" className={styles.stepForm}>
                <Row gutter={24}>
                  <Col span="12">
                    <Form.Item {...formItemLayout} label='插件名'>
                      {getFieldDecorator('plugin_name', {
                        initialValue: info.plugin_name,
                        rules: [
                          {
                            required: true,
                            message: '插件名不能为空'
                          }
                        ]
                      })(<Input placeholder="默认使用上次插件名"/>)}
                    </Form.Item>

                  </Col>
                  <Col span="12">
                    <Form.Item {...formItemLayout} label='版本'>
                      {getFieldDecorator('version', {
                        initialValue: info.version,
                        rules: [
                          {
                            required: true,
                            message: '版本不能为空'
                          }
                        ]
                      })(<Input placeholder="默认使用上次的版本"/>)}
                    </Form.Item>
                  </Col>
                   <Col span="12">
                    <Form.Item {...formItemLayout} label='分享范围'>
                      {getFieldDecorator('scope', {
                        initialValue: info.scope || 'team',
                        rules: [
                          {
                            required: true
                          }
                        ]
                      })(
                        <RadioGroup>
                          <Radio value='team'>团队</Radio>
                          <Radio value='enterprise'>公司</Radio>
                          <Radio value='goodrain'>好雨公有云市</Radio>
                        </RadioGroup>
                      )}
                    </Form.Item>
                  </Col>
                  <Col span="12">
                    <Form.Item {...formItemLayout} label='插件说明'>
                      {getFieldDecorator('desc', {
                        initialValue: info.desc,
                        rules: [
                          {
                            required: false,
                            message: '请输入插件说明'
                          }
                        ]
                      })(<TextArea placeholder="请输入插件说明"/>)}
                    </Form.Item>
                  </Col>
                   <Col span="12">
                    <Form.Item {...formItemLayout} label='图标'>
                        {getFieldDecorator('pic', {
                          rules: [
                            {
                              required: false,
                              message: '请上传图标'
                            }
                          ]
                        })(
                          <Upload
                            className="logo-uploader"
                            name="file"
                            accept="image/jpg,image/jpeg,image/png"
                                action={config.imageUploadUrl}
                                listType="picture-card"
                                fileList={fileList}
                                headers = {myheaders}
                                onChange={this.handleLogoChange}
                                onRemove={this.handleLogoRemove}
                              >
                                {fileList.length > 0? null:uploadButton}
                              </Upload>
                        )}
                      </Form.Item>
                  </Col>
                </Row>
              </Form>
            </div>
          </Card>
          <FooterToolbar>
            <Button type="primary" htmlType="submit" onClick={this.handleSubmit}>提交</Button>
            <Button
              disabled={loading.effects['plugin/giveupSharePlugin']}
              onClick={this.handleGiveup}>放弃分享</Button>
          </FooterToolbar>

        </div>
      </PageHeaderLayout>
    );
  }
}
