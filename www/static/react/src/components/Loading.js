import React, {Component} from 'react';
import { Sider, Spin } from 'antd';
import { connect } from 'react-redux';

class Loading extends Component {
	constructor(props) {
		super(props);
	}
	render() {
		return (
			<div  style={{display: this.props.isAppLoading ? 'block' : 'none', zIndex: 2000}}>
				<div className="loadbg">
		            <div className="loadbox">
		                <div className="loading-center-absolute">
		                    <div className="object" id="object_one"></div>
		                    <div className="object" id="object_two"></div>
		                    <div className="object" id="object_three"></div>
		                </div>
		                <div className="loadtext">加载中</div>
		            </div>
		        </div>
	        </div>
		)
	}
}

function mapStateToProps(state, props){
	return {
		isAppLoading: state.isAppLoading
	}
}

export default connect(mapStateToProps)(Loading);

