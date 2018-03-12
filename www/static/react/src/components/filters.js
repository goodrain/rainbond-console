/*
	初始化云帮信息的组件
*/
import React, {Component} from 'react';
import {connect} from 'react-redux';
import { checkIsPublic } from '../api/comm-api';
import { getUserInfo } from '../api/user-api';
import userUtil from '../utils/user-util';
import { withRouter, matchPath, Redirect } from 'react-router';



function isMatch(url, path){
	var match = matchPath(url, {
	  path: path,
	  exact: true,
	  strict: false
	})
	return !!match;
}


class Filters extends Component {
	constructor(arg){
		super(arg);
	}
	componentWillMount(){
		const dispatch = this.props.dispatch;
	}
	isToLogin(){
		const pathname = this.props.router || this.props.history.location.pathname;
		//登录页面不拦截
		if(isMatch(pathname, '/login')){
			return false;
		}

		if(!this.props.userInfo){
			return true;
		}

		
	}
	render(){
		const isToLogin = this.isToLogin();
		if(isToLogin){
			return <Redirect to="/login" />
		}else{
			return this.props.children;
		}
	}
}

function mapStateToProps(state, props){
	return {
		userInfo: state.userInfo,
		router: state.router
	}
}

export default withRouter(connect(
	mapStateToProps
)(Filters));