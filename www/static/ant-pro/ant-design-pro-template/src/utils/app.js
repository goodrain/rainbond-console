/*
    配置应用各个状态下的各种对应信息
*/
const appStatusMap = {
    running: {
        statusCN: '运行中',
        bgClass: 'bg-green',
        disabledAction: ["restart"],
        activeAction: [
            'stop', 'deploy', 'visit', 'manage_container'
        ],
        iconUrl: '/static/www/img/appOutline/appOutline0.png'
    },
    starting: {
        statusCN: '启动中',
        bgClass: 'bg-yellow',
        disabledAction: [
            'deploy', 'restart', 'visit', 'manage_container'
        ],
        activeAction: ['stop'],
        iconUrl: '/static/www/img/appOutline/appOutline7.png'
    },
    checking: {
        statusCN: '检测中',
        bgClass: 'bg-yellow',
        disabledAction: [
            'deploy', 'restart', 'visit', 'manage_container'
        ],
        activeAction: ["stop"],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    },
    stoping: {
        statusCN: '关闭中',
        bgClass: 'bg-yellow',
        disabledAction: [
            'deploy', 'restart', 'stop', 'visit', 'manage_container'
        ],
        activeAction: [],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'

    },
    unusual: {
        statusCN: '运行异常',
        bgClass: 'bg-red',
        disabledAction: [
            'visit', 'restart', 'manage_container'
        ],
        activeAction: [
            'stop', 'deploy'
        ],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    },
    closed: {
        statusCN: '已关闭',
        bgClass: 'bg-red',
        disabledAction: [
            'visit', "stop", 'manage_container'
        ],
        activeAction: [
            'restart', 'deploy'
        ],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    },
    owed: {
        statusCN: '余额不足已关闭',
        bgClass: 'bg-red',
        disabledAction: [
            'deploy', 'visit', 'restart', 'stop', 'manage_container'
        ],
        activeAction: ['pay'],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    },
    Owed: {
        statusCN: '余额不足已关闭',
        bgClass: 'bg-red',
        disabledAction: [
            'deploy', 'visit', 'restart', 'stop', 'manage_container'
        ],
        activeAction: ['pay'],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    },
    expired: {
        statusCN: '试用已到期',
        bgClass: 'bg-red',
        disabledAction: [
            'visit', 'restart', 'deploy', 'stop', 'manage_container'
        ],
        activeAction: ['pay'],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    },
    undeploy: {
        statusCN: '未部署',
        bgClass: 'bg-gray',
        disabledAction: [
            'restart', 'stop', 'visit', 'manage_container'
        ],
        activeAction: ['deploy'],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    },
    unKnow: {
        statusCN: '未知',
        bgClass: 'bg-red',
        disabledAction: [
            'deploy', 'restart', 'stop', 'visit', 'manage_container'
        ],
        activeAction: [],
        iconUrl: '/static/www/img/appOutline/appOutline1.png'
    }
}

/*

   应用详情bean 工具类

*/

const appUtil = {
    appStatusToBadgeStatus: function (status) {
        var map = {
            running: 'success',
            starting: 'processing',
            checking: 'processing',
            stoping: 'processing',
            unusual: 'error',
            closed: 'error',
            owed: 'error',
            Owed: 'error',
            expired: 'error',
            undeploy: 'default',
            unKnow: 'error'

        }
        return map[status] || map.unKnow;
    },
    getStatusMap: function (status) {
        return status
            ? (appStatusMap[status] || appStatusMap['unKnow'])
            : appStatusMap;
    },
    //根据应用status返回对应的中文描述
    getAppStatusCN: function (status) {
        var map = appStatusMap[status] || appStatusMap['unKnow'];
        return map.statusCN;
    },
    //根据应用status返回对应的css类
    getAppStatusClass: function (status) {
        var map = appStatusMap[status] || appStatusMap['unKnow'];
        return map.bgClass;

    },
    //根据当前应用状态， 返回互斥的操作状态
    getDisableActionByStatus: function (status) {
        var map = appStatusMap[status] || appStatusMap['unKnow'];
        return map.disabledAction;
    },
    //根据应用状态， 返回当前可以进行的操作
    getActiveActionByStatus: function (status) {
        var map = appStatusMap[status] || appStatusMap['unKnow'];
        return map.activeAction;
    },
    //是否已安装性能分析插件
    isInstalledPowerPlugin: function (appDetail) {
        return false;
    },
    //是否可以管理应用
    canManageApp: function (appDetail) {
        const activeAction = appDetail.tenant_actions || [];
        return activeAction.indexOf('manage_service') > -1;
    },
    //是否可以删除
    canDelete: function (appDetail) {
        const activeAction = appDetail.tenant_actions || [];
        return activeAction.indexOf('delete_service') > -1;
    },
    //是否可以转移组
    canMoveGroup: function (appDetail) {
        return true;
    },
    //是否可以部署应用
    canDeploy: function(appDetail){
        const activeAction = appDetail.tenant_actions || [];
        return activeAction.indexOf('code_deploy') > -1;
    },
    //应用安装来源 source_code 源码 market 云市 docker_compose、docker_run、docker_image 镜像
    getInstallSource: function (appDetail) {
        return appDetail.service.service_source
    },
    //是否是云市安装的应用
    isMarketApp: function (appDetail) {
        const source = this.getInstallSource(appDetail);
        return source === 'market';
    },
    //是否是镜像安装的应用
    isImageApp: function (appDetail) {
        const source = this.getInstallSource(appDetail);
        return source === 'docker_compose' || source === 'docker_run' || source === 'docker_image';
    },
    //是否是源码创建的应用
    isCodeApp: function(appDetail){
        const source = this.getInstallSource(appDetail);
        return source === 'source_code';
    },
    //是否是dockerfile类型的应用
    //获取源码创建应用的语言类型
    getLanguage: function (appDetail) {
        var language = appDetail.service.language || '';
        if (language) {
            language = language
                .replace(/\./, '')
                .toLowerCase();
        }
        return language;
    },
    //是否是java类型的语言
    isJava: function (appDetail) {
        var language = this.getLanguage(appDetail);
        return (language === 'java-war' || language === 'java-jar' || language === 'java-maven')
    },
    //是否是dockerfile类型的应用, dockerfile类型的应用也属于源码类型的应用
    isDockerfile: function(appDetail){
        
        var language = this.getLanguage(appDetail);
        return language === 'dockerfile';
    },
    //判断该应用是否创建完成
    isCreateComplete: function (appDetail) {
        var service = appDetail.service || {};
        return service.create_status === 'complete';
    },
    //是否是Compose方式创建的应用
    isCreateFromCompose: function (appDetail) {
        const source = this.getInstallSource(appDetail);
        return source === 'docker_compose'
    },
    //是否是源码创建的应用
    isCreateFromCode: function(appDetail){
        const source = this.getInstallSource(appDetail);
        return source === 'source_code';
    },
    //是否是自定义源码创建的应用
    isCreateFromCustomCode: function(appDetail) {
        var service = appDetail.service || {};
        return this.isCreateFromCode(appDetail) && service.code_from === 'gitlab_manual';
    },
    getCreateTypeCN: function(appDetail) {
        var source = this.getInstallSource(appDetail);
        var map = {
            'source_code' : '源码',
            'market': '云市',
            'docker_compose': 'DockerCompose',
            'docker_run' : 'DockerRun',
            'docker_image': '镜像'
        }
        return map[source] || '';
    }

}

export default appUtil;