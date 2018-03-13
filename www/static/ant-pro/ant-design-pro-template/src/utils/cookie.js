var Domain = "goodrain.com";
const cookie = {
				get: function getCookie(name) {
								var arr,
												reg = new RegExp("(^| )" + name + "=([^;]*)(;|$)");
								if (arr = document.cookie.match(reg)) 
												return unescape(arr[2]);
								else 
												return null;
								}
				,
				set: function (name, value, option = {}) {
								var Days = (option.days != void 0)
												? option.days
												: 30;
								var exp = new Date();
								exp.setTime(exp.getTime() + Days * 24 * 60 * 60 * 1000);
								var domain = option.domain
												? ';domain=' + option.domain
												: '';
								var path = (option.path != void 0)
												? (";path=" + option.path)
												: ";path=/";
								const cookie = name + "=" + escape(value) + ";expires=" + exp.toGMTString() + domain + path;
								document.cookie = cookie;
				},
				remove: function (name, option = {}) {
								var exp = new Date();
								exp.setTime(exp.getTime() - 1);
								var cval = this.get(name);
								var domain = option.domain !== void 0
												? ';domain=' + option.domain
												: ';domain=' + Domain;
								var path = (option.path != void 0)
												? (";path=" + option.path)
												: ";path=/";
								if (cval != null) {
												var v = name + "=" + cval + ";expires=" + exp.toGMTString() + domain + path;
												document.cookie = v;
								}
				},
				setDomain: function (str) {
								Domain = str;
				}
}

export default cookie;