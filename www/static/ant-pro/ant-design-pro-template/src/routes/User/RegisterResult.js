import React from 'react';
import { Button } from 'antd';
import { Link } from 'dva/router';
import Result from '../../components/Result';
import styles from './RegisterResult.less';

const actions = (
  <div className={styles.actions}>
    <a href="/"><Button size="large">返回首页</Button></a>
  </div>
);

export default ({ location }) => (
  <Result
    className={styles.registerResult}
    type="success"
    title={
      <div className={styles.title}>
        你的账户：{location.state ? location.state.account : 'xxx'} 注册成功
      </div>
    }
    description=""
    actions={actions}
    style={{ marginTop: 56 }}
  />
);
