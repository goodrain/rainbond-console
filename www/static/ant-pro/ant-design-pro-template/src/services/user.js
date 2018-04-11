import request from '../utils/request';
import config from '../config/config';


export async function getTeamByName(body={team_name}){
  return request(config.baseUrl + `/console/teams/${body.team_name}/detail`,{
    method: 'get',
    showMessage: false
  });
}

export async function query() {
  return request('/api/users');
}

export async function queryCurrent() {
  return request('/api/currentUser');
}

/*登录*/
export async function login(body = {
  nick_name,
  password
}) {
  return request(config.baseUrl + '/console/users/login', {
    method: 'post',
    data: body,
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    transformRequest: [function (data) {
        let ret = ''
        for (let it in data) {
          ret += encodeURIComponent(it) + '=' + encodeURIComponent(data[it]) + '&'
        }
        return ret
      }
    ]
  });
}

/*退出登录*/
export async function logout() {
  return request(config.baseUrl + '/console/users/logout', {method: 'get'});
}

/*注册*/
export async function register(body = {
  user_name,
  email,
  password,
  password_repeat,
  captcha_code
}) {
  return request(config.baseUrl + '/console/users/register', {
    method: 'post',
    data: body,
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    transformRequest: [function (data) {
        let ret = ''
        for (let it in data) {
          ret += encodeURIComponent(it) + '=' + encodeURIComponent(data[it]) + '&'
        }
        return ret
      }
    ]
  });
}

/* 发送找回密码邮件 */
export async function send_backpassword_email(body = {
  email
}) {
  return request(config.baseUrl + '/console/users/send_reset_email', {
    method: 'post',
    data: body
  });
}

/*重置密码*/
export async function reset_password(body = {
  password,
  password_repeat
}) {
  return request(config.baseUrl + '/console/users/begin_password_reset', {
    method: 'post',
    data: body
  });
}

/*修改密码*/
export async function changePass(body = {
  password,
  new_password,
  new_password2
}) {
  return request(config.baseUrl + '/console/users/changepwd', {
    method: 'post',
    data: body
  });
}

/*
	查看当前登录用户的详情
*/
export async function getDetail(handleError) {
  return request(config.baseUrl + '/console/users/details', {handleError: handleError})
}

/*
	模糊查询用户
*/
export async function search(body = {
  key
}) {

  return request(config.baseUrl + '/console/users/query', {
    method: 'get',
    params: {
      query_key: body.key
    }
  })
}

/*
	获取当前登录用户加入的所有团队
*/
export async function joinedTeams() {
  return request(config.baseUrl + '/console/users/teams/query', {method: 'get'})
}

/*
  创建在某团队上的gitlab账号
  在用户没有填写邮箱信息的时候需要先注册下
*/

export async function gitlabRegister(body = {
  email,
  password
}) {

  return request(config.baseUrl + '/console/gitlab/register', {
    method: 'post',
    data: {
      email: body.email,
      password: body.password
    }
  })
}

/*
  创建github项目
*/
export async function createGitlabProject(body = {
  team_name,
  project_name
}) {
  return request(config.baseUrl + '/console/teams/' + body.team_name + '/code_repo/gitlab', {
    method: 'post',
    data: {
      project_name: body.project_name
    }
  })
}
