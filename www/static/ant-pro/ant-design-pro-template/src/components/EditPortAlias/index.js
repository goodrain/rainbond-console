import React, { PureComponent, Fragment } from 'react';
import { connect } from 'dva';
import { Link, Route } from 'dva/router';
import { Row, Col, Card, Form, Button, Icon, Switch, Alert, Select, Modal, Input} from 'antd';
const FormItem = Form.Item;


@Form.create()
export default class EditAlias extends PureComponent {
    constructor(props){
        super(props);
        this.state = {

        }
    }
    handleSubmit = (e) => {
       e.preventDefault();
       this.props.form.validateFields({ force: true }, (err, values) => {
          if(!err){
              this.props.onOk && this.props.onOk(values);
          }
       })
    }
    handleCancel = () => {
        this.props.onCancel && this.props.onCancel();
    }
    render(){
      const {getFieldDecorator} = this.props.form;
      const formItemLayout = {
        labelCol: {
          xs: { span: 24 },
          sm: { span: 5 },
        },
        wrapperCol: {
          xs: { span: 24 },
          sm: { span: 16 },
        },
      };
      const port = this.props.port || {};
      return (
          <Modal
              title="编辑别名"
              onOk={this.handleSubmit}
              visible={true}
              onCancel={this.handleCancel}
          >

            <Form onSubmit={this.handleSubmit}>
              
              <FormItem
                {...formItemLayout}
                label="别名"
              >
                  {
                    getFieldDecorator('alias', {
                       initialValue : port.port_alias,
                       rules:[{required: true, message: '请填写端口别名'}]
                    })(
                      <Input placeholder="请填写端口别名" />
                    )
                  }
              </FormItem>
            </Form>

          </Modal>
      )
    }
}