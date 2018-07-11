import React, {PureComponent} from 'react';
import styles from './style.less';

export default class Index extends PureComponent {
    render(){
        return (
            <span className={styles.goodrain_rz} {...this.props}>
                官方认证
            </span>
        )
    }
}