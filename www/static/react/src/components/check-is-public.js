import React, {Component} from 'react';
import {connect} from 'react-redux';
import { checkIsPublic } from '../api/comm-api';


class CheckIsPublic extends Component {
	componentWillMount(){
		const dispatch = this.props.dispatch;
		checkIsPublic(
			dispatch, 
		).done((data) => {
			dispatch({
				type: 'ISPUBLIC',
				payload: data.bean.is_public
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
)(CheckIsPublic);