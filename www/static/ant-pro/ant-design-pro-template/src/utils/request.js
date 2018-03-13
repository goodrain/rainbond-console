import axios from 'axios';
import {notification} from 'antd';
import {routerRedux} from 'dva/router';
import store from '../index';
import cookie from './cookie';

const codeMessage = {
    200: '服务器成功返回请求的数据',
    201: '新建或修改数据成功。',
    202: '一个请求已经进入后台排队（异步任务）',
    204: '删除数据成功。',
    400: '发出的请求有错误，服务器没有进行新建或修改数据,的操作。',
    401: '用户没有权限（令牌、用户名、密码错误）。',
    403: '用户得到授权，但是访问是被禁止的。',
    404: '发出的请求针对的是不存在的记录，服务器没有进行操作',
    406: '请求的格式不可得。',
    410: '请求的资源被永久删除，且不会再得到的。',
    422: '当创建一个对象时，发生一个验证错误。',
    500: '服务器发生错误，请检查服务器',
    502: '网关错误',
    503: '服务不可用，服务器暂时过载或维护',
    504: '网关超时'
};

function checkStatus(response) {
    if (response.status >= 200 && response.status < 300) {
        return response;
    }

    const errortext = codeMessage[response.status] || response.statusText;
    notification.error({message: `请求错误 ${response.status}: ${response.url}`, description: errortext});

    const error = new Error(errortext);
    error.name = response.status;
    error.response = response;

    throw error;
}

/**
 * Requests a URL, returning a promise.
 *
 * @param  {string} url       The URL we want to request
 * @param  {object} [options] The options we want to pass to "fetch"
 * @return {object}           An object containing either "data" or "err"
 */
export default function request(url, options) {
    const defaultOptions = {
        credentials: 'include'
    };
    const newOptions = {
        ...defaultOptions,
        ...options
    };
    if (newOptions.method === 'POST' || newOptions.method === 'PUT') {
        newOptions.headers = {
            Accept: 'application/json',
            'Content-Type': 'application/json; charset=utf-8',

            ...newOptions.headers
        };
        newOptions.body = JSON.stringify(newOptions.body);
    }

    if (newOptions.passAuthorization === void 0) {
        newOptions.passAuthorization = true;
    }

    const headers = newOptions.headers || {};

    newOptions.headers = {
        ...headers,

        // "Authorization": 'GRJWT '+ (cookie.get('token') ||
        // 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImxpY2hhbyIsImV4cCI6MTUx
        // ODY2MzYyNCwiZW1haWwiOiJsaWNAZ29vZHJhaW4uY29tIiwidXNlcl9pZCI6Nn0.N95RuiLn0nA8Tw
        // RR0TGh6luHnJ9A_IYJtGxHQdtc2jE'), "Authorization": 'GRJWT '+
        // (cookie.get('token'))
    };

    const token = cookie.get('token');
    if (token && newOptions.passAuthorization) {
        newOptions.headers.Authorization = `GRJWT ${token}`;
    }

    // newOptions.headers.Authorization = 'GRJWT '+
    // 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImxpY2hhbyIsImV4cCI6MTUx
    // ODY2MzYyNCwiZW1haWwiOiJsaWNAZ29vZHJhaW4uY29tIiwidXNlcl9pZCI6Nn0.N95RuiLn0nA8Tw
    // RR0TGh6luHnJ9A_IYJtGxHQdtc2jE';
    newOptions.url = url;
    // newOptions.withCredentials = true;
    axios.defaults.withCredentials = true;
    if (newOptions.params) {
        newOptions.params._ = Date.now();
    }

    newOptions.showMessage = newOptions.showMessage === void 0
        ? true
        : newOptions.showMessage;
    const showLoading = newOptions.showLoading === void 0
        ? true
        : newOptions.showLoading;

    let dispatch;
    if (store) {
        dispatch = store.dispatch;
        showLoading && dispatch && dispatch({type: 'global/showLoading'});
    }

    return axios(newOptions)
        .then(checkStatus)
        .then((response) => {
            showLoading && dispatch && dispatch({type: 'global/hiddenLoading'});

            if (newOptions.method === 'DELETE' || response.status === 204) {
                return response.text();
            }
            const res = response.data.data || {};
            res._code = response.status;

            return res;
        })
        .catch((error) => {
            if (showLoading) {
                dispatch && dispatch({type: 'global/hiddenLoading'});
            }

            if (error.response) {
                const response = error.response;
                // 请求已发出，但服务器响应的状态码不在 2xx 范围内

                const status = error.response.status;

                let resData = {};
                try {
                    resData = error.response.data;
                } catch (e) {}

                if (resData.code === 10405) {
                    cookie.remove('token');
                    cookie.remove('uid');
                    cookie.remove('username');
                    dispatch(routerRedux.push('/user/login'));
                    return;
                }

                // 服务不属于当前数据中心
                if (resData.code === 10404) {
                    cookie.remove('token');
                    dispatch(routerRedux.push('/user/login'));
                    return;
                }

                // 服务不属于当前团队
                if (resData.code === 10403) {
                    cookie.remove('token');
                    dispatch(routerRedux.push('/user/login'));
                    return;
                }

                if (newOptions.handleError) {
                    newOptions.handleError(response);
                    return;
                }

                const msg = resData.msg_show || resData.msg || resData.detail;
                if (msg && newOptions.showMessage === true) {
                    if (msg.indexOf('身份认证信息未提供') > -1) {
                        cookie.remove('token');
                        dispatch(routerRedux.push('/user/login'));
                        return;
                    }

                    notification.error({message: `请求错误 ${response.status}`, description: msg});
                }

                // if (status <= 504 && status >= 500) {
                // dispatch(routerRedux.push('/exception/500'));   return; } if (status >= 404
                // && status < 422) {   dispatch(routerRedux.push('/exception/404')); }
            } else {
                // Something happened in setting up the request that triggered an Error
                console.log('Error', error.message);
            }

            // return error
        });
}
