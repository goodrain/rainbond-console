import React, {Component} from 'react';
import { connect } from 'react-redux';
import {Redirect} from 'react-router';
import userUtil from '../utils/user-util';
import {Link} from 'react-router-dom';

class Authent extends Component {
	constructor(props) {
		super(props);
	}
  componentWillMount(){
     if(!userUtil.isLogin()){
        this.handleTologin();
     }
  }
  handleTologin(){
      userUtil.toLogin();
  }
	render() {
    const userInfo = this.props.userInfo;
    const Com = this.props.component;
    if(!userInfo || !userUtil.isLogin()){
        return <Redirect to="/login"/>;
    }

		return (
        <Com {...this.props} />
            
		)
	}
}

function mapStateToProps(state, props){
	return {
		userInfo: state.userInfo
	}
}


const ConnectAuthent =  connect(mapStateToProps)(Authent);

const AuthentComponent = (component) => {
  return  (props) => {
      return (<ConnectAuthent component={component} {...props} />)
  }

}

export default AuthentComponent;



