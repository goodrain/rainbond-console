import React from 'react';
import CheckPermissions from './CheckPermissions';
import userUtil from '../../utils/user';

class Authorized extends React.Component {
  render() {
    const { children, authority, noMatch = null, logined } = this.props;
    const childrenRender = typeof children === 'undefined' ? null : children;
    return CheckPermissions(
      authority,
      childrenRender,
      noMatch,
      logined
    );
  }
}

export default Authorized;
