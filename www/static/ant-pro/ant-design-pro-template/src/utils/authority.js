// use localStorage to store the authority info, which might be sent from server in actual project.
import cookie from './cookie';

export function getAuthority() {
  return localStorage.getItem('antd-pro-authority') || 'admin';
}

export function setAuthority(data={authority, token, uid, username}) {
  return localStorage.setItem('antd-pro-authority', data.authority);
  cookie.set('token', data.token);
  cookie.set('uid', data.uid);
  cookie.set('username', data.username);
}
