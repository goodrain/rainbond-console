const volumepathTypeToCNMap = {
	'share-file': '共享存储(文件)',
	'local' : '本地存储',
	'memoryfs': '内存文件存储'
}

const volumeUtil = {

	getTypeCN: function(type){
		return volumepathTypeToCNMap[type] || '未知';
	}
}

export default volumeUtil;