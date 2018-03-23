let baseUrl = '';
if(process.env.NODE_ENV == 'dev') {
	baseUrl = 'http://gr-debug.goodrain.com/';
}else if(process.env.NODE_ENV == 'development'){
	baseUrl = '/api';
}else if(process.env.NODE_ENV == 'production'){
	baseUrl = '';
}

const config = {
	baseUrl: baseUrl
}
export default config