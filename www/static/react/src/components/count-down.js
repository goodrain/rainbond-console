import React, {Component} from 'react';
import { Sider, Spin } from 'antd';
import { connect } from 'react-redux';

class CountDown extends Component {
	constructor(props) {
		super(props);
		const num = this.props.num ? this.props.num : 60;
		this.state = {
			num : num
		}
		this.timer = null;
	}
	componentDidMount(){
		this.start();
	}
	onEnd(){
		this.props.onEnd && this.props.onEnd();
	}
	start(){
		this.setState({num: this.state.num-1}, () => {
			if(this.state.num === 0){
				this.stop();
				this.onEnd();
			}else{
				setTimeout(() => {
					this.start();
				}, 1000)
			}
		})
	}
	stop(){
		if(this.timer) {
			clearTimeout(this.timer);
		}
	}
	componentWillUnmount(){
		this.stop();
	}
	render() {
		return (
			<span>{this.state.num}</span>
		)
	}
}

export default CountDown;

