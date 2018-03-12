import React from 'react';
import { Route, Redirect } from 'react-router-dom';
import Authorized from './Authorized';
import { connect } from 'dva';

class PublicLogin extends React.Component {
  componentDidMount(){
      location.href = 'https://sso.goodrain.com'
  }
  render(){
      return null;
  }
}

class AuthorizedRoute extends React.Component {
  getNoMatch(){
      const { isPubCloud, logined, render, authority,
      redirectPath, ...rest } = this.props;

      if(isPubCloud && redirectPath === '/user/login'){
          return <PublicLogin />
      }

      return <Route {...rest} render={() => <Redirect to={{ pathname: redirectPath }} />} />
  }
  render() {
    const { component: Component, logined, render, authority,
      redirectPath, ...rest } = this.props;
    
    return (
      <Authorized
        authority={authority}
        logined={logined}
        noMatch={this.getNoMatch()}
      >
        <Route
          {...rest}
          render={props => (Component ? <Component {...props} /> : render(props))}
        />
      </Authorized>
    );
  }
}

export default connect(({ global }) => {

  return {
    isPubCloud: global.isPubCloud,
  }
})(AuthorizedRoute);

