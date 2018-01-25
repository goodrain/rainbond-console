const UrlUtil = {
	getParams(url, decode=true){
		var arr = url.split("?"), res={}
		if(!arr.length || arr.length == 1){
			return res
		}
		var search = arr[1];
		var searchArr = search.split("&");
		for(var i=0;i<searchArr.length;i++){
			var k = searchArr[i].split("=")[0];
			var v = searchArr[i].split("=")[1];
			res[k] = decode ? decodeURIComponent(v) : v;
		}
		return res;

	}
}

export default UrlUtil;