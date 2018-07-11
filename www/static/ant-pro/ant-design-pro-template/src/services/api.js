import {stringify} from 'qs';
import request from '../utils/request';
import config from '../config/config';

/*
  获取企业所有数据中心的每小时按需消费明细
 */
export async function getAllRegionFee(body={team_name, date}){
  return request(config.baseUrl + `/console/enterprise/team/${body.team_name}/all-region-fee`, {
    method: 'get',
    params: {
      date: body.date
    }
  });
}


/*
  获取企业充值记录
 */
export async function getPayHistory(body={team_name, start, end, page, page_size}){
  return request(config.baseUrl + `/console/enterprise/team/${body.team_name}/recharge-records`, {
    method: 'get',
    params: {
      start: body.start,
      end: body.end,
      page: body.page,
      page_size: body.page_size
    }
  });
}


/*
  初始化一个团队
*/
export async function InitTeam(body={team_alias, region_name}){
  return request(config.baseUrl + `/console/teams/init`, {
    method: 'post',
    data: body
  });
}

/* 获取某个数据中心的资源详情 */
export async function getRegionSource(body={team_name, region}){
  return request(config.baseUrl + `/console/enterprise/region/resource`, {
    method: 'get',
    params: {
      team_name: body.team_name,
      region: body.region
    }
  });
}



/* 获取企业详情 */
export async function getCompanyInfo(body={team_name}){
  return request(config.baseUrl + `/console/enterprise/account`, {
    method: 'get',
    params: {
      team_name: body.team_name
    }
  });
}

/* 获取某数据中心下某一天的资源费用数据 */
export async function getRegionOneDayMoney(body={team_name, date, region}){
  return request(config.baseUrl + `/console/enterprise/team/${body.team_name}/fee`, {
    method: 'get',
    params: {
      date: body.date,
      region: body.region
    }
  });
}


/* 认证企业 */
export async function authEnterprise(body = {
  team_name,
  enterprise_id,
  market_client_id,
  market_client_token
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/enterprise/active`, {
    method: 'post',
    data: {
      enterprise_id: body.enterprise_id,
      market_client_id: body.market_client_id,
      market_client_token: body.market_client_token
    }
  });
}

/* 卸载云市已下载的应用 */
export async function offlineMarketApp(body={app_id}){
   return request(config.baseUrl + `/console/app_market/manage`,{
     method: 'post',
     data: {
      app_id: body.app_id,
      action: 'offline'
     }
   })
}

/* 从云市同步应用的详细模板 */
export async function syncMarketAppDetail(body = {
  team_name,
  body
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/apps/template_details`, {
    method: 'post',
    data: body.body
  });
}

/* 查询所有同步的应用 */
export async function getMarketApp(body = {
  app_name,
  page,
  pageSize,
  is_complete
}) {
  return request(config.baseUrl + `/console/app_market/all`, {
    method: 'get',
    params: {
      app_name: body.app_name,
      page: body.page,
      page_size: body.pageSize,
      is_complete: body.is_complete
    }
  });
}

/*
  从好雨云市同步应用
*/
export async function syncMarketApp(body = {
  team_name
}) {
  return request(config.baseUrl + `/console/teams/${body.team_name}/apps/all_apps`, {method: 'get'});
}

/*
   获取云帮的公共信息、配置信息
*/
export function getRainbondInfo() {
  return request(config.baseUrl + '/console/config/info', {passAuthorization: false});
}

/*
   绑定github
*/
export async function bindGithub(body = {
  code,
  state
}) {
  return request(config.baseUrl + '/console/github/callback', {
    method: 'post',
    data: {
      code: body.code,
      state: body.state
    }
  });
}

/*
  获取github授权地址
*/

/*判断是否是公有云云帮*/
export async function isPubCloud() {
  return request(config.baseUrl + '/console/checksource');
}

//获取全部数据中心
export function getAllRegion() {
  return request(config.baseUrl + '/console/regions', {method: 'get'});
}

export async function queryProjectNotice() {
  return request('/api/project/notice');
}

export async function queryActivities() {
  return request('/api/activities');
}

export async function queryRule(params) {
  return request(`/api/rule?${stringify(params)}`);
}

export async function removeRule(params) {
  return request('/api/rule', {
    method: 'POST',
    body: {
      ...params,
      method: 'delete'
    }
  });
}

export async function addRule(params) {
  return request('/api/rule', {
    method: 'POST',
    body: {
      ...params,
      method: 'post'
    }
  });
}

export async function fakeSubmitForm(params) {
  return request('/api/forms', {
    method: 'POST',
    body: params
  });
}

export async function fakeChartData() {
  return request('/api/fake_chart_data');
}

export async function queryTags() {
  return request('/api/tags');
}

export async function queryBasicProfile() {
  return request('/api/profile/basic');
}

export async function queryAdvancedProfile() {
  return request('/api/profile/advanced');
}

export async function queryFakeList(params) {
  return request(`/api/fake_list?${stringify(params)}`);
}

export async function fakeAccountLogin(params) {
  return request('/api/login/account', {
    method: 'POST',
    body: params
  });
}

export async function fakeRegister(params) {
  return request('/api/register', {
    method: 'POST',
    body: params
  });
}

export async function queryNotices() {
  return request('/api/notices');
}


/* 查询用户站内信 */
export async function getuserMessage(body={team_name, page_num, page_size,msg_type,is_read}){
  return request(config.baseUrl + `/console/teams/${body.team_name}/message`, {
    method: 'get',
    params: {
      page_num: body.page_num,
      page_size: body.page_size,
      msg_type:body.msg_type,
      is_read:body.is_read
    }
  });
}

/* 消息标记为已读未读 */
export async function putMsgAction(body={team_name, msg_ids, action}){
  return request(config.baseUrl + `/console/teams/${body.team_name}/message`, {
    method: 'put',
    data: {
      action: body.action,
      msg_ids: body.msg_ids
    }
  });
}

/* 删除站内信 */
export async function deleteMsg(body={team_name, msg_ids}){
  return request(config.baseUrl + `/console/teams/${body.team_name}/message`, {
    method: 'delete',
    data: {
      msg_ids: body.msg_ids
    }
  });
}

/* 资源价格计算 */
export async function resPrice(body={team_name, region_name,memory,disk,rent_time}){
  return request(config.baseUrl + `/console/enterprise/regions/${body.region_name}/res-price`, {
    method: 'post',
    data: {
      team_name: body.team_name,
      region_name: body.region_name,
      memory: body.memory,
      disk: body.disk,
      rent_time: body.rent_time
    }
  });
}


/* 资源购买 */
export async function buyPurchase(body={team_name, region_name,memory,disk,rent_time}){
  return request(config.baseUrl + `/console/enterprise/regions/${body.region_name}/purchase`, {
    method: 'post',
    data: {
      team_name: body.team_name,
      region_name: body.region_name,
      memory: body.memory,
      disk: body.disk,
      rent_time: body.rent_time
    }
  });
}