import React, { PureComponent } from 'react';
import { Button, Icon, Modal, Form, Checkbox } from 'antd';
import { getTeamPermissions } from '../../services/team';
import TeamPermissionSelect from '../TeamPermissionSelect';

const FormItem = Form.Item;
import UserSelect from '../UserSelect';
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

      return (
          <Modal
            title="添加成员"
            visible={true}
            onOk={this.handleSubmit}
            onCancel={onCancel}
          >

             <Form onSubmit={this.handleSubmit}>
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

              <FormItem
                {...formItemLayout}
                label="选择权限"
              >
                {getFieldDecorator('identity', {
                    initialValue:'admin',
                    rules: [{
                      required: true,
                      message: '请选择权限',
                    }],
                  })(
                    <TeamPermissionSelect value="access" options={options} />
                )}
                
              </FormItem>
              </Form>

             
          </Modal>
      )
   }
}

export default ConfirmModal