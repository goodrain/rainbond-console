export const rules = {
	//用户名
	username:{
		required: {
			value: true,
			message: '请填写用户名'
		},
		maxLength: {
			value: 24,
			message: '用户名最大长度24位'
		}

	},
	//密码
	password: {
		required: {
			value: true,
			message: "请填写密码"
		},
		maxLength: {
			value: 16,
			message: '密码最大长度16位'
		},
		regx: {
			value: /^.{8,16}$/,
			message: '长度8到16位'
		}
	},
	//手机号
	phone:{
		maxLength: {
			value: 11
		},
		regx: {
			value: /^\d{11}$/,
			message: '手机号格式不正确'
		}
	},
	//短信验证码
	phoneCode: {
		maxLength: {
			value: 6,
			message: '短信验证码最长6位'
		},
		regx: {
			value: /^\d{6}$/,
			message: '短信验证码格式不正确，只能为6位数字'
		}
	},
	//验证码
	captchaCode:{
		maxLength: {
			value: 6,
			message: '验证码最长6位'
		},
		regx: {
			value: /^\d{6}$/,
			message: '验证码格式不正确，只能为6位数字'
		}
	},
	//企业名称
	company: {
		maxLength: {
			value: 50
		}
	},
	name: {
		maxLength: {
			value: 20
		}
	},
	//邮箱
	email: {
		maxLength: {
			value: 50,
			message: '邮箱最长6位'
		},
		regx: {
			value: /^[A-Za-z0-9\u4e00-\u9fa5]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$/,
			message: '邮箱格式不正'
		}
	}
}