import React, {Component} from 'react';
var echarts = require('echarts');

class Echarts extends Component {
	componentDidMount(){
		var ref = this.ref;
		var option = this.props.option;
		if(ref && option){
			this.char = echarts.init(ref);
			this.char.setOption(option);
		}
	}
	saveRef = (ref) => {
		this.ref = ref;
    }
    componentWillReceiveProps(nextProps){

    }
	componentDidUpdate(){
		var option = this.props.option;

		if(this.char && option){
			this.char.setOption(option);
		}
	}
	render(){
		var className = this.props.className || '';
		var style = this.props.style || {};
		return (
			<div ref={this.saveRef} className={'echars-wrap '+className} style={{display: 'inline-bock', marginLeft: 'auto',marginRight:'auto', ...style}}>
			</div>
		)
	}
}

export default Echarts;
