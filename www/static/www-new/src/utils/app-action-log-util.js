/*
  应用操作日志
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
    "imageUpgrade":"应用更新",
    "over_memory":"资源超限关闭"
}

const appActionLogUtil = {
	//获取操作的中文描述
	getActionCN: function(log){
		return actionCNMap[log.type];
	},
	//获取操作的状态信息，文字说明和背景颜色
	getActionStatusInfo: function(log){
		var status, bgColor;
		var status_json = {
	        "success" : "完成",
	        "failure" : "失败",
	        "timeout" : "超时",
	        "abnormal" : "异常"
	    }
	    var final_status_json = {
	        "complate" : "完成",
	        "timeout" : "超时"
	    }
	    var bg_color = {
	        "success" : "bg-success",
	        "failure" : "bg-danger",
	        "timeout" : "bg-danger",
	        "abnormal" : "bg-yellow"
	    }
		if( log["final_status"] == "complete" )
        {
            status = status_json[log["status"]];
            bgColor = bg_color[log["status"]];
        }
        else if( log["final_status"] == "timeout" ){
            status = final_status_json[log["final_status"]];
            bgColor = 'bg-danger';
        }
        else{
            status = "进行中";
            bgColor = 'bg-grey';
        }
        return {
        	text: status,
        	bgColor: bgColor
        }
	},
	//获取操作的执行者
	getActionUser: function(log){
		return log.user_name||''
	},
	//是否操作失败
	isFail: function(log){
		return log.status === 'failure'
	},
	//是否操作完成，无论失败
	isComplete: function(log){
		return log.final_status === 'complete';
	},
	//获取失败信息
	getFailMessage: function(log){

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
	//当前操作是否可以回滚
	canRollback: function(log){
		return this.isDeploy(log) && log.code_version && log.code_version.rollback;
	},
	//获取回滚的版本
	getRollbackVersion: function(log){
		return log.deploy_version;
	},
	//获取操作的时间
	getActionTime: function(log){
		return log.start_time || ''
	}
}
export default appActionLogUtil;