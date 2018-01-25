let baseUrl = '';
if(process.env.NODE_ENV == 'dev') {
	baseUrl = 'http://dev.goodrain.com/';
}else if(process.env.NODE_ENV == 'test'){
	baseUrl = 'http://5000.gra4b2e5.goodrain.ali-hz.goodrain.net:10080/'
}else if(process.env.NODE_ENV == 'production'){
	baseUrl = '/';
}

const config = {
	baseUrl: baseUrl,
	projectName: '好雨云帮'
}
export default config