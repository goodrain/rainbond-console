import React, {Component} from 'react';
import ReactDOM from 'react-dom';
import {Form, Input, Icon, Button, Card, Row, Col} from 'antd';
import {Link} from 'react-router-dom';
import { bindPhone, getPhoneCode } from '../utils/apiCenter-util';
import CountDown from '../components/count-down';
import {rules} from '../utils/validator-rules';

const FormItem = Form.Item;
require('../../style/login.css');

class BindPhone extends Component {
	constructor(props){
		super(props);
		this.state = {
			waitGetPhoneCode: false,
			isGetintPhoneCode: false
		}
	}
	handleSubmit = (e) => {
	    e.preventDefault();
	    this.props.form.validateFields((err, values) => {
	      if (!err) {
	        	bindPhone(
	        		this.props.dispatch,
	        		values.phone,
	        		this.props.uid,
	        		values.captcha
	        	).done((data) => {
	        		location.href=decodeURIComponent(this.props.redirect);
	        	})
	      }
	    });
	}
	countDownEnd = () => {
		this.setState({waitGetPhoneCode: false})
	}
	getPhoneCode = () => {
		
		this.props.form.validateFields(['phone'], { force: true }, (err, values) => {
			if(!err){
				this.setState({isGetintPhoneCode: true});
				getPhoneCode(this.props.dispatch, values.phone).done((data) => {
					this.setState({waitGetPhoneCode: true})
				}).always(() => {
					this.setState({isGetintPhoneCode: false});
				})
			}
		})
		
	
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
	    const phone = getFieldValue('phone');
	    return (
	    		<Form onSubmit={this.handleSubmit} className="bind-phone-form hCenter">
			        <FormItem
			          hasFeedback
			        >
			        	{getFieldDecorator('phone', {
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
			        <FormItem>
			          <Button type="primary" htmlType="submit" className="login-form-button">
			            确认绑定
			          </Button>
			        </FormItem>
			    </Form>
		)
	}
}

let BindPhoneForm = Form.create()(BindPhone);

class BindPhonePage extends Component {
	render(){
		const redirect = this.props.match.params.redirect;
		const uid = this.props.match.params.uid;
		return (
			<Card title="绑定手机号" className="bind-phone-card hCenter">
				<BindPhoneForm uid={uid} redirect={redirect} />
			</Card>

		)
	}
}


export default BindPhonePage;