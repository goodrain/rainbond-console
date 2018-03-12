import React, {Component} from 'react';
import { Layout, Icon, Row, Col, Menu, Dropdown } from 'antd';
import config from '../config/config';
import {connect} from 'react-redux';
import {Link} from 'react-router-dom';
const { Header }  = Layout;
require('../../style/header.css');

class BeforeLoginHeader extends Component {
	render(){
		return(
			<Header className="before-login-header">
				<Row>
					<Col span={12}>
						<h1 className={"site-logo"}>
							<img src="/static/images/logo.png" />
						</h1>
					</Col>
					<Col span={12} className="right">
						<p style={{display: 'none'}} className="to-register">没有账号？ 立即<Link to={"/register"} className="to-register-btn">注册</Link></p>
						<p style={{display: 'none'}} className="to-login">已有账号？ 立即<Link to={"/login"} className="to-register-btn">登录</Link></p>
					</Col>
				</Row>
			</Header>
		)
	}
}

class AfterLoginHeader extends Component {
	getMenu(){
		return <Menu>
		    <Menu.Item>
		      <a target="_blank" rel="noopener noreferrer" href="http://www.alipay.com/">1st menu item</a>
		    </Menu.Item>
		    <Menu.Item>
		      <a target="_blank" rel="noopener noreferrer" href="http://www.taobao.com/">2nd menu item</a>
		    </Menu.Item>
		    <Menu.Item>
		      <a target="_blank" rel="noopener noreferrer" href="http://www.tmall.com/">3rd menu item</a>
		    </Menu.Item>
		</Menu>
	}
	render(){
		const userInfo = this.props.userInfo;
		return(
			<Header className="after-login-header">
				<div className="login">
				</div>
				<ul className="menus">
					<li className="menus-item">
						<span className="menus-item-hd">团队</span>
						<div className="menus-item-bd">

						</div>
					</li>
					<li className="menus-item">
						<span className="menus-item-hd">数据中心</span>
						<div className="menus-item-bd">

						</div>
					</li>
				</ul>
				<div className="user-info">
					<Dropdown overlay={this.getMenu()} placement="bottomRight">
					    <span>
					      <Icon type="user" />
					      {userInfo.user_name}
					    </span>
				  	</Dropdown>
				</div>
			</Header>
		)
	}
}



class SiteHeader extends Component {
	constructor(props) {
		super(props);
	}
	handleLogout = () => {
		logout(this.props.dispatch)
	}
	render() {
		const userInfo = this.props.userInfo;
		console.log(userInfo)
		return (
			<div className="site-header">
				{!userInfo && <BeforeLoginHeader />}
				{userInfo && <AfterLoginHeader userInfo={userInfo} />}
			</div>
		)
	}
}


export default connect((state, ownProps) => {
	return {
		userInfo: state.userInfo
	}
})(SiteHeader)

