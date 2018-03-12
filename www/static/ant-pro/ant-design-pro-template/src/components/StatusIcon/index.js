import React, { PureComponent, Fragment } from 'react';
import styles from './index.less'

const appStatusMap = {
    running: {
        iconUrl: 'https://user.goodrain.com/static/www/img/appOutline/appOutline0.png',
        className: 'roundloading'
    },
    starting: {
        iconUrl: 'https://user.goodrain.com/static/www/img/appOutline/appOutline7.png',
        className: ''
    },
    unKnow: {
        iconUrl: 'https://user.goodrain.com/static/www/img/appOutline/appOutline1.png',
        className: ''
    }
}


class Index extends React.Component {
  constructor(props) {
    super(props);
  }
  render() {  
    const {status} = this.props;
    const url = appStatusMap[status] ? appStatusMap[status].iconUrl : appStatusMap['unKnow'].iconUrl;
    const className = appStatusMap[status] ? appStatusMap[status].className : appStatusMap['unKnow'].className;
    return (
        <img style={{width: 60, height: 60, display: 'block', marginLeft: 'auto', marginRight: 'auto'}} src={url} className={className} />
    );
  }
}

export default Index;