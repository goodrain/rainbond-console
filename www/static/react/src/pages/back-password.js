import React, {Component} from 'react';
import ReactDOM from 'react-dom';
import {Form, Input, Icon, Button, Card, Steps, Row, Col} from 'antd';
import {Link} from 'react-router-dom';
import CountDown from '../components/count-down';
import { getPhoneCode, checkPhoneCode, forgetPassword, checkMobile } from '../utils/apiCenter-util';
import {connect} from 'react-redux';
import {rules} from '../utils/validator-rules';

const FormItem = Form.Item;
const Step = Steps.Step;
require('../../style/back-password.css');



//第一步
class InputPhone extends Component {
	constructor(props){
		super(props);
		this.state = {
			waitGetPhoneCode: false,
			isGetintPhoneCode: false
		}
	}
	countDownEnd = () => {
		this.setState({waitGetPhoneCode: false})
	}

	getPhoneCode = () => {
		
		this.props.form.validateFields(['mobile'], { force: true }, (err, values) => {
			if(!err){
				this.setState({isGetintPhoneCode: true});
				getPhoneCode(this.props.dispatch, values.mobile, true).done((data) => {
					this.setState({waitGetPhoneCode: true})
				}).always(() => {
					this.setState({isGetintPhoneCode: false});
				})
			}
		})
		
	
	}

	render(){
		const { getFieldDecorator, getFieldsError, getFieldError, isFieldTouched, getFieldValue,getFieldsValue } = this.props.form;
	    const phone = getFieldValue('mobile');
	    return (
	    	<Form className="step-1-com hCenter">
		        <FormItem
		          hasFeedback
		        >
		        	{getFieldDecorator('mobile', {
		            	rules: [{ required: true, message: '请输入您的手机号!' },{
			            	pattern:rules.phone.regx.value, message:rules.phone.regx.message
			            }]
		          	})(
		            	<Input maxLength="11" placeholder="请填写手机号" />
		          	)}
		        </FormItem>
		        <FormItem
		          style={{display: phone ? '': 'none'}}
		        >
		          <Row gutter={8}>
		            <Col span={12}>
		              {getFieldDecorator('captcha', {
		                rules: [{ required: true, message: '请输入短信验证码!' },{
			            	pattern:rules.phoneCode.regx.value, message:rules.phoneCode.regx.message
			            }]
		              })(
		                <Input maxLength={rules.phoneCode.maxLength.value} size="large" placeholder="请输入短信验证码" />
		              )}
		            </Col>
		            <Col span={12}>
		             {(this.state.waitGetPhoneCode || this.state.isGetintPhoneCode) ? '' : <Button size="large" onClick={this.getPhoneCode}>获取验证码</Button>}
		              {this.state.waitGetPhoneCode ? <Button disabled size="large">获取验证码({<CountDown onEnd={this.countDownEnd} />})</Button> : ''}
		            </Col>
		          </Row>
		        </FormItem>
		    </Form>
	    )
	}
}
const InputPhoneForm = Form.create()(InputPhone);


//第二步
class InputPassword extends Component {
	constructor(props) {
		super(props);
		this.state = {
			confirmDirty: false
		}
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
	      form.validateFields(['newpassword'], { force: true });
	    }
	    callback();
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
	    return(
			<Form>
			<FormItem
			          {...formItemLayout}
			          label="新密码"
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
			          {getFieldDecorator('newpassword', {
			            rules: [{
			              required: true, message: '请确认你的密码!'
			            }, {
			              validator: this.checkPassword
			            }]
			          })(
			            <Input type="password" placeholder="请重复输入密码" onBlur={this.handleConfirmBlur} />
			          )}
			        </FormItem>
			</Form>
		)
	}
}
const InputPasswordForm = Form.create()(InputPassword);

//第三步
class Complete extends Component {
	render(){
		const redirect = this.props.redirect;
		return (
			<div className="back-password-success">
				<h1>密码重置成功！</h1>
				<p>请妥善保管您的密码！</p>
				<Button type="primary"><Link to={"/login/"+redirect}>去登录</Link></Button>
			</div>
		)
		
	}
}




const steps = [{
  title: '验证身份',
  desc: '请填写你注册时的手机号.'
},{
  title: '重置密码',
  content: '请重置密码'
}, {
  title: '完成',
  content: '恭喜您重置密码成功'
}];


class BackPassword extends Component {
	constructor(props){
		super(props);
		this.state = {
			current: 0,
			phone:''
		}
	}
	doNext = () => {
		const current = this.state.current + 1;
    	this.setState({ current }, () => {

    	});
	}
	next = () => {
		if(this.form){

			if(this.state.current == 0){
				this.form.validateFieldsAndScroll((err, values) => {
			      if (!err) {
			      	checkPhoneCode(
			      		this.props.dispatch,
			      		values.mobile,
			      		values.captcha
			      	).done(() => {
			      		this.doNext();
			        	this.setState({phone: values.mobile});
			      	})
			      	
			      }
			    });
			}

			if(this.state.current == 1){
				this.form.validateFieldsAndScroll((err, values) => {
			      if (!err) {
			         forgetPassword(
			         	this.props.dispatch,
			         	this.state.phone,
			         	values.password,
			         	values.newpassword
			         ).done(() => {
			         	this.doNext();
			         })
			      }
			    });
			}
		}
	}
	saveFormRef = (form) => {
	    this.form = form;
	}
	render(){
		const redirect = this.props.match.params.redirect;
		return (
			<div className="back-password-wrap">
				<Card title="找回密码">
					<Steps current={this.state.current} className="back-password-step">
					    {steps.map(item => <Step key={item.title} title={item.title} />)}
					</Steps>


					<div className="steps-content">
						{
							this.state.current === 0 ? 
							<InputPhoneForm ref={this.saveFormRef} />
							:''
						}
						{
							this.state.current === 1 ? 
							<InputPasswordForm ref={this.saveFormRef} />
							:''
						}
						{
							this.state.current === 2 ? 
							<Complete ref={this.saveFormRef} redirect={redirect} />
							:''
						}
					</div>
					<div className="steps-action">
						{
				            this.state.current < steps.length - 1
				            &&
				            <Button type="primary" onClick={() => this.next()}>下一步</Button>
				        }
					</div>
				</Card>
			</div>
		)
	}
}
export default connect()(BackPassword)