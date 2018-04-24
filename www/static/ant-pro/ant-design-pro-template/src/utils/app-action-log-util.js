/*
  应用操作日志模型工具
*/
var actionCNMap = {
    "deploy": "部署",
    "restart": "启动",
    "delete": "删除",
    "stop": "关闭",
    "HorizontalUpgrade": "水平升级",
    "VerticalUpgrade": "垂直升级",
    "callback": "回滚",
    "create": "创建",
    "own_money": "应用欠费关闭",
    "expired": "应用过期关闭",
    "share-ys": "分享到云市",
    "share-yb": "分享到云帮",
    "reboot"  :"应用重启" ,
    "git-change":"仓库地址修改",
    "imageUpgrade":"应用更新"
}

const appActionLogUtil = {
	//是否正在操作中
	isActioning: function(log){
		return !!(log.final_status !== 'complete' && log.final_status !== 'timeout' && log.event_id);
	},
	//获取操作的中文描述
	getActionCN: function(log){
		return log.type_cn || '';
	},
	//获取操作的结果状态中文描述
	getActionResultCN: function(log){
		var status;
		var status_json = {
	        "success" : "完成",
	        "failure" : "失败",
	        "timeout" : "超时",
	        "abnormal" : "异常"
	    }
	    var final_status_json = {
	        "complate" : "完成",
			"timeout" : "超时",
			"failure" : "失败",
	        "timeout" : "超时"
	    }
	    
		if( log["final_status"] == "complete" )
        {
            status = status_json[log["status"]];
        }
        else if( log["final_status"] == "timeout" ){
            status = final_status_json[log["final_status"]];
        }
        else{
            status = "进行中";
        }

        return status;
	},
	//获取操作的执行者
	getActionUser: function(log){
		return log.user_name||''
	},
	//是否操作失败
	isFail: function(log){
		return !!(this.isComplete(log) && log.status === 'failure');
	},
	//是否操作超时
	isTimeout: function(log){
		return !!(this.isComplete(log) && log.status === 'timeout');
	},
	//是否操作成功
	isSuccess: function(log){
		return !!(this.isComplete(log) &&  log.status === 'success');
	},
	//是否操作完成，无论失败
	isComplete: function(log){
		return log.final_status === 'complete';
	},
	//获取失败信息
	getFailMessage: function(log){
		return log.message || ''
	},
	//获取版本提交者
	getCommitUser: function(log){
		if(log.code_version){
			return log.code_version.user;
		}
		return ''
	},
	//获取代码版本
	getCodeVersion: function(log){
		if(log.code_version){
			return log.code_version.code_version;
		}
		return ''
	},
	
	//获取版本提交说明
	getCommitLog: function(log){
		if(log.code_version){
			return log.code_version.commit;
		}
		return ''
	},
	//是否部署的操作
	isDeploy: function(log){
		return log.type === 'deploy';
	},
	//是否显示版本commit信息
	isShowCommitInfo: function(log){
		return this.isDeploy(log) && log.code_version;
	},	
	//当前操作是否可以回滚
	canRollback: function(log){
		return !!(!this.isFail(log) && this.isDeploy(log) && log.code_version && log.code_version.rollback);
	},
	//获取回滚的版本
	getRollbackVersion: function(log){
		return log.deploy_version;
	},
	//获取操作的时间
	getActionTime: function(log){
		return (log.start_time || '').split(' ')[1]
	},
	//获取操作的日期
	getActionDate: function(log){
		return (log.start_time || '').split(' ')[0]
	},
	//获取操作的日期时间
	getActionDateTime: function(log){
		return log.start_time || '';
	}
}
export default appActionLogUtil;