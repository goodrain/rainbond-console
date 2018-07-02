import request from '../utils/request';
import config from '../config/config';




/*
获取所有的权限
*/
export async function getAllPerms(body={}){
  return request(config.baseUrl + `console/teams/operate_options`,{
    method: 'get'
  })
}

/*
修改角色
 */
export async function editRole(body={team_name, role_id, role_name, options_ids}){
  return request(config.baseUrl + `console/teams/${body.team_name}/update_role_perms`,{
    method: 'post',
    data:{
      role_id: body.role_id,
      new_role_name: body.role_name,
      new_options_id_list: body.options_ids
    }
  })
}


/*
删除角色
 */
export async function removeRole(body={team_name, role_id}){
  return request(config.baseUrl + `console/teams/${body.team_name}/del-role`,{
    method: 'delete',
    data:{
      role_id: body.role_id
    }
  })
}


/*
创建角色
 */
export async function createRole(body={team_name, role_name, options_ids}){
  return request(config.baseUrl + `console/teams/${body.team_name}/add-role`,{
    method: 'post',
    data:{
      role_name: body.role_name,
      options_id_list: body.options_ids
    }
  })
}



/*
获取团队下所有角色
 */
export async function getRoles(body={team_name, page, page_size}){
  return request(config.baseUrl + `console/teams/${body.team_name}/role-list`,{
    method: 'get',
    params:{
      page: body.page,
      page_size: body.page_size
    }
  })
}



/*
	团队下用户的信息
*/
export async function userDetail(body = {
  team_name,
  user_name
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/${body.user_name}/details`, {method: 'get'});
}

/*
	移交团队管理权限
*/
export async function moveTeam(body = {
  team_name,
  user_name
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/pemtransfer`, {
    method: 'post',
    data: {
      user_name: body.user_name
    }
  });
}

/*
	获取团队所有的可选的权限
*/
export async function getTeamPermissions() {
  return request(config.baseUrl + '/console/teams/user/identity', {method: 'get'});
}

/*
	修改成员角色
*/
export async function editMember(body = {
  team_name,
  user_name,
  role_ids,
  user_name
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/${body.user_name}/mod-role`, {
    method: 'post',
    data: {
      role_ids: body.role_ids
    }
  });
}

/*
   新建团队
*/
export async function createTeam(body = {
  team_name,
  useable_regions: []
}) {
  return request(config.baseUrl + `/console/teams/add-teams`, {
    method: 'post',
    data: {
      team_alias: body.team_name,
      useable_regions: body
        .useable_regions
        .join(',')
    }
  });
}

/*
	获取团队下的所有成员
*/
export async function getMembers(body = {
  team_name,
  page,
  pageSize
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/users`, {
    method: 'get',
    params: {
      page: body.page,
      page_size: body.pageSize
    }
  });
}

/*
	添加成员
*/
export async function addMember(body = {
  team_name,
  user_ids,
  role_ids
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/add_team_user`, {
    method: 'post',
    data: {
      user_ids: body.user_ids,
      role_ids: body.role_ids
    }
  });
}

/*
    删除成员
*/
export async function removeMember(body = {
  team_name,
  user_ids
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/users/batch/delete`, {
    method: 'delete',
    data: {
      user_ids: body.user_ids
    }
  });
}

/*
	修改团队名称
*/
export async function editTeamName(body = {
  team_name,
  new_team_alias
}) {

  return request(config.baseUrl + `/console/teams/${body.team_name}/modifyname`, {
    method: 'post',
    data: {
      new_team_alias: body.new_team_alias
    }
  });
}

/*
	删除团队
*/
export async function deleteTeam(body = {
  team_name
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/delete`, {method: 'delete'});
}

/*
	获取团队下的数据中心
*/
export async function getRegions(body = {
  team_name
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/region/query`);
}

/*
   总览团队在某个数据中心下的信息
*/
export async function getTeamRegionOverview(body = {
  team_name,
  region_name
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/overview`, {showLoading: false});
}

/*
	获取团队在某个数据数据中心下的所有应用
*/
export async function getTeamRegionApps(body = {}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/overview/service/over`, {
    method: 'get',
    params: body,
    showLoading: false
  });
}

/*
   查询某个团队在某个数据中心下的所有应用状态
*/
export async function getTeamRegionAppsStatus(body = {
  team_name,
  region_name,
  service_ids
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/${body.region_name}/overview/services/status`, {
    method: 'post',
    data: {
      service_ids: body.service_ids
    }
  });
}

/*
	获取团队在某个数据中心下的所有应用组
*/
export async function getTeamRegionGroups(body = {
  team_name
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/overview/groups`);
}

/*
   获取团队下的证书
*/
export async function getCertificates(body = {
  team_name
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/certificates`);
}

/*
  添加证书
*/
export async function addCertificate(body = {
  team_name,
  alias,
  private_key,
  certificate
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/certificates`, {
    method: 'post',
    data: {
      alias: body.alias,
      private_key: body.private_key,
      certificate: body.certificate
    }
  });
}

/*
  获取团队下最新操作动态
*/
export async function getNewestEvent(body = {
  team_name,
  page,
  page_size
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/services/event`, {
    method: 'get',
    params: {
      team_name: body.team_name,
      page: 1,
      page_size: 6
    }
  });
}

/*
  获取团队未开通的数据中心列表
*/
export function unOpenRegion(body = {
  team_name
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/region/unopen`, {method: 'get'});
}

/* 开通数据中心 */
export function openRegion(body = {
  team_name,
  region_names
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/region`, {
    method: 'patch',
    data: {
      region_names: body.region_names
    }
  });
}

/*
  获取团队授权绑定的github信息, 如果未绑定这个接口会返回去绑定的地址
*/
export function getGithubInfo(body = {
  team_name
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/code_repo/github`, {
    method: 'get',
    data: {
      tenantName: body.team_name
    }
  });
}

/*
  获取团队授权绑定的gitlub信息
*/
export function getGitlabInfo(body = {
  team_name
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/code_repo/gitlab`, {
    method: 'get',
    data: {
      tenantName: body.team_name
    }
  });
}

/*
  获取数据中心的key
*/
export async function getRegionKey(body = {
  team_name,
  region_name
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/regions/${body.region_name}/publickey`, {method: 'get'});
}

/*
  退出团队
*/
export async function exitTeam(body = {
  team_name
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/exit`, {method: 'get'});
}
