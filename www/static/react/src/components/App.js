import React, {Component} from 'react';
import {connect} from 'react-redux';

import {HashRouter as Router, Route, Redirect, Switch} from 'react-router-dom';
import SiteHeader from './SiteHeader';
import SiteFooter from './SiteFooter';
import Loading from './Loading';
import cookie from '../utils/cookie-util';
import http from '../utils/http';
import Routers from './routers';
import AppInit from './app-init';
import CheckIsPublic from './check-is-public';
import CheckLogin from './check-login';
import ListenRouter from './listen-router';
import Filters from './filters';
require('../../style/them.css')

class App extends Component {
	constructor(props){
		super(props);
	}
	componentWillMount(){
		//验证登录
		const token = cookie.get('token');
		if(token && user){
			http.setToken(token);
			this.props.dispatch({
				type: 'LOGIN',
				userInfo:{
					token: token
				}
			})
		}
	}
	render(){
		const userInfo = this.props.userInfo;
		const dispatch = this.props.dispatch;
		return (
			<Router history={this.props.history}>
				<ListenRouter>
					<AppInit>
					    <Filters>
							<Routers />
						</Filters>
					</AppInit>	
				</ListenRouter>
			</Router>
		)
	}
}

function mapStateToProps(state, props){
	return {
		userInfo: state.userInfo
	}
}

export default connect(
	mapStateToProps
)(App);