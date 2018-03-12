import React, { PureComponent } from 'react';
import { Form, Button, Input, Modal} from 'antd';
const FormItem = Form.Item;

@Form.create()
export default class EditGroupName extends PureComponent {
   onOk = (e) => {
      e.preventDefault();
    this.props.form.validateFields({force: true}, (err, vals)=>{
       if(!err){
          this.props.onOk && this.props.onOk(vals)
       }
    })
   }
   render() {
     const {title, onCancel, onOk, group_name} = this.props;
     const { getFieldDecorator, getFieldValue } = this.props.form;
     const formItemLayout = {
      labelCol: {
        xs: { span: 24 },
        sm: { span: 6 },
      },
      wrapperCol: {
        xs: { span: 24 },
        sm: { span: 16 }
      },
    };
     return (
        <Modal
           title={title  || '新建应用组'}
           visible = {true}
           onCancel={onCancel}
           onOk={this.onOk}
        >
          <Form onSubmit={this.onOk}>
              <FormItem
              {...formItemLayout}
              label="组名称"
              >
              {
                getFieldDecorator('group_name', {
                  initialValue: group_name || '',
                  rules:[{required: true, message: '请填写组名称'}]
                })(
                  <Input placeholder="请填写组名称" />
                )
              }
              </FormItem>
          </Form>
        </Modal>
      )
   }
}