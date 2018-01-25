import React, {Component} from 'react';
import ReactDOM from 'react-dom';
import {connect} from 'react-redux';
import {Table, Icon, message, Card} from 'antd';
import RegisterForm from '../components/register-form';
import {Link} from 'react-router-dom';
import { register } from '../api/user-api';
import urlUtil from '../utils/url-util';
require('../../style/register.css');


class Register extends Component {
	constructor(props){
		super(props);
		this.state = {
			success: false
		}
		this.timer = null;
	}
	componentWillMount(){
		this.props.dispatch({
			type: 'SET_REDIRECT',
			redirect: this.props.match.params.redirect
		})
	}
	componentDidMount(){
		var toLoginDom = document.querySelector(".to-login");
		toLoginDom.style.display = "block";
	}
	componentWillUnmount(){
		clearTimeout(this.timer);
		document.querySelector(".to-login").style.display = "none";
	}
	onSubmit = (data) => {
		register(this.props.dispatch, data).done((data) => {
			message.success("注册成功， 3秒后自动跳转");
			this.timer = setTimeout(() => {
				location.hash="/"
			}, 3000)
		})
	}
	render(){
		const redirect = this.props.match.params.redirect;
		return (
			<div className="register-wrap">
				<Card title="欢迎注册好雨云帮">
					<div className="register-form-wrap">
						{!this.state.success ? <RegisterForm dispatch={this.props.dispatch} redirect={redirect} onSubmit={this.onSubmit} /> : '' }
					</div>
				</Card>
			</div>
		)
	}
}

export default connect()(Register)