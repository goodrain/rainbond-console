/*  创建应用页面级api接口  */
import utils from '../utils/util';
import widget from '../ui/widget';
import http from '../utils/http';
const Msg = widget.Message;

/*
	
*/
/*
    获取应用页面初始数据
*/
export const getInstallAppPageData = (tenantName, type) => {
    var dfd = $.Deferred();
    http({
        type: 'get',
        url: '/ajax/'+ tenantName +'/ +'/appdetails/?fr='+type
    }).done((data) => {
        if(data.success === false){
            Msg.warning(data.message);
            dfd.reject(data);
        }else{
            //转换后台返回的actions
            if(data.actions){
                var actions = data.actions;
                data.actions = {};
                for(var k in actions){
                    var item = actions[k] || [];
                    for(var i=0;i<item.length;i++){
                        data.actions[item[i]] = 1;
                    }
                }
            }

            //设置
            if(type == 'settings'){
                var serviceId = data.tenantServiceInfo.service_id;
                var group_id = data.serviceGroupIdMap[serviceId];
                var group_name = "";
                if(group_id){
                    group_name = data.serviceGroupNameMap[group_id] || '未分组';
                }
                data.group_name = group_name;
                data.group_id = group_id;
            }

            dfd.resolve(data);
        }
        
    }).fail((data) => {
        dfd.reject(data);
    })
    return dfd;
}