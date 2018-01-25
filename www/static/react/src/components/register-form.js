import React, { Component } from 'react';
import { Form, Row, Col, Input, Button, Checkbox } from 'antd';
import { connect } from 'react-redux';
import { getPhoneCode } from '../utils/apiCenter-util';
import CountDown from './count-down';
import config from '../config/config';
const FormItem = Form.Item;
import {rules} from '../utils/validator-rules';

class RegisterForm extends Component {
	constructor(props) {
		super(props);
		this.countDownNum = this.props.countDownNum  || 50;
		this.state = {
			confirmDirty: false
		}
	}
	handleSubmit = (e) => {
	    e.preventDefault();
	    this.props.form.validateFieldsAndScroll((err, values) => {
	      if (!err) {
	        this.props.onSubmit && this.props.onSubmit(values);
	      }
	    });
	}
	handleConfirmBlur = (e) => {
	    const value = e.target.value;
	    this.setState({ confirmDirty: this.state.confirmDirty || !!value });
	}
	checkPassword = (rule, value, callback) => {
	    const form = this.props.form;
	    if (value && value !== form.getFieldValue('password')) {
	      callback('二次密码输入不一致!');
	    } else {
	      callback();
	    }
	}
	checkConfirm = (rule, value, callback) => {
	    const form = this.props.form;
	    if (value && this.state.confirmDirty) {
	      form.validateFields(['password_repeat'], { force: true });
	    }
	    callback();
	}
	countDownEnd = () => {
		this.setState({waitGetPhoneCode: false})
	}
	wechatLogin = () => {
		location.href=config.baseUrl + "wechat-login/?next="+this.props.redirect
	}
	render() {
		const { getFieldDecorator, getFieldsError, getFieldError, isFieldTouched, getFieldValue,getFieldsValue } = this.props.form;
		 const formItemLayout = {
	      labelCol: {
	        xs: { span: 24 },
	        sm: { span: 6 }
	      },
	      wrapperCol: {
	        xs: { span: 24 },
	        sm: { span: 14 }
	      }
	    };
	    const tailFormItemLayout = {
	      wrapperCol: {
	        xs: {
	          span: 24,
	          offset: 0
	        },
	        sm: {
	          span: 14,
	          offset: 6
	        }
	      }
	    };
	    const phoneNo = getFieldValue('phone_no');
		return (
			<Form onSubmit={this.handleSubmit}>
		        <FormItem
		          {...formItemLayout}
		          label={(
		            <span>
		              用户名
		            </span>
		          )}
		          hasFeedback
		        >
		          {getFieldDecorator('user_name', {
		            rules: [{ required: true, message: '请输入你的用户名' }]
		          })(
		            <Input maxLength={rules.name.value} placeholder="请输入你的用户名" />
		          )}
		        </FormItem>
		        <FormItem
		          {...formItemLayout}
		          label="密码"
		          hasFeedback
		        >
		          {getFieldDecorator('password', {
		            rules: [{
		              required: true, message: '请输入密码!'
		            },{
		            	pattern:rules.password.regx.value, message:rules.password.regx.message
		            } ,{
		              validator: this.checkConfirm
		            }]
		          })(
		            <Input maxLength={rules.password.maxLength.value} type="password" placeholder={rules.password.regx.message} />
		          )}
		        </FormItem>
		        <FormItem
		          {...formItemLayout}
		          label="确认密码"
		          hasFeedback
		        >
		          {getFieldDecorator('password_repeat', {
		            rules: [{
		              required: true, message: '请确认你的密码!'
		            }, {
		              validator: this.checkPassword
		            }]
		          })(
		            <Input maxLength={rules.password.maxLength.value} type="password" placeholder="请重复输入密码" onBlur={this.handleConfirmBlur} />
		          )}
		        </FormItem>
		        <FormItem
		          {...formItemLayout}
		          label="邮箱"
		          hasFeedback
		        >
		          {getFieldDecorator('email', {
		            rules: [{ required: true, message: '请输入您的邮箱地址!' },{
		            	pattern:rules.email.regx.value, message:rules.email.regx.message
		            }]
		          })(
		            <Input maxLength={rules.email.maxLength.value} placeholder="请输入您的邮箱地址" />
		          )}
		        </FormItem>
		        <FormItem
		          {...formItemLayout}
		          label="验证码"
		          hasFeedback
		        >
		          <Row gutter={8}>
		            <Col span={12}>
		              {getFieldDecorator('captcha_code', {
		                rules: [{ required: false, message: '请输验证码!' },{
		            	pattern:rules.captchaCode.regx.value, message:rules.captchaCode.regx.message
		            }]
		              })(
		                <Input maxLength={rules.captchaCode.maxLength.value} size="large" placeholder="请输入验证码" />
		              )}
		            </Col>
		          </Row>
		        </FormItem>
		        <FormItem {...tailFormItemLayout}>
		          <Button style={{width: '100%'}} type="primary" htmlType="submit" size="large">注册</Button>
		        </FormItem>
		      </Form>
		)
	}
}
const ConnectedRegisterForm = Form.create()(RegisterForm);
export default ConnectedRegisterForm;