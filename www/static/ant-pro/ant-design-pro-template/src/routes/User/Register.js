import React, {Component} from 'react';
import {connect} from 'dva';
import {routerRedux, Link} from 'dva/router';
import {
  Form,
  Input,
  Button,
  Select,
  Row,
  Col,
  Popover,
  Progress
} from 'antd';
import styles from './Register.less';
import config from '../../config/config';

const FormItem = Form.Item;
const {Option} = Select;
const InputGroup = Input.Group;

const passwordStatusMap = {
  ok: <div className={styles.success}>强度：强</div>,
  pass: <div className={styles.warning}>强度：中</div>,
  poor: <div className={styles.error}>强度：太短</div>
};

const passwordProgressMap = {
  ok: 'success',
  pass: 'normal',
  poor: 'exception'
};

@connect(({user, loading}) => ({register: user.register, submitting: loading.effects['user/register']}))
@Form.create()
export default class Register extends Component {
  state = {
    count: 0,
    confirmDirty: false,
    visible: false,
    help: '',
    prefix: '86',
    time: Date.now()
  };

  componentWillReceiveProps(nextProps) {
    const account = this
      .props
      .form
      .getFieldValue('user_name');
    if (nextProps.register) {
      this
        .props
        .dispatch(routerRedux.push({pathname: '/user/register-result', state: {
            account
          }}));
    }
  }

  componentWillUnmount() {
    clearInterval(this.interval);
  }

  onGetCaptcha = () => {
    let count = 59;
    this.setState({count});
    this.interval = setInterval(() => {
      count -= 1;
      this.setState({count});
      if (count === 0) {
        clearInterval(this.interval);
      }
    }, 1000);
  };

  getPasswordStatus = () => {
    const {form} = this.props;
    const value = form.getFieldValue('password');
    if (value && value.length > 9) {
      return 'ok';
    }
    if (value && value.length > 5) {
      return 'pass';
    }
    return 'poor';
  };

  handleSubmit = (e) => {
    e.preventDefault();
    this
      .props
      .form
      .validateFields({
        force: true
      }, (err, values) => {
        if (!err) {
          this
            .props
            .dispatch({
              type: 'user/register',
              payload: {
                ...values
              },
              complete: () => {
                this.changeTime()
              }
            });
        }
      });
  };

  handleConfirmBlur = (e) => {
    const {value} = e.target;
    this.setState({
      confirmDirty: this.state.confirmDirty || !!value
    });
  };

  checkConfirm = (rule, value, callback) => {
    const {form} = this.props;
    if (value && value !== form.getFieldValue('password')) {
      callback('两次输入的密码不匹配!');
    } else {
      callback();
    }
  };

  checkPassword = (rule, value, callback) => {
    if (!value) {
      this.setState({
        help: '请输入密码！',
        visible: !!value
      });
      callback('error');
    } else {
      this.setState({help: ''});
      if (!this.state.visible) {
        this.setState({
          visible: !!value
        });
      }
      if (value.length < 6) {
        callback('error');
      } else {
        const {form} = this.props;
        if (value && this.state.confirmDirty) {
          form.validateFields(['confirm'], {force: true});
        }
        callback();
      }
    }
  };

  changePrefix = (value) => {
    this.setState({prefix: value});
  };

  renderPasswordProgress = () => {
    const {form} = this.props;
    const value = form.getFieldValue('password');
    const passwordStatus = this.getPasswordStatus();
    return value && value.length
      ? (
        <div className={styles[`progress-${passwordStatus}`]}>
          <Progress
            status={passwordProgressMap[passwordStatus]}
            className={styles.progress}
            strokeWidth={6}
            percent={value.length * 10 > 100
            ? 100
            : value.length * 10}
            showInfo={false}/>
        </div>
      )
      : null;
  };
  changeTime = (time) => {
    this.setState({
      time: Date.now()
    })
  }
  render() {
    const {form, submitting} = this.props;
    const {getFieldDecorator} = form;
    const {count, prefix} = this.state;
    return (
      <div className={styles.main}>
        <h3>注册</h3>
        <Form onSubmit={this.handleSubmit}>
          <FormItem>
            {getFieldDecorator('user_name', {
              rules: [
                {
                  required: true,
                  message: '请输入用户名！'
                }
              ]
            })(<Input size="large" placeholder="用户名"/>)}
          </FormItem>
          <FormItem>
            {getFieldDecorator('email', {
              rules: [
                {
                  required: true,
                  message: '请输入邮箱地址！'
                }, {
                  type: 'email',
                  message: '邮箱地址格式错误！'
                }
              ]
            })(<Input size="large" placeholder="邮箱"/>)}
          </FormItem>
          <FormItem help={this.state.help}>

            {getFieldDecorator('password', {
              rules: [
                {
                  validator: this.checkPassword
                }
              ]
            })(<Input size="large" type="password" placeholder="至少8位，区分大小写"/>)}
          </FormItem>
          <FormItem>
            {getFieldDecorator('password_repeat', {
              rules: [
                {
                  required: true,
                  message: '请确认密码！'
                }, {
                  validator: this.checkConfirm
                }
              ]
            })(<Input size="large" type="password" placeholder="确认密码"/>)}
          </FormItem>
          <FormItem>
            <Row gutter={8}>
              <Col span={16}>
                {getFieldDecorator('captcha_code', {
                  rules: [
                    {
                      required: true,
                      message: '请输入验证码！'
                    }
                  ]
                })(<Input size="large" placeholder="验证码"/>)}
              </Col>
              <Col span={8}>
                <img
                  onClick={this.changeTime}
                  src={config.baseUrl + '/console/captcha?_=' + this.state.time}
                  style={{
                  width: '100%',
                  height: 40
                }}/>
              </Col>
            </Row>
          </FormItem>
          <FormItem>
            <Button
              size="large"
              loading={submitting}
              className={styles.submit}
              type="primary"
              htmlType="submit">
              注册
            </Button>
            <Link className={styles.login} to="/user/login">
              使用已有账户登录
            </Link>
          </FormItem>
        </Form>
      </div>
    );
  }
}
