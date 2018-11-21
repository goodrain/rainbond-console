import React from 'react';
import { createDevTools } from 'redux-devtools';
import LogMonitor from 'redux-devtools-log-monitor';//日志监控
import DockMonitor from 'redux-devtools-dock-monitor';//代码监控

export default createDevTools(
  //创建DevTools组件
  <DockMonitor
    defaultIsVisible={false}
    toggleVisibilityKey="ctrl-h"
    changePositionKey="ctrl-w">
    <LogMonitor />
  </DockMonitor>
);
