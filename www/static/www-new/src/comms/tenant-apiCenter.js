/*   租户相关api请求功能  */
import http from '../utils/http';
import utils from '../utils/util';
import widget from '../ui/widget';
var Msg = widget.Message;
/*
    分享应用组
*/
export function getAllApp(tenantName) {
    var dfd = $.Deferred();
    http({
        type : "get",
        url : "/ajax/" + tenantName + "/apps"
    }).done(function(data){
        if(data.success === false){
            Msg.warning(data.message);
            dfd.reject(data);
        }else{
            dfd.resolve(data);
        }
    }).fail(function(data){
        dfd.reject(data);
    })
    return dfd;
}