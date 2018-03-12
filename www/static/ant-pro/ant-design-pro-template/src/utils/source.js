const sourceUtil = {
	getMemoryAndUnit(memory, num=2){

		if(memory === void 0){
			return ''
		}

		if(memory < 1024){
			return memory + 'M'
		}else{
			var res = memory/1024;
			if(res%1 === 0){
				return res + 'G';
			}else{
				return res.toFixed(num, 2) + 'G';
			}
			
		}
	},
	getDiskAndUnit(disk,  num=2){
		if(disk === void 0){
			return ''
		}

		if(disk < 1024){
			return disk.toFixed(num) + 'G';
		}else{
			return (disk/1024).toFixed(num) + 'T';
		}
		
	},
	getNetAndUnit(net, num=2){
		if(net === void 0){
			return ''
		}

		return net.toFixed(num) + 'G';
	},
	getMonthlyAndUnit(month_num){
		if(month_num === void 0){
			return ''
		}
		if(month_num<12){
			return month_num+'个月';
		}
		return (month_num/12) + '年';
	}
}
export default sourceUtil;