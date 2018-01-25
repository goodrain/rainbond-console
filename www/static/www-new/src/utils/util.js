

/*
    配置应用各个状态下的各种对应信息
*/
const appStatusMap = {
    running: {
        statusCN: '运行中',
        bgClass: 'bg-green',
        disabledAction: ["restart"],
        activeAction: ['stop', 'deploy', 'visit', 'manage_container'],
        iconUrl: '/static/www/img/appOutline/appOutline0.png'
    },
    starting: {
        statusCN: '启动中',
        bgClass: 'bg-yellow',
        disabledAction: ['deploy', 'restart', 'visit', 'manage_container'],
        activeAction: ['stop'],
        iconUrl: '/static/www/img/appOutline/appOutline7.png'
    },
    checking: {
        statusCN: '检测中',
        bgClass: 'bg-yellow',
        disabledAction: ['deploy', 'restart', 'visit', 'manage_container'],
        activeAction: ["stop"],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    },
    stoping: {
        statusCN: '关闭中',
        bgClass: 'bg-yellow',
        disabledAction: ['deploy', 'restart', 'stop', 'visit', 'manage_container'],
        activeAction: [],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'

    },
    unusual: {
        statusCN: '运行异常',
        bgClass: 'bg-red',
        disabledAction: ['visit', 'restart', 'manage_container'],
        activeAction: ['stop', 'deploy'],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    },
    abnormal: {
        statusCN: '异常',
        bgClass: 'bg-yellow'
    },
    closed: {
        statusCN: '已关闭',
        bgClass: 'bg-red',
        disabledAction: ['visit',"stop", 'manage_container'],
        activeAction: ['restart','deploy'],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    },
    owed: {
        statusCN: '余额不足已关闭',
        bgClass: 'bg-red',
        disabledAction: ['deploy', 'visit', 'restart', 'stop', 'manage_container'],
        activeAction: ['pay'],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    },
    Owed: {
        statusCN: '余额不足已关闭',
        bgClass: 'bg-red',
        disabledAction: ['deploy', 'visit', 'restart', 'stop', 'manage_container'],
        activeAction: ['pay'],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    },
    expired: {
        statusCN: '试用已到期',
        bgClass: 'bg-red',
        disabledAction: ['visit', 'restart', 'deploy', 'stop', 'manage_container'],
        activeAction: ['pay'],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    },
    undeploy: {
        statusCN: '未部署',
        bgClass: 'bg-gray',
        disabledAction: ['restart', 'stop', 'visit', 'manage_container'],
        activeAction: ['deploy'],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    },
    upgrade: {
        statusCN: '升级中',
        bgClass: 'bg-green'
    },
    unKnow: {
        statusCN: '未知',
        bgClass: 'bg-red',
        disabledAction: ['deploy', 'restart', 'stop', 'visit', 'manage_container'],
        activeAction: [],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    }
}

const util = {
    getStatusMap: function(status) {
        return status ? (appStatusMap[status] || appStatusMap['unKnow'])  : appStatusMap;
    },
    //根据应用status返回对应的中文描述
    getAppStatusCN: function(status) {
        var map = appStatusMap[status] || appStatusMap['unKnow'];
        return map.statusCN;
    },
    //根据应用status返回对应的css类
    getAppStatusClass: function(status) {
        var map = appStatusMap[status] || appStatusMap['unKnow'];
        return map.bgClass;

    },
    //根据当前应用状态， 返回互斥的操作状态
    getDisableActionByStatus: function(status) {
        var map = appStatusMap[status] || appStatusMap['unKnow'];
        return map.disabledAction;
    },
    //根据应用状态， 返回当前可以进行的操作
    getActiveActionByStatus: function(status) {
        var map = appStatusMap[status] || appStatusMap['unKnow'];
        return map.activeAction;
    },
    getAppActionStatusCN: function(status){
        return appActionStatusCN[status] || '未知'
    }
}


export default util;
