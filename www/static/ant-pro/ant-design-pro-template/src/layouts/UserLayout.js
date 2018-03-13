import React from 'react';
import {Link, Redirect, Switch, Route} from 'dva/router';
import DocumentTitle from 'react-document-title';
import {Icon} from 'antd';
import GlobalFooter from '../components/GlobalFooter';
import styles from './UserLayout.less';
import logo from '../../public/images/logo.png';
import {getRoutes} from '../utils/utils';

const links = [
  {
    key: 'help',
    title: '帮助',
    href: ''
  }, {
    key: 'privacy',
    title: '隐私',
    href: ''
  }, {
    key: 'terms',
    title: '条款',
    href: ''
  }
];

const copyright = <div>Copyright
  <Icon type="copyright"/>
  2018 好雨科技</div>;

class UserLayout extends React.PureComponent {
  getPageTitle() {
    const {routerData, location} = this.props;
    const {pathname} = location;
    let title = '好雨云帮';
    if (routerData[pathname] && routerData[pathname].name) {
      title = `${routerData[pathname].name} - 好雨云帮`;
    }
    return title;
  }
  componentDidMount() {
    var load = document.getElementById('load');
    if (load) {
      document
        .body
        .removeChild(load);
    }
  }
  render() {
    const {routerData, match} = this.props;

    return (
      <DocumentTitle title={this.getPageTitle()}>
        <div className={styles.container}>
          <div className={styles.content}>
            <div className={styles.top}>
              <div className={styles.header}>
                <Link to="/">
                  <img alt="logo" className={styles.logo} src={logo}/>
                </Link>
              </div>
              <div className={styles.desc}>无服务器Pass、以应用为中心、软件定义一切</div>
            </div>
            <Switch>
              {getRoutes(match.path, routerData).map(item => (<Route
                key={item.key}
                path={item.path}
                component={item.component}
                exact={item.exact}/>))}
              <Redirect exact from="/user" to="/user/login"/>
            </Switch>
          </div>
          <GlobalFooter links={links} copyright={copyright}/>
        </div>
      </DocumentTitle>
    );
  }
}

export default UserLayout;
