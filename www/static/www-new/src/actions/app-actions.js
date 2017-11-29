import { getAppInfo } from '../comms/app-apiCenter';



//获取应用详情
export function getAppInfoAction(tenantName, serviceAlias) {
	return (dispatch, getState) => {
		getAppInfo(dispatch, tenantName, serviceAlias).done(function(data){
			dispatch(setAppInfo(data));
		})
	}
}

export function setAppInfo(appInfo) {
	return {
		type: 'SET_APP_INFO',
		appInfo: appInfo
	}
}