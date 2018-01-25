import React, {Component} from 'react';
import {connect} from 'react-redux';
import {Form, Input, Icon, Button, Checkbox, Card} from 'antd';
import {Link} from 'react-router-dom';
import { login } from '../utils/login-api-util';
require('../../style/login.css');
const FormItem = Form.Item;

class Login extends Component {
	handleSubmit = (e) => {
	    e.preventDefault();
	    this.props.form.validateFields((err, values) => {
	      if (!err) {
	        	login(
	        		this.props.dispatch,
	        		values.userName,
	        		values.password
	        	)
	      }
	    });
	  }
	render(){
		const { getFieldDecorator } = this.props.form;
	    return (
		    <div className="page-login">
		    	<div className="page-login-bd">
		    		<div className="page-login-bd-l">
		    		</div>

			      	<Card  className="page-login-bd-r" title="欢迎登录好雨云帮管理后台">
					    <Form onSubmit={this.handleSubmit} className="login-form">
					        <FormItem>
					          {getFieldDecorator('userName', {
					            rules: [{ required: true, message: '请输入用户名!' }]
					          })(
					            <Input size="large" prefix={<Icon type="user" style={{ fontSize: 13 }} />} placeholder="用户名  / 手机号 ／ 邮箱" />
					          )}
					        </FormItem>
					        <FormItem>
					          {getFieldDecorator('password', {
					            rules: [{ required: true, message: '请输入密码!' }]
					          })(
					            <Input size="large" prefix={<Icon type="lock" style={{ fontSize: 13 }} />} type="password" placeholder="密码" />
					          )}
					        </FormItem>
					        <FormItem>
					          <Button size="large" type="primary" htmlType="submit" className="login-form-button">
					            登 录
					          </Button>
					        </FormItem>
					      </Form>
				  	</Card>
			  	</div>
			</div>
		)
	}
}

let loginForm = Form.create()(Login);
const connectLogin = connect()(loginForm);
export default connectLogin;