import React, {Component} from 'react';
import {connect} from 'dva';
import {Link} from 'dva/router';
import {Checkbox, Alert, Icon} from 'antd';
import Login from '../../components/Login';
import styles from './Login.less';

const {
  Tab,
  UserName,
  Password,
  Mobile,
  Captcha,
  Submit
} = Login;

@connect(({login, loading}) => ({login: {}, submitting: loading.effects['user/login']}))
export default class LoginPage extends Component {
  state = {
    type: 'account',
    autoLogin: true
  }

  onTabChange = (type) => {
    this.setState({type});
  }

  handleSubmit = (err, values) => {
    const {type} = this.state;
    if (!err) {
      this
        .props
        .dispatch({
          type: 'user/login',
          payload: {
            ...values
          }
        });
    }
  }

  changeAutoLogin = (e) => {
    this.setState({autoLogin: e.target.checked});
  }

  renderMessage = (content) => {
    return (<Alert
      style={{
      marginBottom: 24
    }}
      message={content}
      type="error"
      showIcon/>);
  }

  render() {
    const {login, submitting} = this.props;
    const {type} = this.state;
    return (
      <div className={styles.main}>
        <Login
          defaultActiveKey={type}
          onTabChange={this.onTabChange}
          onSubmit={this.handleSubmit}>
          <Tab key="account" tab="">
            {login.status === 'error' && login.type === 'account' && !login.submitting && this.renderMessage('账户或密码错误')
}
            <UserName name="nick_name" placeholder="用户名/邮箱"/>
            <Password name="password" placeholder="密码"/>
          </Tab>
          <div>
            <Checkbox checked={this.state.autoLogin} onChange={this.changeAutoLogin}>自动登录</Checkbox>

          </div>
          <Submit loading={submitting}>登录</Submit>
          <div className={styles.other}>

            <Link className={styles.register} to="/user/register">注册账户</Link>
          </div>
        </Login>
      </div>
    );
  }
}
