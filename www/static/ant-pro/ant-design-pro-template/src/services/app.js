import request from '../utils/request';
import config from '../config/config';

/*
	获取应用的历史操作日志
*/
export function getActionLog(body = {
				team_name,
				app_alias,
				page,
				page_size,
				start_time
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/events`, {
								method: 'get',
								params: {
												page: body.page,
												page_size: body.page_size,
												start_time: body.start_time || ''
								}
				});
}

/*
	获取应用某个操作历史的详细日志
	level {
	 info, debug, error
	}
*/
export function getActionLogDetail(body = {
				team_name,
				app_alias,
				level,
				event_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/event_log`, {
								method: 'get',
								params: {
												level: body.level || 'info',
												event_id: body.event_id
								}
				});
}

/*
	部署应用
*/
export function deploy(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/deploy`, {method: 'post'});
}
/*
	批量部署应用
*/
export function batchDeploy(body = {
				team_name,
				serviceIds
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/batch_actions`, {
								method: 'post',
								data: {
												action: 'deploy',
												service_ids: body.serviceIds
								}
				});
}

/*
	应用重启
*/
export function restart(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/restart`, {method: 'post'});
}

/*
	批量重启
*/
export function batchReStart(body = {
				team_name,
				serviceIds
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/batch_actions`, {
								method: 'post',
								data: {
												action: 'restart',
												service_ids: body.serviceIds
								}
				});
}

/*
	应用启动
*/
export function start(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/start`, {method: 'post'});
}
/*
	批量应用启动
*/
export function batchStart(body = {
				team_name,
				serviceIds
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/batch_actions`, {
								method: 'post',
								data: {
												action: 'start',
												service_ids: body.serviceIds
								}
				});
}

/*
	应用关闭
*/
export function stop(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/stop`, {method: 'post'});
}

/*
	批量应用关闭
*/
export function batchStop(body = {
				team_name,
				serviceIds
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/batch_actions`, {
								method: 'post',
								data: {
												action: 'stop',
												service_ids: body.serviceIds
								}
				});
}

/*
	应用回滚
*/
export function rollback(body = {
				team_name,
				app_alias,
				deploy_version
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/rollback`, {
								method: 'post',
								data: {
												deploy_version: body.deploy_version
								}

				});
}

/*
	获取应用详细信息
*/
export async function getDetail(body = {
				team_name,
				app_alias
}, handleError) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/detail`, {
								method: 'get',
								handleError: handleError
				});
}

/*
	获取应用状态
*/
export function getStatus(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/status`, {
								method: 'get',
								showLoading: false
				});
}

/*
	获取监控日志--日志页面
*/
export function getMonitorLog(body = {
				team_name,
				app_alias,
				lines
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/log`, {
								method: 'get',
								params: {
												action: 'service',
												lines: body.lines || 50
								}
				});
}

/*
	获取监控日志的websocket地址
*/
export function getMonitorWebSocketUrl(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/log_instance`, {method: 'get'});
}

/*
	历史日志下载
*/
export function getHistoryLog(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/history_log`, {method: 'get'});
}

/*
	水平升级
	new_node : 节点数量
*/
export function horizontal(body = {
				team_name,
				app_alias,
				new_node
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/horizontal`, {
								method: 'post',
								data: {
												new_node: body.new_node
								}
				});
}

/*
	垂直升级
	new_memory : 内存数量 单位 MB
*/
export function vertical(body = {
				team_name,
				app_alias,
				new_memory
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/vertical`, {
								method: 'post',
								data: {
												new_memory: body.new_memory
								}
				});
}

/*
  获取应用已依赖的其他应用
*/
export function getRelationedApp(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/dependency`, {method: 'get'});
}

/*
  获取应用可以依赖的应用
*/
export function getUnRelationedApp(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/un_dependency`, {method: 'get'});
}

/*
  添加依赖的应用
*/
export function addRelationedApp(body = {
				team_name,
				app_alias,
				dep_service_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/dependency`, {
								method: 'post',
								data: {
												dep_service_id: body.dep_service_id
								}
				});
}

/*
	删除依赖的应用
*/
export function removeRelationedApp(body = {
				team_name,
				app_alias,
				dep_service_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/dependency/${body.dep_service_id}`, {method: 'delete'});
}

/*
	获取挂载或未挂载的目录
	type: 查询的类别 mnt（已挂载的,默认）| unmnt (未挂载的)
*/
export function getMnt(body = {
				team_name,
				app_alias,
				page,
				pageSize,
				type: 'mnt'
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/mnt`, {
								method: 'get',
								params: {
												page: body.page,
												page_size: body.page_size,
												type: body.type
								}
				});
}

/*
   为应用挂载其他应用共享的存储
   body [{"id":49,"path":"/add"},{"id":85,"path":"/dadd"}]
*/
export function addMnt(body = {
				team_name,
				app_alias,
				body
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/mnt`, {
								method: 'post',
								data: {
												body: JSON.stringify(body.body || [])
								}
				});
}

/*
  取消挂载依赖
*/
export async function deleteMnt(body = {
				team_name,
				app_alias,
				dep_vol_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/mnt/${body.dep_vol_id}`, {method: 'delete'});
}

/*
	获取应用的端口
*/
export async function getPorts(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/ports`, {method: 'get'});
}

/*
   修改端口协议
*/

export async function changePortProtocal(body = {
				team_name,
				app_alias,
				port,
				protocol
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/ports/${body.port}`, {
								method: 'put',
								data: {
												action: 'change_protocol',
												protocol: body.protocol
								}
				});
}

/*
	打开端口外部访问
*/
export async function openPortOuter(body = {
				team_name,
				app_alias,
				port
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/ports/${body.port}`, {
								method: 'put',
								data: {
												action: 'open_outer'
								}
				});
}

/*
	关闭端口外部访问
*/
export async function closePortOuter(body = {
				team_name,
				app_alias,
				port
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/ports/${body.port}`, {
								method: 'put',
								data: {
												action: 'close_outer'
								}
				});
}

/*
	打开端口内部访问
*/
export async function openPortInner(body = {
				team_name,
				app_alias,
				port
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/ports/${body.port}`, {
								method: 'put',
								data: {
												action: 'open_inner'
								}
				});
}

/*
	关闭端口内部访问
*/
export async function closePortInner(body = {
				team_name,
				app_alias,
				port
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/ports/${body.port}`, {
								method: 'put',
								data: {
												action: 'close_inner'
								}
				});
}

/*
   修改端口别名
*/
export async function editPortAlias(body = {
				team_name,
				app_alias,
				port,
				port_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/ports/${body.port}`, {
								method: 'put',
								data: {
												action: 'change_port_alias',
												port_alias: body.port_alias
								}
				});
}

/*
	删除端口
*/
export async function deletePort(body = {
				team_name,
				app_alias,
				port
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/ports/${body.port}`, {method: 'delete'});
}

/*
	绑定域名
*/
export async function bindDomain(body = {
				team_name,
				app_alias,
				port,
				domain,
				protocol,
				certificate_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/domain`, {
								method: 'post',
								data: {
												domain_name: body.domain,
												container_port: body.port,
												protocol: body.protocol,
												certificate_id: body.certificate_id
								}
				});
}

/*
	解绑域名
*/
export async function unbindDomain(body = {
				team_name,
				app_alias,
				port,
				domain
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/domain`, {
								method: 'delete',
								data: {
												domain_name: body.domain,
												container_port: body.port
								}
				});
}

/*
	添加端口
*/
export async function addPort(body = {
				team_name,
				app_alias,
				port,
				protocol
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/ports`, {
								method: 'post',
								data: {
												port: body.port,
												protocol: body.protocol
								}
				});
}
/*
 获取应用的自定义环境变量
 evn
*/
export async function getInnerEnvs(body = {
				team_name,
				app_alias,
				env_type
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/envs`, {
								method: 'get',
								params: {
												env_type: 'inner'
								}
				});
}

/*
 添加应用的自定义环境变量
 name ： 说明
*/
export async function addInnerEnvs(body = {
				team_name,
				app_alias,
				name,
				attr_name,
				attr_value
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/envs`, {
								method: 'post',
								data: {
												name: body.name,
												attr_name: body.attr_name,
												attr_value: body.attr_value,
												scope: 'inner',
												is_change: true
								}
				});
}

/*
 获取应用的自定义环境变量
 evn
*/
export async function getOuterEnvs(body = {
				team_name,
				app_alias,
				env_type
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/envs`, {
								method: 'get',
								params: {
												env_type: 'outer'
								}
				});
}

/*
 添加应用的自定义环境变量
 name ： 说明
*/
export async function addOuterEnvs(body = {
				team_name,
				app_alias,
				name,
				attr_name,
				attr_value
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/envs`, {
								method: 'post',
								data: {
												name: body.name,
												attr_name: body.attr_name,
												attr_value: body.attr_value,
												scope: 'outer'
								}
				});
}

/*
 修改应用的环境变量
 name ： 说明
*/
export async function editEvns(body = {
				team_name,
				app_alias,
				name,
				attr_name,
				attr_value
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/envs/${body.attr_name}`, {
								method: 'put',
								data: {
												name: body.name,
												attr_value: body.attr_value
								}
				});
}

/*
 删除应用的环境变量
*/
export async function deleteEvns(body = {
				team_name,
				app_alias,
				attr_name
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/envs/${body.attr_name}`, {method: 'delete'});
}

/*
	获取应用运行时探测的信息
*/
export async function getRunningProbe(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/probe`, {
								method: 'get',
								params: {
												mode: 'liveness'
								}
				});
}

/*
	获取应用启动时探测的信息
*/
export async function getStartProbe(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/probe`, {
								method: 'get',
								params: {
												mode: 'readiness'
								}
				});
}

/*
	添加/编辑应用启动时探测
*/
export async function addStartProbe(body = {
				team_name,
				app_alias,
				scheme,
				path,
				port,
				initial_delay_second,
				period_second,
				timeout_second,
				success_threshold
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/probe`, {
								method: 'post',
								data: {
												mode: 'readiness',
												scheme: body.scheme,
												path: body.path,
												port: body.port,
												http_header: body.http_header,
												initial_delay_second: body.initial_delay_second,
												period_second: body.period_second,
												timeout_second: body.timeout_second,
												success_threshold: body.success_threshold
								}
				});
}

/*
	添加/编辑应用运行时探测
*/
export async function addRunningProbe(body = {
				team_name,
				app_alias,
				scheme,
				path,
				port,
				initial_delay_second,
				period_second,
				timeout_second,
				failure_threshold
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/probe`, {
								method: 'post',
								data: {
												mode: 'liveness',
												scheme: body.scheme,
												path: body.path,
												port: body.port,
												http_header: body.http_header,
												initial_delay_second: body.initial_delay_second,
												period_second: body.period_second,
												timeout_second: body.timeout_second,
												failure_threshold: body.failure_threshold
								}
				});
}

/*
	添加/编辑应用启动时探测
*/
export async function editStartProbe(body = {
				team_name,
				app_alias,
				scheme,
				path,
				port,
				initial_delay_second,
				period_second,
				timeout_second,
				success_threshold,
				is_used
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/probe`, {
								method: 'put',
								data: {
												mode: 'readiness',
												scheme: body.scheme,
												path: body.path,
												port: body.port,
												http_header: body.http_header,
												initial_delay_second: body.initial_delay_second,
												period_second: body.period_second,
												timeout_second: body.timeout_second,
												success_threshold: body.success_threshold,
												is_used: body.is_used === void 0
																? true
																: body.is_used
								}
				});
}

/*
	添加/编辑应用运行时探测
*/
export async function editRunningProbe(body = {
				team_name,
				app_alias,
				scheme,
				path,
				port,
				initial_delay_second,
				period_second,
				timeout_second,
				failure_threshold,
				is_used
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/probe`, {
								method: 'put',
								data: {
												mode: 'liveness',
												scheme: body.scheme,
												path: body.path,
												port: body.port,
												http_header: body.http_header,
												initial_delay_second: body.initial_delay_second,
												period_second: body.period_second,
												timeout_second: body.timeout_second,
												failure_threshold: body.failure_threshold,
												is_used: body.is_used === void 0
																? true
																: body.is_used
								}
				});
}

/*
	获取应用基本详情
*/
export async function getBaseInfo(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/brief`, {method: 'get'});
}

/*
	获取应用的持久化路径
*/
export async function getVolumes(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/volumes`, {method: 'get'});
}

/*
	添加应用的持久化路径
*/
export async function addVolume(body = {
				team_name,
				app_alias,
				volume_name,
				volume_type,
				volume_path
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/volumes`, {
								method: 'post',
								data: {
												volume_name: body.volume_name,
												volume_type: body.volume_type,
												volume_path: body.volume_path
								}
				});
}

/*
	删除应用的某个持久化目录
*/
export async function deleteVolume(body = {
				team_name,
				app_alias,
				volume_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/volumes/${body.volume_id}`, {method: 'delete'});
}

/*
	 获取应用平均响应时间监控数据(当前请求时间点的数据)
*/
export async function getAppRequestTime(body = {
				team_name,
				app_alias,
				serviceId
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/monitor/query`, {
								method: 'get',
								showMessage: false,
								params: {
												query: 'sum(app_requesttime{service_id="' + body.serviceId + '",mode="avg"})'
								},
								showLoading: false
				});
}

/*
	 获取应用平均响应时间监控数据(一段时间内数据)
*/
export async function getAppRequestTimeRange(body = {
				team_name,
				app_alias,
				serviceId,
				step: 7,
				start,
				end
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/monitor/query_range`, {
								method: 'get',
								showMessage: false,
								params: {
												query: 'sum(app_requesttime{service_id="' + body.serviceId + '",mode="avg"})',
												start: body.start,
												end: body.end || (new Date().getTime() / 1000),
												step: body.step
								},
								showLoading: false
				});
}

/*
	 获取应用吞吐率监控数据(当前请求时间点的数据)
*/
export async function getAppRequest(body = {
				team_name,
				app_alias,
				serviceId
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/monitor/query`, {
								method: 'get',
								showMessage: false,
								params: {
												query: 'ceil(delta(app_request{method="total",service_id="' + body.serviceId + '"}[1m])/12)'
								},
								showLoading: false
				});
}

/*
	 获取应用吞磁盘监控数据(当前请求时间点的数据)
*/
export async function getAppDisk(body = {
				team_name,
				app_alias,
				serviceId
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/monitor/query`, {
								method: 'get',
								showMessage: false,
								params: {
												query: 'app_resource_appfs{service_id="' + body.serviceId + '"}'
								},
								showLoading: false
				});
}

/*
	 获取应用吞磁盘监控数据(当前请求时间点的数据)
*/
export async function getAppMemory(body = {
				team_name,
				app_alias,
				serviceId
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/monitor/query`, {
								method: 'get',
								showMessage: false,
								params: {
												query: 'app_resource_appmemory{service_id="' + body.serviceId + '"}'
								},
								showLoading: false
				});
}

/*
	 获取应用吞吐率监控数据(一段时间内数据)
*/
export async function getAppRequestRange(body = {
				team_name,
				app_alias,
				serviceId,
				step: 7,
				start,
				end
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/monitor/query_range`, {
								method: 'get',
								showMessage: false,
								params: {
												query: 'ceil(delta(app_request{method="total",service_id="' + body.serviceId + '"}[1m])/12)',
												start: body.start,
												end: body.end || (new Date().getTime() / 1000),
												step: body.step
								},
								showLoading: false
				});
}

/*
	获取应用在线人数监控数据(当前请求时间点的数据)
*/
export async function getAppOnlineNumber(body = {
				team_name,
				app_alias,
				serviceId
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/monitor/query`, {
								method: 'get',
								showMessage: false,
								params: {
												query: 'sum(app_requestclient{service_id="' + body.serviceId + '"})'
								},
								showLoading: false
				});
}

/*
	获取应用在线人数监控数据(一段时间内数据)
*/
export async function getAppOnlineNumberRange(body = {
				team_name,
				app_alias,
				serviceId,
				step: 7,
				start,
				end
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/monitor/query_range`, {
								method: 'get',
								showMessage: false,
								params: {
												query: 'sum(app_requestclient{service_id="' + body.serviceId + '"})',
												start: body.start,
												end: body.end || (new Date().getTime() / 1000),
												step: body.step
								},
								showLoading: false
				});
}

/* 获取应用的代码分支 */
export function getCodeBranch(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/code/branch`, {method: 'get'});
}

/* 设置应用的代码分支 */
export function setCodeBranch(body = {
				team_name,
				app_alias,
				branch
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/code/branch`, {
								method: 'put',
								data: {
												branch: body.branch
								}
				});
}

/*
获取应用的伸缩信息
*/
export async function getExtendInfo(body = {
				team_name,
				app_alias
}, handleError) {

				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/extend_method`, {
								method: 'get',
								handleError: handleError
				});
}

/*
	获取应用的实例
*/
export async function getPods(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/pods`, {method: 'get'});
}

/*
	管理实例
*/
export async function managePods(body = {
				team_name,
				app_alias,
				pod_name,
				manage_name
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/pods`, {
								method: 'post',
								data: {
												c_id: body.pod_name,
												h_id: body.manage_name
								}
				});
}

/*
   获取应用的访问信息
*/
export async function getVisitInfo(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/visit`, {method: 'get'});
}

/*
	获取应用标签
*/
export async function getTags(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/labels`, {method: 'get'});
}

/*
	删除应用标签
*/
export async function deleteTag(body = {
				team_name,
				app_alias,
				label_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/labels`, {
								method: 'delete',
								data: {
												label_id: body.label_id
								}
				});
}

/*
	添加标签
*/
export async function addTags(body = {
				teamName,
				app_alias,
				tags: []
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/labels`, {
								method: 'post',
								data: body.tags
				});
}

/*
	修改应用名称
*/
export async function editName(body = {
				team_name,
				app_alias,
				service_cname
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/brief`, {
								method: 'put',
								data: {
												service_cname: body.service_cname
								}
				});
}

/*
	转移组
*/
export async function moveName(body = {
				team_name,
				app_alias,
				service_cname
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/brief`, {
								method: 'put',
								data: {
												service_cname: body.service_cname
								}
				});
}

/*
	获取设置了权限的团队成员
*/
export async function getMembers(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/perms`, {method: 'get'});
}

/*
	设置用户权限
*/
export async function setMemberAction(body = {
				team_name,
				app_alias,
				user_ids: [],
				identity
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/perms`, {
								method: 'patch',
								data: {
												user_ids: body
																.user_ids
																.join(','),
												identity: body.identity
								}
				});
}

/*
	删除成员应用权限
*/
export async function deleteMember(body = {
				team_name,
				app_alias,
				user_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/perms`, {
								method: 'delete',
								data: {
												user_id: body.user_id
								}
				});
}

/*
	修改用户权限
*/
export async function editMemberAction(body = {
				team_name,
				app_alias,
				user_ids,
				identity
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/perms`, {
								method: 'put',
								data: {
												user_id: body.user_id,
												identity: body.identity
								}
				});
}

/*
	修改应用所属组
*/
export async function moveGroup(body = {
				team_name,
				app_alias,
				group_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/group`, {
								method: 'put',
								data: {
												group_id: body.group_id
								}
				});
}

/*
	获取应用的运行环境信息
*/
export async function getRuntimeInfo(body = {
				team_name,
				app_alias,
				group_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/compile_env`, {method: 'get'});
}

/*
	修改应用的运行环境信息
*/
export async function editRuntimeInfo(body = {
				team_name,
				app_alias,
				service_runtimes,
				service_server,
				service_dependency
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/compile_env`, {
								method: 'put',
								data: {
												//服务运行版本，如php5.5等
												service_runtimes: body.service_runtimes,
												//服务使用的服务器，如tomcat,apache,nginx等
												service_server: body.service_server,
												//服务依赖，如php-mysql扩展等
												service_dependency: body.service_dependency
								}
				});
}

/*
	应用未创建阶段的信息修改
	可部分修改
*/

export async function editAppCreateInfo(body = {
				team_name,
				app_alias,
				service_cname,
				image,
				cmd,
				git_url,
				min_memory,
				extend_method,
				user_name,
				password
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/check_update`, {
								method: 'put',
								data: body
				});
}

/*
	删除应用
	is_force:	true直接删除，false进入回收站
	未创建成功的直接删除、 已经创建的进入回收站
*/
export async function deleteApp(body = {
				team_name,
				app_alias,
				is_force
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/delete`, {
								method: 'delete',
								data: {
												is_force: body.is_force === void 0
																? false
																: true
								}
				});
}

/*
	查询应用的性能分析插件
*/
export async function getAnalyzePlugins(body = {
				team_name,
				app_alias
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/analyze_plugins`, {method: 'get'});
}

/*
	获取应用的插件信息, 包括已安装的和未安装的
*/
export async function getPlugins(body = {
				team_name,
				app_alias,
				category
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/pluginlist`, {
								method: 'get',
								params: {
												category: body.category
								}
				});
}

/*
	开通插件
*/
export async function installPlugin(body = {
				team_name,
				app_alias,
				plugin_id,
				build_version
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/plugins/${body.plugin_id}/install`, {
								method: 'post',
								data: {
												build_version: body.build_version
								}
				});
}

/*
	卸载插件
*/
export async function unInstallPlugin(body = {
				team_name,
				app_alias,
				plugin_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/plugins/${body.plugin_id}/install`, {method: 'delete'});
}

/*
  启用插件
*/
export async function startPlugin(body = {
				team_name,
				app_alias,
				plugin_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/plugins/${body.plugin_id}/open`, {
								method: 'put',
								data: {
												is_switch: true
								}
				});
}

/*
  停用插件
*/
export async function stopPlugin(body = {
				team_name,
				app_alias,
				plugin_id
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/plugins/${body.plugin_id}/open`, {
								method: 'put',
								data: {
												is_switch: false
								}
				});
}

/*
   获取插件的配置信息
*/
export async function getPluginConfigs(body = {
				team_name,
				app_alias,
				plugin_id,
				build_version
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/plugins/${body.plugin_id}/configs`, {
								method: 'get',
								params: {
												build_version: body.build_version
								}
				});
}

/*
   更新插件的配置信息
*/
export async function editPluginConfigs(body = {
				team_name,
				app_alias,
				plugin_id,
				data
}) {
				return request(config.baseUrl + `/console/teams/${body.team_name}/apps/${body.app_alias}/plugins/${body.plugin_id}/configs`, {
								method: 'put',
								data: body.data
				});
}
