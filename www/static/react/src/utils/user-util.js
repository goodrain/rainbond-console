import cookie from './cookie-util';


const userUtil = {
	isLogin: function(){

		if(process.env.NODE_ENV == 'test'){
			const token = cookie.get('token') || '1nnJEew6HTLl4H8OWms9fUrMegXoOG';
			return token
		}else if(process.env.NODE_ENV == 'production'){
			const token = cookie.get('token');
			return token
		}	
	},
	getUserFormCookie: function(){
		if(process.env.NODE_ENV == 'test'){
			return {
				token: cookie.get('token') || '1nnJEew6HTLl4H8OWms9fUrMegXoOG',
				username: cookie.get('username') || 'yyqhlw',
				uid: cookie.get('uid') || '483d037aefa840e4b6dfb4fdfeeeb8e6',
				sid: cookie.get('sid')
			}
		}else if(process.env.NODE_ENV == 'production'){
			return {
				token: cookie.get('token'),
				username: cookie.get('username'),
				uid: cookie.get('uid'),
				sid: cookie.get('sid')
			}
		}
		
	},
	logout: function(){
		cookie.remove('token', {domain:'.goodrain.com'});
	},
	toLogin: function(){
		location.hash = "/login";
	}
}

export default userUtil;