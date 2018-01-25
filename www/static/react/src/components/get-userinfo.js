import React, {Component} from 'react';
import {connect} from 'react-redux';
import { getUserInfo } from '../api/user-api';
import userUtil from '../utils/user-util';


class GetUserInfo extends Component {
	componentWillMount(){
		const dispatch = this.props.dispatch;
		getUserInfo(
			dispatch, 
		).done((data) => {
			dispatch({
				type: 'LOGIN',
				userInfo: data.bean
			})
		})
	}
	componentWillUpdate(){
		
	}
	render(){
		return (
			this.props.children
		)
	}
}

function mapStateToProps(state, props){
	return {
		
	}
}

export default connect(
	mapStateToProps
)(GetUserInfo);