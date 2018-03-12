const appPortUtil = {
	//是否打开内部访问
   isOpenInner: function(portBean){
   		return portBean.is_inner_service
   },
   //是否打开了外部访问
   isOpenOuter: function(portBean){
   		return portBean.is_outer_service
   },
   //获取绑定的域名
   getDomains: function(portBean) {
   		return portBean.bind_domains || [];
   },
   //是否可以绑定域名
   canBindDomain: function(portBean){
   		return !!(portBean.protocol === 'http');
   },
   //获取显示的标明
   getShowAlias: function(portBean) {
      var alias = portBean.port_alias || '';
   	return alias+'_HOST:'+alias+'_PORT';
   },
   //获取内部服务地址
   getInnerUrl: function(portBean) {
	   if(this.isOpenInner(portBean)){
	   	return portBean.inner_url;
	   }
	   return ''
   },
   //获取外部访问地址
   getOuterUrl: function(portBean) {
   	if(this.isOpenOuter(portBean)){
   	  	if(portBean.protocol === 'http'){
   	  	  	return 'http://' + portBean.outer_url;
   	  	}
   	   return portBean.outer_url;
   	}
   	return ''
   }
}

export default appPortUtil;