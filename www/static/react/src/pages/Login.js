import React, {Component} from 'react';
import ReactDOM from 'react-dom';
import {Form, Input, Icon, Button, Checkbox, Card} from 'antd';
import {Link} from 'react-router-dom';
import {connect} from 'react-redux';
import { login } from '../api/user-api';
import UrlUtil from '../utils/url-util';
import config from '../config/config';
import {rules} from '../utils/validator-rules';

const FormItem = Form.Item;
require('../../style/login.css');

class Login extends Component {
	handleSubmit = (e) => {
	    e.preventDefault();
	    const redirect = this.props.redirect;
		var toHash = decodeURIComponent(redirect);
		var toHashParam = UrlUtil.getParams(toHash);

	    this.props.form.validateFields((err, values) => {
	        if (!err) {
	        	delete values.remember;
	        	login(
	        		this.props.dispatch,
	        		values
	        	).done((data) => {
	        		location.hash = '/';
	        		
	        	})
	        }
	    });
	}
	wechatLogin = () => {
		location.href=config.baseUrl + "wechat-login/?next="+this.props.redirect
	}
	render(){
		
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
	    return (

	    		<Form onSubmit={this.handleSubmit} className="login-form">
			        <FormItem>
			          {getFieldDecorator('nick_name', {
			            rules: [{ required: true, message: '请输入登录名称!' }]
			          })(
			            <Input placeholder="用户名 ／ 邮箱" />
			          )}
			        </FormItem>
			        <FormItem>
			          {getFieldDecorator('password', {
			            rules: [{ required: true, message: '请输入你的密码!' },{ pattern: rules.password.regx.value, message: rules.password.regx.message }]
			          })(
			            <Input maxLength={rules.password.maxLength.value} type="password" placeholder={rules.password.regx.message} />
			          )}
			        </FormItem>
			        <FormItem>
			          {getFieldDecorator('remember', {
			            valuePropName: 'checked',
			            initialValue: true
			          })(
			            <Checkbox>下次自动登录</Checkbox>
			          )}
			          <Link className="login-form-forgot" to={"/backpassword/"+this.props.redirect}>忘记密码？</Link>
			          <Button type="primary" htmlType="submit" className="login-form-button">
			            登录
			          </Button>
			        </FormItem>
			    </Form>
		)
	}
}

let LoginForm = Form.create()(Login);

class LoginPage extends Component {
	componentWillUnmount(){
		document.querySelector(".to-register").style.display = "none";
	}
	componentWillMount(){
		this.props.dispatch({
			type: 'SET_REDIRECT',
			redirect: this.props.match.params.redirect
		})
	}
	componentDidMount(){
		var toLoginDom = document.querySelector(".to-register");
		toLoginDom.style.display = "block";

	}
	render(){
		const redirect = this.props.match.params.redirect;
		return (
			<div className="login-wrap">
				<Card title="欢迎登录好雨云帮">
					<LoginForm dispatch={this.props.dispatch} redirect={redirect} />
				</Card>
			</div>
		)
	}
}

export default connect()(LoginPage)