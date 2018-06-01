import React from 'react';
import { Avatar, List, Badge } from 'antd';
import classNames from 'classnames';
import styles from './NoticeList.less';

export default function NoticeList({
  data = [], onClick, onClear, title, locale, emptyText, emptyImage,
}) {
  if (data.length === 0) {
    return (
      <div style={{textAlign: 'center'}}>
        {emptyImage ? (
          <img src={emptyImage} alt="not found" />
        ) : null}
        <div style={{padding: '50px 0'}}>{emptyText || locale.emptyText}</div>
        <div className={styles.clear} onClick={onClear}>
          查看历史消息
        </div>
      </div>
    );
  }
  return (
   
    <div>
      <List className={styles.list}>
        {data.map((item, i) => {
          const itemCls = classNames(styles.item, {
            [styles.read]: item.read,
          });
          return (
            <List.Item className={itemCls} key={item.key || i} onClick={() => onClick(item)}>
              <List.Item.Meta
                className={styles.meta}
                avatar={item.avatar ? <Avatar className={styles.avatar} src={item.avatar} /> : null}
                title={
                  <div className={styles.title}>
                    {item.title}
                <div className={styles.extra}>{item.is_read === false ? <Badge status="error" /> : null}</div>
                  </div>
                }
                description={
                  <div>
                    <div className={styles.description} title={item.description}>
                      {"查看详情"}
                    </div>
                    <div className={styles.datetime}>{item.datetime}</div>
                  </div>
                }
              />
            </List.Item>
          );
        })}
      </List>
      <div className={styles.clear} onClick={onClear}>
         查看历史消息
      </div>
    </div>
  );
}
