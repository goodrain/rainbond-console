/*
	应用付费时后台返回的应用数据业务对象
*/


class PayAppADT {
	constructor(app){
		this.app = app || {};
	}
	//应用id
	getAppId(){
		return this.app.service_id||'';
	}
	//租户id
	getTenantId(){
		return this.app.tenant_id || '';
	}
	//应用名称
	getAppName(){
		return this.app.service_cname||'';
	}
	//获取租户名称
	getTenantName(){
		return this.app.tenant_name || '';
	}
	//获取应用别名
	getAppAlias(){
		return this.app.service_alias || '';
	}
	//是否已经内存包月
	isMemoryPayed(){
		return this.app.memory_pay_method === 'prepaid';
	}
	//是否已经磁盘包月
	isDiskPayed(){
		return this.app.disk_pay_method === 'prepaid';
	}
	//内存是否可以延长时间
	canAddMemoryDate(){
		return this.isMemoryPayed();
	}
	//硬盘是否可以延长时间
	canAddDiskDate(){
		return this.isDiskPayed();
	}
	//内存是否可以调整大小
	canAddMemorySize(){
		return this.isMemoryPayed();
	}
	//磁盘是否可以调整大小, 后台接口暂时没有
	canAddDiskSize(){
		return false;
	}
	//获取该应用的可用总内存， min_memory * min_node
	getTotalMemory(unit){
		var memory = this.getNodeNum() * this.getNodeMemory();
		if(unit === true){
			return memory + 'M';
		}else{
			return memory;
		}
	}
	//获取硬盘大小
	getDisk(unit){
		var disk = (this.app.disk || 0);
		if(disk % 1024 > 0){
			disk = Math.round(disk/1024, 2);
		}else{
			disk = disk/1024;
		}

		if(unit === true){
			return disk + 'G';
		}else{
			return disk;
		}
	}
	//获取节点数量
	getNodeNum(){
		return this.app.min_node || 0;
	}
	//获取应用单个节点的可用内存
	getNodeMemory(unit){
		var memory = (this.app.min_memory || 0);
		if(unit === true){
			return memory+ 'M';
		}else{
			return memory;
		}
	}
	getMemoryUnit(){
		return 'M';
	}
	getDiskUnit(){
		return 'G';
	}
	//包月结束日期
	getEndDate(){
		return this.app.buy_end_time.split(' ')[0]
	}
	//包月结束日期，加时分秒
	getEndDateTime(){
		return this.app.buy_end_time;
	}
}

export default PayAppADT;