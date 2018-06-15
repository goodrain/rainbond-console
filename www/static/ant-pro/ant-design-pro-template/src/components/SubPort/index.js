import React, {PureComponent, Fragment} from 'react';
import {
  Row,
  Col,
  Card,
  Form,
  Button,
  Icon,
  Switch,
  Select,
  Modal,
  Input,
  notification
} from 'antd';
const FormItem = Form.Item;
const Option = Select.Option;
const {TextArea} = Input;

@Form.create()
export default class AddDomain extends PureComponent {
  constructor(props) {
    super(props);
    this.state = {}
  }
  handleSubmit = (e) => {
    e.preventDefault();
    this
      .props
      .form
      .validateFields({
        force: true
      }, (err, values) => {
        if (!err) {
          if(values.port == '请选择端口'){
            notification.info({message: '您还没有选择端口，请先选择端口！'});
            return
          }
          this.props.onOk && this
            .props
            .onOk(values);
        }
      })
  }
  handleCancel = () => {
    this.props.onCancel && this
      .props
      .onCancel();
  }
  render() {
    const {getFieldDecorator, getFieldValue} = this.props.form;
    const formItemLayout = {
      labelCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 5
        }
      },
      wrapperCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 16
        }
      }
    };
   const postList = this.props.postList;
   const initialVal = postList[0].lb_mpping_port
    return (
      <Modal
        title="绑定域名"
        onOk={this.handleSubmit}
        visible={true}
        onCancel={this.props.onCancel}>
        <Form onSubmit={this.handleSubmit}>

          <FormItem {...formItemLayout} label="请选择端口">
            {getFieldDecorator('port', {
              initialValue: '请选择端口',
              rules: [
                {
                  required: true,
                  message: '请选择端口'
                }
              ]
            })(
              <Select>
                {
                  postList.map((port)=>{
                      return (
                        <Option value={port.service_id  + '||' +  port.lb_mpping_port}>{port.lb_mpping_port}</Option>
                      )
                  })
                }
              </Select>
            )
}
          </FormItem>
        </Form>

      </Modal>
    )
  }
}