/*
   应用状态bean 工具类
*/

const appStatusUtil = {
    //是否可以部署
    canDeploy: function (appStatus) {
        const activeAction = appStatus.activeAction || [];
        return activeAction.indexOf('deploy') > -1;
    },
    //是否可以重启
    canRestart: function (appStatus) {
        const activeAction = appStatus.activeAction || [];
        return activeAction.indexOf('reboot') > -1;
    },
    //是否可以启动
    canStart: function (appStatus) {
        const activeAction = appStatus.activeAction || [];
        return activeAction.indexOf('restart') > -1;
    },
    //是否可以访问
    canVisit: function (appStatus) {
        const activeAction = appStatus.activeAction || [];
        return activeAction.indexOf('visit') > -1;
    },
    //是否可以关闭
    canStop: function (appStatus) {
        const activeAction = appStatus.activeAction || [];
        return activeAction.indexOf('stop') > -1;
    },
    //是否可以进入管理容器
    canManageDocker: function (appStatus) {
        const activeAction = appStatus.activeAction || [];
        return activeAction.indexOf('manage_container') > -1;
    }
}

export default appStatusUtil;