import React from 'react';
import classNames from 'classnames';
import styles from './index.less';

export default ({ className, links, copyright }) => {
  const clsString = classNames(styles.globalFooter, className);
  return (
    <div className={clsString}>
      <div className={styles.copyright}></div>
    </div>
  );
};
