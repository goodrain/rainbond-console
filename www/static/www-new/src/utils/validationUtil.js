const rules = {
	email: {
		reg: '^[A-Za-z0-9\\u4e00-\\u9fa5]+@[a-zA-Z0-9_-]+(\\.[a-zA-Z0-9_-]+)+$'
	},
	//正整数
	zzs: {
		reg: '^[1-9]\\d*$'
	},
	//应用环境变量名称验证
	envvar: {
		reg: '^[A-Z][A-Z0-9_]+$'
	}
}


const validation = {
	valid: function(rule, value){
		var ruleType = rules[rule];
		if(ruleType) {
			return new RegExp(ruleType.reg).test(value);
		}
		return true;
	}
}

export default validation;