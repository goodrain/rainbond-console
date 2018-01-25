import http from '../utils/http';
import config from '../config/config';
import cookie from '../utils/cookie-util';


/*
	获取是否是公有云
*/
export function checkIsPublic(dispatch){
	return http({
		url:config.baseUrl + 'console/checksource',
		type: 'get',
		isTipError: false,
		async: false
	}, dispatch)
}
