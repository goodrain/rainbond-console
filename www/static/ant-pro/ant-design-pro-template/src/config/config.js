let baseUrl = '';
let imageUploadUrl = '';
if(process.env.NODE_ENV == 'dev') {
	baseUrl = 'http://gr-debug.goodrain.com/';
}else if(process.env.NODE_ENV == 'development'){
	// baseUrl = '/api';
	baseUrl  = 'http://5000.gre7f825.goodrain.ali-hz.goodrain.net'
}else if(process.env.NODE_ENV == 'production'){
	baseUrl = '';
}

imageUploadUrl = baseUrl + '/console/files/upload';
const config = {
	baseUrl: baseUrl,
	imageUploadUrl: imageUploadUrl
}
export default config