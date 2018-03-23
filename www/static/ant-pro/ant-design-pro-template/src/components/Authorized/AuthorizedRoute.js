import React from 'react';
import {Route, Redirect} from 'react-router-dom';
import Authorized from './Authorized';
import {connect} from 'dva';

class PublicLogin extends React.Component {
  componentWillMount() {
    var href = `https://sso.goodrain.com/#/login/${encodeURIComponent(location.href)}`;
    location.href = href;
  }
  componentDidMount() {}
  render() {
    return null;
  }
}

class AuthorizedRoute extends React.Component {
  getNoMatch() {
    const {
      isPubCloud,
      logined,
      render,
      authority,
      redirectPath,
      rainbondInfo,
      ...rest
    } = this.props;

    if (redirectPath === '/user/login') {

      if (rainbondInfo && rainbondInfo.is_public) {
        return < PublicLogin />
    } else {

      return <Route
        {...rest}
        render={() => <Redirect to={{
        pathname: redirectPath
      }}/>}/>
    }
  } else {

    return <Route
      {...rest}
      render={() => <Redirect to={{
      pathname: redirectPath
    }}/>}/>
  }

}
render() {
  const {
    component: Component,
    logined,
    render,
    authority,
    redirectPath,
    rainbondInfo,
    ...rest
  } = this.props;

  return (
    <Authorized authority={authority} logined={logined} noMatch={this.getNoMatch()}>
      <Route
        {...rest}
        render={props => (Component
        ? <Component {...props}/>
        : render(props))}/>
    </Authorized>
  );
}
}

export default connect(({global}) => {
return ({rainbondInfo: global.rainbondInfo})
})(AuthorizedRoute);
