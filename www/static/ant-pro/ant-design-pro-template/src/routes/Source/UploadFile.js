import React, {PureComponent, Fragment} from 'react';
import {connect} from 'dva';
import {Link} from 'dva/router';
import globalUtil from '../../utils/global';
import userUtil from '../../utils/user';
import BasicListStyles from '../List/BasicList.less';
import {
    Button,
    Icon,
    Form,
    Input,
    Radio,
    notification,
    Modal,
    Upload
} from 'antd';
import config from '../../config/config'
import cookie from '../../utils/cookie';

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
export default class UploadFile extends PureComponent {
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
