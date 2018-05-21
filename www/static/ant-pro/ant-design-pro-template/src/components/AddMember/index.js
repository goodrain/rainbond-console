import React, { PureComponent } from 'react';
import { Button, Icon, Modal, Form, Checkbox, Select, Input } from 'antd';
import {connect} from 'dva';
import { getTeamPermissions } from '../../services/team';
import globalUtil from '../../utils/global';

const Option = Select.Option;
const FormItem = Form.Item;
import UserSelect from '../UserSelect';
const CheckboxGroup = Checkbox.Group;

@Form.create()
@connect(({}) => ({}))
class ConfirmModal extends PureComponent{
   constructor(arg){
     super(arg);
     this.state = {
        actions: [],
        roles: []
     }
   }
   componentDidMount(){
      this.loadRoles();
   }
   loadRoles = () => {
    const {dispatch} = this.props;
    const team_name = globalUtil.getCurrTeamName();
    const region_name = globalUtil.getCurrRegionName();
    dispatch({
      type: 'teamControl/getRoles',
      payload: {
        team_name: team_name,
        page_size: 10000,
        page: 1
      },
      callback: (data) => {
        this.setState({
          roles: data.list || [],
          roleTotal: data.total
        })
      }
    })
  }
   handleSubmit= () => {
      
       this.props.form.validateFields((err, values) => {
        if (!err) {
          this.props.onOk && this.props.onOk(values);
        }
      });
   }
   render(){
      const { getFieldDecorator } = this.props.form;
      const { onOk, onCancel}= this.props;
      const data = this.props.data;
      const formItemLayout = {
        labelCol: {
          xs: { span: 24 },
          sm: { span: 6 },
        },
        wrapperCol: {
          xs: { span: 24 },
          sm: { span: 14 },
        },
      };
      const tailFormItemLayout = {
        wrapperCol: {
          xs: {
            span: 24,
            offset: 0,
          },
          sm: {
            span: 14,
            offset: 6,
          },
        },
      };
      const roles = this.state.roles || [];

      return (
          <Modal
            title="添加成员"
            visible={true}
            onOk={this.handleSubmit}
            onCancel={onCancel}
          >

             <Form onSubmit={this.handleSubmit}>
              {
                 data ? 
                 <FormItem
                  {...formItemLayout}
                  label="用户名"
                  hasFeedback
                >
                  {getFieldDecorator('user_name', {
                      initialValue: data.user_name || '',
                      rules: [{
                        required: false,
                        message: '请输入用户名称',
                      }],
                    })(
                      <Input disabled placeholder="请输入用户名称" />
                  )}
                </FormItem>
                :
                <FormItem
                  {...formItemLayout}
                  label="选择用户"
                  hasFeedback
                >
                  {getFieldDecorator('user_ids', {
                      rules: [{
                        required: true,
                        message: '请选择要添加的用户',
                      }],
                    })(
                      <UserSelect />
                  )}
                </FormItem>
              }
              

              <FormItem
                {...formItemLayout}
                label="选择角色"
              >
                {getFieldDecorator('role_ids', {
                    initialValue:data ? data.role_info.map((item)=>{return item.role_id}) : [],
                    rules: [{
                      required: true,
                      message: '请选择角色',
                    }],
                  })(
                    <Select
                    mode="multiple"
                    placeholder="请选择角色"
                    style={{ width: '100%' }}
                  >
                     {
                       roles.map((role)=>{
                           return <Option value={role.role_id}>{role.role_name}</Option>
                       })
                     }
                  </Select>
                )}
                
              </FormItem>
              </Form>

             
          </Modal>
      )
   }
}

export default ConfirmModal