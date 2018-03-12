/*
	初始化云帮信息的组件
*/

import React, {Component} from 'react';
import {connect} from 'react-redux';
import { checkIsPublic } from '../api/comm-api';
import { getUserInfo } from '../api/user-api';
import {  } from '../api/team-api';
import userUtil from '../utils/user-util';


class AppInit extends Component {
	constructor(arg){
		super(arg);
		this.state = {
			inited: false
		}
	}
	componentWillMount(){
		const dispatch = this.props.dispatch;
		checkIsPublic(
			dispatch
		).done((data)=>{
			dispatch({
				type: 'ISPUBLIC',
				payload: data.bean.is_public
			})
		}).done(()=>{
			return getUserInfo(
				dispatch
			).done((data)=>{
				dispatch({
					type: 'LOGIN',
					userInfo: data.bean
				})
			}).fail((data, code)=>{
				
			})
		}).always(()=>{

			this.setState({inited: true})
		})
	}
	render(){
		const isAppInited = this.state.inited;
		if(isAppInited){
			console.log(this.props.children)
			return this.props.children
		}else{
			return <h1> 初始化中...</h1>
		}
	}
}

function mapStateToProps(state, props){
	return {
		isAppInited:  state.isAppInited,
		userInfo: state.userInfo,
		teams:state.teams,
		regions:state.regions
	}
}

export default connect(
	mapStateToProps
)(AppInit);