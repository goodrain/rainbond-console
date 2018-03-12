import React, { PureComponent, Fragment } from 'react';
import { connect } from 'dva';
import { Button, Table, Modal, notification} from 'antd';
import { unOpenRegion } from '../../services/team';
import globalUtil from '../../utils/global';



//开通数据中心
@connect(({ user, teamControl }) => ({
  currUser: user.currentUser,
}))
class OpenRegion extends PureComponent { 
   constructor(props){
     super(props);
     this.state = {
       selectedRowKeys:[],
       regions:[]
     }
   }
   componentDidMount(){
     this.getUnRelationedApp();
   }
   handleSubmit = () => {
      if(!this.state.selectedRowKeys.length){
        notification.warning({
          message: '请选择要开通的数据中心'
        })
        return;
      }

      this.props.onSubmit && this.props.onSubmit(this.state.selectedRowKeys);

   }
   getUnRelationedApp = () => {
       unOpenRegion({
         team_name: globalUtil.getCurrTeamName()
      }).then((data) => {
          if(data){
              this.setState({regions: data.list || []})
          }
      })
   }
   handleCancel = () => {
     this.props.onCancel && this.props.onCancel();
   }
   render(){
      const rowSelection = {
        onChange: (selectedRowKeys, selectedRows) => {
           this.setState({selectedRowKeys: selectedRows.map((item)=>{return item.region_name})})
        }
      };

      return (
        <Modal
        title="开通数据中心"
        width={600}
        visible={true}
        onOk={this.handleSubmit}
        onCancel = {this.handleCancel}
        >
        <Table
          size="small"
          pagination = {false}
          dataSource={this.state.regions || []}
          rowSelection = {rowSelection}
          columns={[{
            title: '数据中心',
            dataIndex: 'region_alias'
          },{
            title: '简介',
            dataIndex: 'desc'
          }]}
         />
         </Modal>
      )
   }
}

export default OpenRegion;