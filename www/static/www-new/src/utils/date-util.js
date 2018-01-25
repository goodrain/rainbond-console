const dateUtil = {
	format: function(date, format) {
		var date = new Date(date);
		var map = {
			yyyy: function(){
				return date.getFullYear()
			},
			MM: function(){
				var val = date.getMonth() + 1;
				return val < 10 ? '0'+val : val;
			},
			dd: function(){
				var val = date.getDate();
				return val < 10 ? '0'+val : val;
			},
			hh: function(){
				var val = date.getHours();
				return val < 10 ? '0'+val : val;
			},
			mm: function() {
				var val = date.getMinutes();
				return val < 10 ? '0'+val : val;
			},
			ss: function(){
				var val = date.getSeconds();
				return val < 10 ? '0'+val : val;
			}
		}
		for(var k in map){
			format = format.replace(k, map[k]);
		}
		return format;
	},

	/*
		根据日期返回今天，昨天，前天，或者日期
	*/
	dateToCN: function(date, format){

		//是否是昨天
		function isToday(str) {
		    var d = new Date(str);
		    var todaysDate = new Date();
		    if (d.setHours(0, 0, 0, 0) == todaysDate.setHours(0, 0, 0, 0)) {
		        return true;
		    } else {
		        return false;
		    }
		}

		//是否昨天
		function isYestday(date){
			var d = new Date(date);
			var date = (new Date());    //当前时间
		    var today = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime(); //今天凌晨
		    var yestday = new Date(today - 24*3600*1000).getTime();
		    return d.getTime() < today && yestday <= d.getTime();
		}
		//是否是前天
		function isBeforeYestday(date){
			var d = new Date(date);
			var date = (new Date());    //当前时间
		    var today = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime(); //今天凌晨
		    var yestday = new Date(today - 24*3600*1000).getTime();
		    var beforeYestday = new Date(today - 48*3600*1000).getTime();
		    return d.getTime() < yestday && beforeYestday <= d.getTime();
		}

		function getShowData(date){
			if(isToday(date)){
				return '今天';
			}else if(isYestday(date)){
				return '昨天';
			}else if(isBeforeYestday(date)){
				return '前天';
			}
			return dateUtil.format(date, format);
		}
		return getShowData(date)
	
	}
}
export default dateUtil;