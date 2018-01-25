import React, {Component} from 'react';
import { Layout, Icon, Row, Col } from 'antd';
import config from '../config/config';
import {connect} from 'react-redux';
import {Link} from 'react-router-dom';
const { Header }  = Layout;

class SiteHeader extends Component {
	constructor(props) {
		super(props);
	}
	handleLogout = () => {
		logout(this.props.dispatch)
	}
	render() {
		return (
			<Header>
				<Row>
					<Col span={12}>
						<h1 className={"site-logo"}>
							<img src="/static/images/logo.png" />
						</h1>
					</Col>
					<Col span={12} className="right">
						<p style={{display: 'none'}} className="to-register">没有账号？ 立即<Link to={"/register/"+this.props.redirect} className="to-register-btn">注册</Link></p>
						<p style={{display: 'none'}} className="to-login">已有账号？ 立即<Link to={"/login/"+this.props.redirect} className="to-register-btn">登录</Link></p>
					</Col>
				</Row>
			</Header>
		)
	}
}


export default connect((state, ownProps) => {
	return {
		redirect: state.redirect
	}
})(SiteHeader)

