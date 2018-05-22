import React, { PureComponent } from 'react';
import { Button, Icon, Modal, Form, Checkbox, Input } from 'antd';
import { getTeamPermissions } from '../../services/team';
import RolePermsSelect from '../RolePermsSelect';

const FormItem = Form.Item;
const CheckboxGroup = Checkbox.Group;

@Form.create()
class ConfirmModal extends PureComponent{
   constructor(arg){
     super(arg);
     this.state = {
        actions: []
     }
   }
   componentDidMount(){

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
      const { onOk, onCancel, actions}= this.props;
      const data = this.props.data || {};

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

      const options = actions || [];
      const options_ids = data ? (data.role_perm||[]).map((item)=>{return item.perm_id}) : [];

      return (
          <Modal
            title={this.props.title || "添加角色"}
            visible={true}
            width={800}
            onOk={this.handleSubmit}
            onCancel={onCancel}
          >

             <Form onSubmit={this.handleSubmit}>
              <FormItem
                {...formItemLayout}
                label="角色名称"
                hasFeedback
              >
                {getFieldDecorator('role_name', {
                    initialValue: data.role_name || '',
                    rules: [{
                      required: true,
                      message: '请输入角色名称',
                    }],
                  })(
                    <Input />
                )}
                
              </FormItem>

              <FormItem
                {...formItemLayout}
                label="选择权限"
              >
                {getFieldDecorator('options_ids', {
                    initialValue:options_ids || '',
                    rules: [{
                      required: true,
                      message: '请选择权限',
                    }],
                  })(
                    <RolePermsSelect datas={options} />
                )}
                
              </FormItem>
              </Form>

             
          </Modal>
      )
   }
}

export default ConfirmModal