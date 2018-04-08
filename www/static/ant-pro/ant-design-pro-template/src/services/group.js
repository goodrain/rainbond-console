import request from '../utils/request';
import config from '../config/config';

/* 
  查询这个组的所有可监控应用的响应时间和吞吐率
*/
export async function groupMonitorData(body={team_name, group_id}){
	return request(config.baseUrl + `/console/teams/${body.team_name}/groups/${body.group_id}/monitor/batch_query`, {
	  method: 'get',
	  showLoading: false,
	  showMessage: false
	});
  }
  

/*
	应用未创建阶段的信息修改
	可部分修改
*/

export async function editAppCreateCompose(body = {
				team_name,
				group_id,
				group_name,
				compose_content
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/groups/${body.group_id}/compose_update`, {
								method: 'put',
								data: body
				});
}

/*
	获取某个应用组的信息
*/
export async function getGroupDetail(body = {
				team_name,
				group_id
}, handleError) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/groups/${body.group_id}`, {handleError: handleError});
}

/*
	获取某个应用组的应用列表
*/
export async function getGroupApps(body = {
				team_name,
				region_name,
				group_id,
				page,
				page_size
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/service/group`, {
								method: 'get',
								params: {
												group_id: body.group_id,
												page: body.page,
												page_size: body.page_size
								},
								showLoading: false
				});
}

/*
  删除组
*/
export async function deleteGroup(body = {
				team_name,
				group_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/groups/${body.group_id}`, {method: 'delete'});
}

/*
  放弃compose创建的应用， 只用在创建未完成阶段
*/
export async function deleteCompose(body = {
				team_name,
				group_id,
				compose_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/groups/${body.group_id}/delete`, {
								method: 'delete',
								data: {
												compose_id: body.compose_id
								}
				});
}

/*
  修改组
*/
export async function editGroup(body = {
				team_name,
				group_id,
				group_name
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/groups/${body.group_id}`, {
								method: 'put',
								data: {
												group_name: body.group_name
								}
				});
}

/*
  组
*/
export async function addGroup(body = {
				team_name,
				group_name
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/groups`, {
								method: 'post',
								data: {
												group_name: body.group_name
								}
				});
}

/*
	查询未完成分享记录
*/
export async function recordShare(body = {
				team_name,
				group_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/groups/${body.group_id}/share/record`, {
								method: 'get',
								params: {
												team_name: body.team_name,
												group_id: body.group_id
								}
				});
}

/*
	验证是否可以分享
*/
export async function checkShare(body = {
				team_name,
				group_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/groups/${body.group_id}/share/record`, {
								method: 'post',
								data: {
												group_id: body.group_id
								}
				});
}

/*
	放弃分享
*/
export async function giveupShare(body = {
				team_name,
				share_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/share/${body.share_id}/giveup`, {method: 'delete'});
}

/*
	查询需要分享应用信息和插件信息
*/
export async function getShare(body = {
				team_name,
				shareId
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/share/${body.shareId}/info`, {method: 'get'})
}

/*
	提交分享信息
*/
export async function submitShare(body = {
				team_name,
				share_id,
				new_info
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/share/${body.share_id}/info`, {
								method: 'post',
								data: body.new_info
				})
}

/*
  构建compose应用
*/
export async function buildCompose(body = {
				team_name,
				group_id,
				compose_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/groups/${body.group_id}/compose_build`, {
								method: 'post',
								data: {
												compose_id: body.compose_id
								}
				});
}

/*
   获取分享应用的事件信息
*/
export async function getShareEventInfo(body = {
				team_name,
				share_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/share/${body.share_id}/events`, {method: 'get'});
}

/*
    执行分享事件
*/
export async function startShareEvent(body = {
				team_name,
				share_id,
				event_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/share/${body.share_id}/events/${body.event_id}`, {method: 'post'});
}

/*
    查询分享状态
*/
export async function getShareStatus(body = {
				team_name,
				share_id,
				event_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/share/${body.share_id}/events/${body.event_id}`, {method: 'get'});
}

/*
    完成分享
*/
export async function completeShare(body = {
				team_name,
				share_id,
				event_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/share/${body.share_id}/complete`, {method: 'post'});
}
