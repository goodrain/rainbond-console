import React, { PureComponent } from 'react';
import { connect } from 'dva';
import { Link, Switch, Route, routerRedux } from 'dva/router';
import { Row, Col, Card, Form, Button, Icon, Menu, Dropdown, notification, Select, Input} from 'antd';
import globalUtil from '../../utils/global';



const { Option } = Select;
const formItemLayout = {
  labelCol: {
    span: 5,
  },
  wrapperCol: {
    span: 19,
  },
};

@Form.create()
export default class Index extends PureComponent {
	constructor(props){
		super(props);
		this.state = {
			
		}
	}
	handleSubmit = (e) => {
		e.preventDefault();
		const form = this.props.form;
		form.validateFields((err, fieldsValue) => {
	        if (err) return;
	        this.props.onSubmit && this.props.onSubmit(fieldsValue)
	    });
	}
	render(){
		const { getFieldDecorator, getFieldValue } = this.props.form;
		const data = this.props.data || {};

		return (
			        <Form  layout="horizontal" hideRequiredMark>
			          <Form.Item
			            {...formItemLayout}
			            label="好雨Git密码"
			          >
			            {getFieldDecorator('password', {
			              initialValue: data.password || '',
			              rules: [{ required: true, message: '请输入密码' }],
			            })(
			              <Input type="password" placeholder="同云帮登录密码" />
			            )}
			          </Form.Item>
			          <Form.Item
			            {...formItemLayout}
			            label="邮箱"
			          >
			            {getFieldDecorator('email', {
			              initialValue: data.email || '',
			              rules: [{required: true, type: 'email', message: '邮箱格式不正确' }],
			            })(
			              <Input readOnly={!!data.email} placeholder="请输入邮箱" />
			            )}
			          </Form.Item>
			          <Form.Item
			            wrapperCol={{
			              xs: { span: 24, offset: 0 },
			              sm: { span: formItemLayout.wrapperCol.span, offset: formItemLayout.labelCol.span },
			            }}
			            label=""
			          >
			            <Button   onClick={this.handleSubmit} type="primary">
			              确认提交
			            </Button>
			          </Form.Item>
			        </Form>

		)
	}
}