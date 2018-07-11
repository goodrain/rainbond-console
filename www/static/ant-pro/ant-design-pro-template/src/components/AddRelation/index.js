/*
  添加依赖应用
*/
import React, { PureComponent, Fragment } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import { Link, Switch, Route } from 'dva/router';
import { Row, Col, Card, Form, Button, Icon, Menu, Input,  Dropdown, Table, Modal, notification, Select} from 'antd';
import { getRelationedApp , getUnRelationedApp, addRelationedApp, removeRelationedApp } from '../../services/app';
import globalUtil from '../../utils/global';
const FormItem = Form.Item;
const Option = Select.Option;

@Form.create()
export default class AddRelation extends PureComponent {
   constructor(props){
     super(props);
     this.state = {
       selectedRowKeys:[],
       apps:[],
       page: 1,
       page_size: 6,
       total:0,
       search_key:'',
       condition:''
     }
   }
   componentDidMount(){
     this.getUnRelationedApp();
   }
   handleSubmit = () => {
      if(!this.state.selectedRowKeys.length){
        notification.warning({
          message: '请选择要依赖的应用'
        })
        return;
      }

      var ids = this.state.selectedRowKeys.map((item) => {
          return this.state.apps[item].service_id
      })
      this.props.onSubmit && this.props.onSubmit(ids);

   }
   getUnRelationedApp = () => {
       getUnRelationedApp({
         team_name: globalUtil.getCurrTeamName(),
         app_alias: this.props.appAlias,
         page: this.state.page,
         page_size: this.state.page_size,
         search_key: this.state.search_key,
         condition: this.state.condition
      }).then((data) => {
          if(data){
              this.setState({apps: data.list || [], total: data.total, selectedRowKeys: []})
          }
      })
   }
   handleCancel = () => {
     this.props.onCancel && this.props.onCancel();
   }
   onPageChange = (page) => {
     this.setState({page: page}, ()=>{
        this.getUnRelationedApp();
     })
   }
   handleSearch = (e) => {
     e.preventDefault();
     this.state.page = 1;
     this.getUnRelationedApp();
   }
   handleKeyChange = (e) => {
    this.setState({search_key: e.target.value})
   }
   handleConditionChange = (value) => {
      this.setState({condition: value})
   }
   render(){
      const rowSelection = {
        onChange: (selectedRowKeys, selectedRows) => {
           this.setState({selectedRowKeys: selectedRowKeys})
        },
        selectedRowKeys: this.state.selectedRowKeys
      };
      const { getFieldDecorator } = this.props.form;
      return (
        <Modal
        title="添加依赖"
        width={600}
        visible={true}
        onOk={this.handleSubmit}
        onCancel = {this.handleCancel}
        >
        <Form style={{textAlign: 'right', paddingBottom: 8}} layout="inline" onSubmit={this.handleSearch}>
          <FormItem>
              <Input
                size="small"
                type="text"
                onChange={this.handleKeyChange}
                value={this.state.search_key}
                placeholder="请输入关键字"
              />
          </FormItem>
          <FormItem>
              <Select
                size="small"
                style={{ width: 100 }}
                value={this.state.condition}
                onChange={this.handleConditionChange}
              >
                <Option value="">全部</Option>
                <Option value="service_name">应用名称</Option>
                <Option value="group_name">应用组</Option>
              </Select>
          </FormItem>
          <FormItem>
            <Button size="small" htmlType="submit"><Icon type="search" />搜索</Button>
          </FormItem>
        </Form>
        <Table
          size="middle"
          pagination = {{
            current: this.state.page,
            pageSize: this.state.page_size,
            total: this.state.total,
            onChange: this.onPageChange
          }}
          dataSource={this.state.apps || []}
          rowSelection = {rowSelection}
          columns={[{
            title: '应用名',
            dataIndex: 'service_cname'
          },{
            title: '所属组',
            dataIndex: 'group_name'
          }]}
         />
         </Modal>
      )
   }
}
