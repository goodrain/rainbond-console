import cookie from './cookie';


const regioniUtil = {
	actionToCN(action=[]){
		var res = [];
		res = action.map((item) => {
			return actionMap[item]
		});
		return res.join(', ')
	},
	//获取监控页面 SocketUrl
	getMonitorWebSocketUrl(bean) {
		var uri = bean.websocket_uri;

		if(uri[uri.length-1]!=='/'){
			uri = uri + '/';
		} 

		return uri + 'new_monitor_message'
	},
	//获取操作日志SocketUrl
	getEventWebSocketUrl(bean) {
		var uri = bean.websocket_uri;
		if(uri[uri.length-1]!=='/'){
			uri = uri + '/';
		} 
		return uri + 'event_log'
	}

}

export default regioniUtil;