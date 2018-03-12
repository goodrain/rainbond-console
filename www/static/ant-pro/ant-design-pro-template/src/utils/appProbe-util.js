/*
   应用健康检测模型util
*/

const appProbeUtil = {
   //获取初始化等候时间, 单位秒
   getInitWaitTime: function(probeBean){
      return probeBean.initial_delay_second
   },
   //获取检测间隔时间, 单位秒
   getIntervalTime: function(probeBean){
      return probeBean.period_second
   },
   //获取检测超时时间, 单位秒
   getTimeoutTime: function(probeBean) {
        return probeBean.timeout_second
   },
   //获取连续检测成功次数
   getSuccessTimes: function(probeBean){
      return probeBean.success_threshold
   },
   //获取连续检测失败次数
   getFailTimes: function(probeBean){
      return probeBean.failure_threshold
   },
   //获取检测的接口
   getPort: function(probeBean){
      return probeBean.port;
   },
   //获取使用的探针协议
   getProtocol: function(probeBean){
      return probeBean.scheme
   },
   //获取请求头，http协议下有效
   getHeaders: function(probeBean){
      return probeBean.http_header
   },
   //获取路径，http协议下有效
   getPath: function(probeBean){
      return probeBean.path
   },

   //获取检测类型中文描述
   getcnName: function(probeBean){
      if(probeBean.mode === 'readiness'){
          return '启动时检测'
      }

      if(probeBean.mode === 'liveness') {
          return '运行时检测'
      }

      return ''
   },

   //是否是启动时检测
   isStartProbe: function(probeBean) {
       return probeBean.mode === 'readiness'
   },
   //是否是运行时检测
   isRunningProbe: function(probeBean) {
       return probeBean.mode === 'liveness'
   },
   //是否开启
	isUsed: function(probeBean){
      return probeBean.is_used
   }
}

export default appProbeUtil;