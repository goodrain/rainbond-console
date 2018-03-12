/*
	初始化云帮信息的组件
*/

import React, {Component} from 'react';
import {connect} from 'react-redux';
import { checkIsPublic } from '../api/comm-api';
import { getUserInfo } from '../api/user-api';
import userUtil from '../utils/user-util';


class CheckIsPublic extends Component {
	componentWillMount(){
		const dispatch = this.props.dispatch;
		checkIsPublic(
			dispatch
		).done((data)=>{
			dispatch({
				type: 'ISPUBLIC',
				payload: data.bean.is_public
			})
		})

		// .done(()=>{
		// 	return getUserInfo(
		// 		dispatch
		// 	).done(()=>{
		// 		dispatch({
		// 			type: 'LOGIN',
		// 			userInfo: data.bean
		// 		})
		// 	})
		// }).always(()=>{
		// 	dispatch({
		// 		type: 'INITED'
		// 	})
		// })
	}
	render(){
		return this.props.children;
	}
}

function mapStateToProps(state, props){
	return {
		
	}
}

export default connect(
	mapStateToProps
)(CheckIsPublic);