
const categoryMap = {
	'net-plugin:up': '入口网络',
	'net-plugin:down': '出口网络',
	'analyst-plugin:perf': '性能分析',
	'init-plugin': '初始化类型',
	'general-plugin': '一般类型',
	'downstream_net_plugin': '网络治理',
	'perf_analyze_plugin': '性能分析'
}


const inType = {
	'env': '环境变量',
	'auto': '主动发现'
}

const metaType = {
	  'un_define': '不依赖',
	  'upstream_port': '应用端口',
	  'downstream_port': '下游应用端口'
}

const buildStatusMap = {
	'unbuild': '未构建',
	'building': '构建中',
	'build_success': '构建成功',
	'build_fail': '构建失败',
	'time_out': '构建超时'
}

const versionStatusMap = {
	'fixed': '固定',
	'unfixed': '未固定'
}

export default {
	getCategoryCN : function(category){
		return categoryMap[category] || '未知类型'
	},
	getMetaTypeCN: function(v){
		return metaType[v] || '未知'
	},
	getInjectionCN: function(v){
		return inType[v] || '未知'
	},
	//是否从云市安装的插件
	isMarketPlugin: function(bean){
		 return bean.origin !== 'source_code'
	},
	//获取插件版本构建状态的中文描述
	getBuildStatusCN: function(status) {
		return buildStatusMap[status] || '未知'
	},
	//获取插件版本构建状态的中文描述
	getVersionStatusCN: function(status) {
		return versionStatusMap[status] || '未知'
	},
	//是否可以修改基本信息和配置组信息, 已经版本固定的不能进行修改
	canEditInfoAndConfig: function(bean) {
		return bean.plugin_version_status !== 'fixed'
	},
	//是否可以构建
	canBuild: function(bean) {
		return bean.plugin_version_status !== 'fixed' && 
		bean.build_status !== 'building'
	}

}