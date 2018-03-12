import React, {Component} from 'react';
import {connect} from 'react-redux';
import {Button, Layout} from 'antd';
const { Header, Content, Sider }  = Layout;
import {HashRouter as Router, Route, Redirect, Switch} from 'react-router-dom';
import SiteHeader from './SiteHeader';
import SiteFooter from './SiteFooter';
import Loading from './Loading';

import lazyController from '../utils/lazyController';
import Authent from './Authent';

import LoadLogin from 'bundle-loader?lazy!../pages/login';
import LoadRegister from 'bundle-loader?lazy!../pages/register';
import LoadBackPassword from 'bundle-loader?lazy!../pages/back-password';
import LoadBindPhone from 'bundle-loader?lazy!../pages/bind-phone';



class Routers extends Component {
	render(){
		const userInfo = this.props.userInfo;
		const dispatch = this.props.dispatch;
		console.log('routers')
		return (

				<Layout>
					<SiteHeader  dispatch={dispatch} />
					<Content style={{minHeight: 500,padding:'60px 16px', position:'relative'}}>
							<Switch>
								<Route exact path="/login" component={lazyController(LoadLogin)}></Route>
								<Route path="/register" component={lazyController(LoadRegister)}></Route>
								<Route path="/backpassword/:redirect" component={lazyController(LoadBackPassword)}></Route>
								<Route path="/bindphone/:uid/:redirect" component={lazyController(LoadBindPhone)}></Route>
							</Switch>
					</Content>
					<SiteFooter />
				</Layout>
		)
	}
}

export default connect(
	
)(Routers);