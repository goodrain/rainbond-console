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
  Input
} from 'antd';
const FormItem = Form.Item;
const Option = Select.Option;
const {TextArea} = Input;

@Form.create()
export default class SubDomain extends PureComponent {
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
          span: 6
        }
      },
      wrapperCol: {
        xs: {
          span: 24
        },
        sm: {
          span: 18
        }
      }
    };
    
    return (
      <Modal
        title="新增二级域名"
        onOk={this.handleSubmit}
        visible={true}
        onCancel={this.handleCancel}>
        <Row gutter={24}>
            <Col className="gutter-row" span={12}>
              <Form onSubmit={this.handleSubmit}>
              
                <FormItem {...formItemLayout} label="域名">
                  {getFieldDecorator('domain', {
                    rules: [
                      {
                        required: true,
                        message: '请添加域名'
                      }, {
                        pattern: /^[0-9a-zA-Z]*$/,
                        message: '格式不正确，请输入数字或字母'
                      }

                    ]
                  })(<Input placeholder="请填写域名"/>)
      }            
                </FormItem>
              </Form>
            </Col>
            <Col className="gutter-row" span={12} style={{lineHeight:'36px'}}>
               .{this.props.sld_suffix}
            </Col>
        </Row>
      </Modal>
    )
  }
}