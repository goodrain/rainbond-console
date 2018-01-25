const cookie = {
	get:function getCookie(name)
	{
		var arr,reg=new RegExp("(^| )"+name+"=([^;]*)(;|$)");
		if(arr=document.cookie.match(reg))
		return unescape(arr[2]);
		else
		return null;
	},
	set: function(name,value, days, domain)
	{
		var Days = (days != void 0) ? days : 30;
		var exp = new Date();
		exp.setTime(exp.getTime() + Days*24*60*60*1000);
		domain = domain ? ';domain='+domain : '';
		const cookie = name + "="+ escape (value) + ";expires=" + exp.toGMTString()+domain;
		document.cookie = cookie;
	},
	remove: function(name)
	{
		var exp = new Date();
		exp.setTime(exp.getTime() - 1);
		var cval=this.get(name);
		if(cval!=null)
		document.cookie= name + "="+cval+";expires="+exp.toGMTString();
	}
}

export default cookie;