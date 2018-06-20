const util = {
    /* 
        获取内部市场导出应用的下载地址
     */
    getAppExportUrl: function(body={team_name, app_id, format}){
        return `${location.protocol}//${location.host}/console/teams/${body.team_name}/apps/export/down?app_id=${body.app_id}&format=${body.format}`
    }
}

export default util