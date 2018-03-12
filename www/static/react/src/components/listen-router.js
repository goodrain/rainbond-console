import React, {Component} from 'react';
import { connect } from 'react-redux';
import { withRouter, matchPath } from 'react-router'

class ListenRouter extends Component {
	constructor(props) {
		super(props);
	}
	componentDidMount(){
		this.props.history.listen(()=>{
			console.log(this.props.history)
			this.props.dispatch({
				type:'ROUTER',
				payload: this.props.history.location.pathname
			})

		})
	}
	render() {
		return this.props.children;
	}
}


export default withRouter(connect()(ListenRouter));

