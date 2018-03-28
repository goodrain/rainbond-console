import React, { PureComponent, Fragment } from 'react';
import { connect } from 'dva';
import { Link, Route } from 'dva/router';
import { Row, Col, Card, Form, Button, Icon, Switch, Alert, Select, Modal, Input} from 'antd';
const FormItem = Form.Item;


@Form.create()
export default class AddPort extends PureComponent {
   componentWillMount(){

   }
   handleSubmit = (e) => {
      e.preventDefault();
      this.props.form.validateFields((err, values) => {
         if(!err){
            this.props.onOk && this.props.onOk(values);
         }
      })
   }
   handleCheckPort = (rule, value, callback) => {
      const { getFieldValue } = this.props.form;
      if(this.props.isImageApp){
         if(value<1 || value > 65535){
          callback("端口范围为1-65535");
          return;
         }
      }else{
        if(value<1025 || value > 65535){
          callback("端口范围为1025-65535");
          return;
         }
      }
      callback();
    
  }
   render(){
     const { getFieldDecorator } = this.props.form;
     const formItemLayout = {
        labelCol: {
          xs: { span: 24 },
          sm: { span: 4 },
        },
        wrapperCol: {
          xs: { span: 24 },
          sm: { span: 16 },
        },
      };
     
     return (
        <Modal
          title="添加端口"
          onOk={this.handleSubmit}
          onCancel={this.props.onCancel}
          visible={true}
        >
          <Form onSubmit={this.handleSubmit}>
            <FormItem
              {...formItemLayout}
              label="端口"
            >
                {
                  getFieldDecorator('port', {
                     rules:[{required: true, message: '请添写端口'}, {validator: this.handleCheckPort}]
                  })(
                    <Input type="number" placeholder={this.props.isImageApp ? "请填写端口,范围1-63325": "请填写端口,范围1025-63325"}  />
                  )
                }
            </FormItem>
            <FormItem
              {...formItemLayout}
              label="协议"
            >
                {
                  getFieldDecorator('protocol', {
                     initialValue : 'http',
                     rules:[{required: true, message: '请添加端口'}]
                  })(
                    <Select>
                       <Option value="http">http</Option>
                       <Option value="tcp">tcp</Option>
                       <Option value="udp">udp</Option>
                       <Option value="mysql">mysql</Option>
                     </Select>
                  )
                }
            </FormItem>
          </Form>
        </Modal>
     )
   }
}