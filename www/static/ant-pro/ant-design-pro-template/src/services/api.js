import { stringify } from 'qs';
import request from '../utils/request';
import config from '../config/config';


/*
   获取云帮的公共信息、配置信息
*/
export async function getRainbondInfo() {
  return request(config.baseUrl + '/console/config/info', {
     passAuthorization: false
  });
}

/*
   绑定github
*/
export async function bindGithub(body={code, state}) {
  return request(config.baseUrl + '/console/github/callback', {
     method: 'post',
     data:{
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
export function getAllRegion(){
   return request(config.baseUrl + '/console/regions', {
    method: 'get'
   });
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
      method: 'delete',
    },
  });
}

export async function addRule(params) {
  return request('/api/rule', {
    method: 'POST',
    body: {
      ...params,
      method: 'post',
    },
  });
}

export async function fakeSubmitForm(params) {
  return request('/api/forms', {
    method: 'POST',
    body: params,
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
    body: params,
  });
}

export async function fakeRegister(params) {
  return request('/api/register', {
    method: 'POST',
    body: params,
  });
}

export async function queryNotices() {
  return request('/api/notices');
}


