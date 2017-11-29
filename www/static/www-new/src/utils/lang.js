const lang = {
	'owed' : '余额不足请及时充值',
	'expired' : '试用已到期',
	'language' : '应用语言监测未通过',
	'often' : '操作正在进行中，请稍后',
	'over_memory' : '资源已达上限，不能升级',
	'over_money' : '余额不足，不能升级',
	'no_support' : '当前服务不支持修改'
}

const getLang = {
	get: function(key, backup) {
		return lang[key] || backup || '';
	}
}


export default  getLang;