/*
	初始化云帮信息的组件
*/
import React, {Component} from 'react';
import {connect} from 'react-redux';
import { checkIsPublic } from '../api/comm-api';
import { getUserInfo } from '../api/user-api';
import userUtil from '../utils/user-util';
import { withRouter, matchPath } from 'react-router'

class CheckUser extends Component {
	constructor(arg){
		super(arg);
	}
	componentWillMount(){
		const dispatch = this.props.dispatch;
		this.checkLogin(this.props)
	}
	componentWillReceiveProps(nextProps){
		this.checkLogin(nextProps)
	}
	checkLogin(props){
		
		const match = matchPath(props.location.pathname, {
		  path: '/users/:id',
		  exact: true,
		  strict: false
		})
	}
	render(){
		const children = this.props.children;
		const userInfo = this.props.userInfo;
		return this.props.children;
		if(!userInfo){
			return null;
		}else{
			return this.props.children;
		}
	}
}

function mapStateToProps(state, props){
	return {
		userInfo:  state.userInfo,
		router: state.router
	}
}

export default withRouter(connect(
	mapStateToProps
)(CheckUser));