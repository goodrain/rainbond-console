/* eslint-disable no-use-before-define */
import debug from 'debug';
import { List, Map as makeMap } from 'immutable';
import defaults from 'lodash/defaults';
import reqwest from 'reqwest';
import {
  blurSearch, clearControlError, closeWebsocket, openWebsocket,
  receiveApiDetails, receiveControlError,
  receiveControlNodeRemoved, receiveControlPipe, receiveControlPipeStatus,
  receiveControlSuccess, receiveError,
  receiveNodeDetails, receiveNodesDelta,
  receiveNodesForTopology, receiveNodesMonitor, receiveNotFound
} from '../actions/app-actions';
import { API_INTERVAL } from '../constants/timer';
import { layersTopologyIdsSelector } from '../selectors/resource-view/layout';


const log = debug('scope:web-api-utils');

const reconnectTimerInterval = 5000;
const updateFrequency = '5s';
const FIRST_RENDER_TOO_LONG_THRESHOLD = 100; // ms
const csrfToken = (() => {
  // Check for token at window level or parent level (for iframe);
  /* eslint-disable no-underscore-dangle */
  const token = typeof window !== 'undefined'
    ? window.__WEAVEWORKS_CSRF_TOKEN || parent.__WEAVEWORKS_CSRF_TOKEN
    : null;
  /* eslint-enable no-underscore-dangle */
  if (!token || token === '$__CSRF_TOKEN_PLACEHOLDER__') {
    // Authfe did not replace the token in the static html.
    return null;
  }

  return token;
})();

let socket;
let reconnectTimer = 0;
let currentUrl = null;
let currentOptions = null;
const topologyTimer = 0;
let apiDetailsTimer = 0;
let controlErrorTimer = 0;
let createWebsocketAt = 0;
let firstMessageOnWebsocketAt = 0;
let continuePolling = true;
let newData = null;
let appName = null;
let newAppInfo = [];
let appServiceAlias = [];
const tiem = 0;
export function buildOptionsQuery(options) {
  if (options) {
    return options.map((value, param) => {
      if (List.isList(value)) {
        value = value.join(',');
      }
      return `${param}=${value}`;
    }).join('&');
  }
  return '';
}

export function basePath(urlPath) {
  //
  // "/scope/terminal.html" -> "/scope"
  // "/scope/" -> "/scope"
  // "/scope" -> "/scope"
  // "/" -> ""
  //
  const parts = urlPath.split('/');
  // if the last item has a "." in it, e.g. foo.html...
  if (parts[parts.length - 1].indexOf('.') !== -1) {
    return parts.slice(0, -1).join('/');
  }
  return parts.join('/').replace(/\/$/, '');
}

export function basePathSlash(urlPath) {
  //
  // "/scope/terminal.html" -> "/scope/"
  // "/scope/" -> "/scope/"
  // "/scope" -> "/scope/"
  // "/" -> "/"
  //
  return `${basePath(urlPath)}/`;
}

export function getApiPath(pathname = window.location.pathname) {
  if (process.env.SCOPE_API_PREFIX) {
    return basePath(`${process.env.SCOPE_API_PREFIX}${pathname}`);
  }

  return basePath(pathname);
}

export function getWebsocketUrl(host = window.location.host, pathname = window.location.pathname) {
  const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
  return `${wsProto}://${host}${process.env.SCOPE_API_PREFIX || ''}${basePath(pathname)}`;
}

function createWebsocket(topologyUrl, optionsQuery, dispatch) {
  if (socket) {
    socket.onclose = null;
    socket.onerror = null;
    socket.close();
    // onclose() is not called, but that's fine since we're opening a new one
    // right away
  }

  // profiling
  createWebsocketAt = new Date();
  firstMessageOnWebsocketAt = 0;

  socket = new WebSocket(`${getWebsocketUrl()}${topologyUrl}/ws?t=${updateFrequency}&${optionsQuery}`);

  socket.onopen = () => {
    dispatch(openWebsocket());
  };

  socket.onclose = () => {
    clearTimeout(reconnectTimer);
    log(`Closing websocket to ${topologyUrl}`, socket.readyState);
    socket = null;
    dispatch(closeWebsocket());

    if (continuePolling) {
      reconnectTimer = setTimeout(() => {
        createWebsocket(topologyUrl, optionsQuery, dispatch);
      }, reconnectTimerInterval);
    }
  };

  socket.onerror = () => {
    log(`Error in websocket to ${topologyUrl}`);
    dispatch(receiveError(currentUrl));
  };

  socket.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    dispatch(receiveNodesDelta(msg));

    // profiling (receiveNodesDelta triggers synchronous render)
    if (!firstMessageOnWebsocketAt) {
      firstMessageOnWebsocketAt = new Date();
      const timeToFirstMessage = firstMessageOnWebsocketAt - createWebsocketAt;
      if (timeToFirstMessage > FIRST_RENDER_TOO_LONG_THRESHOLD) {
        log('Time (ms) to first nodes render after websocket was created',
          firstMessageOnWebsocketAt - createWebsocketAt);
      }
    }
  };
}

const cookie = {
  get: function getCookie(name) {
    let arr,
      reg = new RegExp(`(^| )${name}=([^;]*)(;|$)`);
    if (arr = document.cookie.match(reg)) { return unescape(arr[2]); }
    return null;
  },
  set(name, value, option = {}) {
    const Days = (option.days != void 0) ? option.days : 30;
    const exp = new Date();
    exp.setTime(exp.getTime() + Days * 24 * 60 * 60 * 1000);
    const domain = option.domain ? `;domain=${option.domain}` : '';
    const path = (option.path != void 0) ? (`;path=${option.path}`) : ';path=/';
    const cookie = `${name}=${escape(value)};expires=${exp.toGMTString()}${domain}${path}`;
    document.cookie = cookie;
  },
  remove(name, option = {}) {
    const exp = new Date();
    exp.setTime(exp.getTime() - 1);
    const cval = this.get(name);
    const domain = option.domain ? `;domain=${option.domain}` : '';
    if (cval != null) { document.cookie = `${name}=${cval};expires=${exp.toGMTString()}${domain}`; }
  }
};

/**
  * XHR wrapper. Applies a CSRF token (if it exists) and content-type to all requests.
  * Any opts that get passed in will override the defaults.
  */
function doRequest(opts) {
  const config = defaults(opts, {
    contentType: 'application/json',
    type: 'json'
  });
  if (csrfToken) {
    config.headers = Object.assign({}, config.headers, { 'X-CSRF-Token': csrfToken });
  }
  config.headers = config.headers || {};

  const token = cookie.get('token');
  if (token) {
    config.headers.Authorization = `GRJWT ${token}`;
  }

  return reqwest(config);
}

/**
 * Does a one-time fetch of all the nodes for a custom list of topologies.
 */
function getNodesForTopologies(getState, dispatch, topologyIds, topologyOptions = makeMap()) {
  // fetch sequentially
  getState().get('topologyUrlsById')
    .filter((_, topologyId) => topologyIds.contains(topologyId))
    .reduce((sequence, topologyUrl, topologyId) => sequence.then(() => {
      const optionsQuery = buildOptionsQuery(topologyOptions.get(topologyId));
      return doRequest({ url: `${getApiPath()}${topologyUrl}?${optionsQuery}` });
    })
      .then(json => dispatch(receiveNodesForTopology(json.nodes, topologyId))),
      Promise.resolve());
}

/**
 * Gets nodes for all topologies (for search).
 */
export function getAllNodes(getState, dispatch) {
  const state = getState();
  const topologyOptions = state.get('topologyOptions');
  const topologyIds = state.get('topologyUrlsById').keySeq();
  getNodesForTopologies(getState, dispatch, topologyIds, topologyOptions);
}

/**
 * One-time update of all the nodes of topologies that appear in the current resource view.
 * TODO: Replace the one-time snapshot with periodic polling.
 */
export function getResourceViewNodesSnapshot(getState, dispatch) {
  const topologyIds = layersTopologyIdsSelector(getState());
  getNodesForTopologies(getState, dispatch, topologyIds);
}

export function getTopologies(options, dispatch, initialPoll) {
  dispatch(() => (dispatch, getState) => {
    const firstLoad = !getState().get('topologiesLoaded');
    // dispatch({
    //   type: ActionTypes.RECEIVE_TOPOLOGIES,
    //   topologies
    // });
    const state = getState();
    getNodesDelta(
      getCurrentTopologyUrl(state),
      activeTopologyOptionsSelector(state),
      dispatch
    );
    getNodeMonitorData(dispatch);
    getNodeDetails(
      state.get('topologyUrlsById'),
      state.get('currentTopologyId'),
      activeTopologyOptionsSelector(state),
      state.get('nodeDetails'),
      dispatch
    );
    // Populate search matches on first load
    if (firstLoad && state.get('searchQuery')) {
      dispatch(focusSearch());
    }
    // Fetch all the relevant nodes once on first load
    if (firstLoad && isResourceViewModeSelector(state)) {
      getResourceViewNodesSnapshot(getState, dispatch);
    }
  });
}


// 转换好雨云的数据到weaveScope的数据
function goodrainData2scopeData(data = {}) {
  const windowParent = window.parent;
  const groupId = windowParent.iframeGetGroupId && windowParent.iframeGetGroupId();
  const scopeData = {
    add: [],
    update: null,
    remove: null
  };
  const add = [];
  const keys = Object.keys(data.json_data);
  let node = {};
  let item = {};
  const cloud = {
    id: 'The Internet',
    app_id:groupId,
    service_alias: 'internet',
    service_cname: '网关',
    label: '网关',
    shape: 'cloud',
    stack: true,
    stackNum: 1,
    linkable: true,
    rank: 'internet',
    cur_status: 'running',
    adjacency: []
  };

  if (!keys.length) {
    window.parent && window.parent.onNodesEmpty && window.parent.onNodesEmpty();
  }

  function getStackNum(item) {
    if (item.cur_status !== 'running') {
      return 1;
    }
    item.node_num = item.node_num || 1;
    return item.node_num > 3 ? 3 : item.node_num;
  }

  keys.forEach((k) => {
    if (Object.prototype.hasOwnProperty.call(data.json_data, k)) {
      node = {};
      item = data.json_data[k];
      node.service_cname = item.service_cname;
      node.service_id = item.service_id;
      node.service_alias = item.service_alias;
      if(item.app_id == groupId && item.cur_status != 'third_party' && item.app_type !== 'helm'){
        node.label = item.service_cname;
        node.stackNum = 1;
        node.is_flag = false;
        node.cur_status = item.cur_status;
      }else if(item.app_id != groupId && item.cur_status != 'third_party' && item.app_type !== 'helm'){
        node.label = item.app_name;
        node.stackNum = 3;
        node.is_flag = true;
        node.cur_status = item.app_status
        node.component_status = item.cur_status
      }else if(item.app_type !== 'helm' && item.cur_status == 'third_party'){
        node.label = item.service_cname;
        node.stackNum = 1;
        node.is_flag = false;
        node.cur_status = item.cur_status;
      }else if(item.app_type === 'helm'){
        node.cur_status = 'helm';
        node.label = item.app_name;
        node.stackNum = 3;
        node.is_flag = true;
      }
      node.component_memory = item.component_memory
      node.id = item.service_id;
      node.app_id = item.app_id;
      node.lineTip = item.lineTip;
      node.labelMinor = '';
      // 根据状态改变颜色用
      node.rank = node.cur_status;
      node.shape = 'hexagon';
      node.stack = true;
      node.linkable = item.cur_status === 'running' ? 1 : 0;
      node.adjacency = data.json_svg[k] || [];
      add.push(node);
      if (item.is_internet) {
        cloud.adjacency.push(k);
      }
    }
  });
  if (add.length && cloud.adjacency.length) {
    add.unshift(cloud);
  }
  // let adds = {}
  // for(let i=0; i<add.length; i++){
  //     if(add[i].app_id != groupId){
  //       if(!adds[add[i].app_id]){
  //         adds[add[i].app_id]=[add[i]]
  //       }else{
  //         adds[add[i].app_id].push(add[i])
  //       }
  //     }
  // }
  let adds = []
  let newAdds = []
  for(let i = 0; i<add.length; i++){
      if(add[i].app_id != groupId && add[i].cur_status != 'third_party' && add[i].cur_status != 'helm'){
        newAdds.push(add[i])
      }else{
        adds.push(add[i])
      }
  }
  var map = newAdds.reduce((all, m) => {
    let list = all.get(m.app_id);
    if (!list) {
        list = [];
        all.set(m.app_id, list);
    }
    list.push(m);
    return all;
  }, new Map());;
  Array.from(map.entries())
    // 这里过滤掉 list 只有一个元素的，剩下的就是有重复的
    .forEach(([app_id, list]) => {
      if(list.length > 0){
        const values = list.map(m => m);
        adds.push(values[0])
        newAppInfo = list
      }else{
        adds.push(list[0])
      }
    });
  const scopeDataAdd = adds;
  scopeData.add = null;
  scopeData.remove = null;
  scopeData.update = null;
  if (scopeDataAdd.length === 0) {
    return scopeData;
  }
  if (newData === null) { scopeData.add = scopeDataAdd; }

  if (newData !== null && newData !== scopeDataAdd) {
    const newAdjacency = newData[0] && newData[0].adjacency;

    const scopeAdjacency = scopeDataAdd[0] && scopeDataAdd[0].adjacency;
    scopeData.remove = [];
    scopeData.update = [];

    // remove
    for (let i = 0; i < newAdjacency.length; i++) {
      if (scopeAdjacency.indexOf(newAdjacency[i]) < 0) {
        scopeData.remove.push(newAdjacency[i]);
      }
    }
    for (let i = 0; i < newData.length; i++) {
      for (let k = 0; k < scopeDataAdd.length; k++) {
        // add
        if ((newData.length !== scopeDataAdd.length) || scopeData.remove.length > 0) {
          scopeData.add = scopeDataAdd;
        }
        // update
        if ((newData[i].adjacency !== scopeDataAdd[k].adjacency) || (newData[i].cur_status !== scopeDataAdd[k].cur_status)) {
          scopeData.update = scopeDataAdd;
        }
      }
    }
  }

  newData = scopeData.add == null ? newData : scopeData.add;
  scopeData.remove = scopeData.remove !== null && scopeData.remove.length > 0 ? scopeData.remove : null;
  scopeData.update = scopeData.update !== null && scopeData.update.length > 0 ? scopeData.update : null;

  return scopeData;
}

// TODO: topologyUrl and options are always used for the current topology so they as arguments
// can be replaced by the `state` and then retrieved here internally from selectors.
export function getNodesDelta(topologyUrl, options, dispatch) {
  // 如果父级window有挂载获取节点的方法， 则优先调用它
  if (window.parent && window.parent.weavescope) {
    const config = window.parent.weavescope || {};
    config.getNodes && dispatch(receiveNodesDelta(config.getNodes()));
    return false;
  }
  // tiem++
  const windowParent = window.parent;
  const url = (windowParent && windowParent.iframeGetNodeUrl && windowParent.iframeGetNodeUrl()) || '';
  // const url = 'https://goodrain.goodrain.com/console/teams/64q1jlfb/regions/rainbond/topological?group_id=644';
  doRequest({
    url,
    success: (res) => {
      if (res.code === 200) {
        const scopeData = goodrainData2scopeData(res.data.bean);
        dispatch(receiveNodesDelta(scopeData));
        
      }
      setTimeout(() => {
        getNodesDelta(topologyUrl, options, dispatch);
      }, 5000);
    },
    error: () => {
      dispatch(receiveError(url));
      setTimeout(() => {
        getNodesDelta(topologyUrl, options, dispatch);
      }, 5000);
    }
  });


  const optionsQuery = buildOptionsQuery(options);
  // Only recreate websocket if url changed or if forced (weave cloud instance reload);
  // Check for truthy options and that options have changed.
  const isNewOptions = currentOptions && currentOptions !== optionsQuery;
  const isNewUrl = topologyUrl !== currentUrl || isNewOptions;
  // `topologyUrl` can be undefined initially, so only create a socket if it is truthy
  // and no socket exists, or if we get a new url.
  if ((topologyUrl && !socket) || (topologyUrl && isNewUrl)) {
    // createWebsocket(topologyUrl, optionsQuery, dispatch);
    currentUrl = topologyUrl;
    currentOptions = optionsQuery;
  }
}

export function getNodeMonitorData(dispatch) {
  const windowParent = window.parent;
  const getDataFn = windowParent.iframeGetMonitor;
  if (getDataFn) {
    getDataFn((data) => {
      dispatch(receiveNodesMonitor(data.list));
      setTimeout(() => {
        getNodeMonitorData(dispatch);
      }, 10000);
    }, (err) => {
      console.log(err);
    });
  }
}


export function getNodeDetails(topologyUrlsById, currentTopologyId, options, nodeMap, dispatch, serviceAlias) {
  // get details for all opened nodes

  const windowParent = window.parent;
  const obj = nodeMap.last();
  const tenantName = windowParent.iframeGetTenantName && windowParent.iframeGetTenantName();
  const region = windowParent.iframeGetRegion && windowParent.iframeGetRegion();
  const groupId = windowParent.iframeGetGroupId && windowParent.iframeGetGroupId();
  if (obj && serviceAlias && tenantName && groupId) {
    const topologyUrl = topologyUrlsById.get(obj.topologyId);
    let url = '';
    if (obj.id === 'The Internet') {
      url = `/console/teams/${tenantName}/${groupId}/outer-service?region=${region}&_=${new Date().getTime()}`;
    } else {
      url = `/console/teams/${tenantName}/topological/services/${serviceAlias}?region=${region}&_=${new Date().getTime()}`;
    }
    doRequest({
      url,
      success: (res) => {
        res = res || {};

        res.rank = res.cur_status;
        if (obj.id === 'The Internet') {
          res.cur_status = 'running';
        }
        res = res || {};
        const data = res.data || {};
        const bean = data.bean || {};
        bean.id = obj.id;
        dispatch(receiveNodeDetails(bean));
      },
      error: (err) => {
        log(`Error in node details request: ${err.responseText}`);
        // dont treat missing node as error
        if (err.status === 404) {
          dispatch(receiveNotFound(obj.id));
        } else {
          dispatch(receiveError(topologyUrl));
        }
      }
    });
  } else if (obj) {
    log('No details or url found for ', obj);
  }
}
//获取组件磁盘信息
export function Disklist(topologyUrlsById, currentTopologyId, options, nodeMap, dispatch, serviceAlias) {
  const windowParent = window.parent;
  const obj = nodeMap.last();
  const tenantName = windowParent.iframeGetTenantName && windowParent.iframeGetTenantName();
  const region = windowParent.iframeGetRegion && windowParent.iframeGetRegion();
  const groupId = windowParent.iframeGetGroupId && windowParent.iframeGetGroupId();
  let url = '';
  if (serviceAlias && tenantName) {
    const topologyUrl = topologyUrlsById.get(obj.topologyId);
    url = `/console/teams/${tenantName}/apps/${serviceAlias}/resource?region=${region}&_=${new Date().getTime()}`;

    doRequest({
      url,
      success: (res) => {
        res = res || {};

        res.rank = res.cur_status;
        if (obj.id === 'The Internet') {
          res.cur_status = 'running';
        }
        res = res || {};
        const data = res.data.bean || {};
        dispatch({
          type: "DISK_DETAIL",
          data
        });
      },
      error: (err) => {
        log(`Error in node details request: ${err.responseText}`);
      }
    });
  }
}
// 获取运行实例
export function GetPods(topologyUrlsById, currentTopologyId, options, nodeMap, dispatch, serviceAlias) {
  const windowParent = window.parent;
  const obj = nodeMap.last();
  const tenantName = windowParent.iframeGetTenantName && windowParent.iframeGetTenantName();
  const region = windowParent.iframeGetRegion && windowParent.iframeGetRegion();
  const groupId = windowParent.iframeGetGroupId && windowParent.iframeGetGroupId();
  let url = '';
  if (serviceAlias && tenantName) {
    const topologyUrl = topologyUrlsById.get(obj.topologyId);
    url = `/console/teams/${tenantName}/apps/${serviceAlias}/pods?region=${region}&_=${new Date().getTime()}`;

    doRequest({
      url,
      success: (res) => {
        res = res || {};

        res.rank = res.cur_status;
        if (obj.id === 'The Internet') {
          res.cur_status = 'running';
        }
        res = res || {};
        const data = res.data.list.new_pods || [];
        dispatch({
          type: "GET_PODS",
          data
        });
      },
      error: (err) => {
        log(`Error in node details request: ${err.responseText}`);
      }
    });
  }
}
//获取组件访问信息
export function Visitinfo(topologyUrlsById, currentTopologyId, options, nodeMap, dispatch, serviceAlias) {
  const windowParent = window.parent;
  const obj = nodeMap.last();
  const tenantName = windowParent.iframeGetTenantName && windowParent.iframeGetTenantName();
  const region = windowParent.iframeGetRegion && windowParent.iframeGetRegion();
  const groupId = windowParent.iframeGetGroupId && windowParent.iframeGetGroupId();
  let url = '';
  if (serviceAlias && tenantName) {
    const topologyUrl = topologyUrlsById.get(obj.topologyId);
    url = `/console/teams/${tenantName}/apps/${serviceAlias}/visit?region=${region}&_=${new Date().getTime()}`;

    doRequest({
      url,
      success: (res) => {
        res = res || {};

        res.rank = res.cur_status;
        if (obj.id === 'The Internet') {
          res.cur_status = 'running';
        }
        res = res || {};
        const data = res.data.bean.access_info[0] || {};
        dispatch({
          type: "VISIT_INFO",
          data
        });
      },
      error: (err) => {
        log(`Error in node details request: ${err.responseText}`);
      }
    });
  }
}
export function visitInfoParams( appNodes, nodeId ){
  return new Promise((resolve, reject)=>{
    const windowParent = window.parent;
    const VisitParams = windowParent.iframeGetNodeVistitUrl && windowParent.iframeGetNodeVistitUrl()
    const appnodes = appNodes._list._tail.array
    for(let i=0; i<appnodes.length; i++){
      if(nodeId === appnodes[i][0].id ){
        var app_ID = appnodes[i][0].app_id
      }
    }
    let url = ''
    if(app_ID){
      url = `${VisitParams}?group_id=${app_ID}`;
  
      doRequest({
        url,
        success: (res) => {
          if (res && res.code === 200) {
            const data = res.data.bean;
            if (JSON.stringify(data) === '{}') {
              return;
            }
            const serviceIds = [];
            const service_alias = [];
            const { json_data } = data;
            Object.keys(json_data).map(key => {
              serviceIds.push(key);
              if (
                json_data[key].cur_status == 'running' &&
                json_data[key].is_internet == true
              ) {
                service_alias.push(json_data[key].service_alias);
              }
            });
            resolve(service_alias)
          }
        },
        error: (err) => {
          log(`Error in node details request: ${err.responseText}`);
        }
      });
    }
  })
}
//获取应用访问信息
export async function appVisitInfo(topologyUrlsById, currentTopologyId, options, nodeMap, dispatch, serviceAlias, appNodes, nodeId) {
  const visitinfoParams = await visitInfoParams(appNodes,nodeId)
  const windowParent = window.parent;
  const obj = nodeMap.last();
  const tenantName = windowParent.iframeGetTenantName && windowParent.iframeGetTenantName();
  const region = windowParent.iframeGetRegion && windowParent.iframeGetRegion();
  const groupId = windowParent.iframeGetGroupId && windowParent.iframeGetGroupId();
  let url = '';
  const service_alias = [...new Set(visitinfoParams)].join('-');
  if (tenantName) {
    url = `/console/teams/${tenantName}/group/service/visit?service_alias=${service_alias}`;

    doRequest({
      url,
      success: (res) => {
        res = res || {};

        res.rank = res.cur_status;
        res = res || {};
        const data = res.data.list || [];
        dispatch({
          type:"APP_VISIT_INFO",
          data
        });
      },
      error: (err) => {
        log(`Error in node details request: ${err.responseText}`);
      }
    });
  }
}
//应用下面的组件数量
export function appModuleInfo(topologyUrlsById, currentTopologyId, options, nodeMap, dispatch,serviceAlias,appNodes,nodeId) {
  const windowParent = window.parent;
  const obj = nodeMap.last();
  const tenantName = windowParent.iframeGetTenantName && windowParent.iframeGetTenantName();
  const region = windowParent.iframeGetRegion && windowParent.iframeGetRegion();
  const groupId = windowParent.iframeGetGroupId && windowParent.iframeGetGroupId();
  const appnodes = appNodes._list._tail.array
    for(let i=0; i<appnodes.length; i++){
      if(nodeId === appnodes[i][0].id ){
        var app_Id = appnodes[i][0].app_id
      }
    }
  let url = '';
  if (tenantName && groupId) {
    url = `/console/teams/${tenantName}/groups/${app_Id}?region=${region}&_=${new Date().getTime()}`;

    doRequest({
      url,
      success: (res) => {
        res = res || {};

        res.rank = res.cur_status;
        res = res || {};
        const data = res.data.bean || {};
        dispatch({
          type:"APP_MODULE_INFO",
          data
        });
      },
      error: (err) => {
        log(`Error in node details request: ${err.responseText}`);
      }
    });
  }
}
//应用名称信息
export function appNameInfo(topologyUrlsById, currentTopologyId, options, nodeMap, dispatch,serviceAlias) {
  if(newAppInfo.length > 0){
    const data = newAppInfo
    dispatch({
      type: "NEW_APP_INFO",
      data
    });
  }
  
//   const windowParent = window.parent;
//   const obj = nodeMap.last();
//   const tenantName = windowParent.iframeGetTenantName && windowParent.iframeGetTenantName();
//   const region = windowParent.iframeGetRegion && windowParent.iframeGetRegion();
//   const groupId = windowParent.iframeGetGroupId && windowParent.iframeGetGroupId();
//   let url = '';
//   if (tenantName && groupId) {
//     url = `/console/teams/${tenantName}/groups/${groupId}?region=${region}&_=${new Date().getTime()}`;

//     doRequest({
//       url,
//       success: (res) => {
//         appName = res.data.bean.app_name
//       },
//       error: (err) => {
//         log(`Error in node details request: ${err.responseText}`);
//       }
//     });
//   }
}
//应用下的基本信息
export function appInfo(topologyUrlsById, currentTopologyId, options, nodeMap, dispatch, serviceAlias,appNodes,nodeId) {
  const windowParent = window.parent;
  const obj = nodeMap.last();
  const tenantName = windowParent.iframeGetTenantName && windowParent.iframeGetTenantName();
  const region = windowParent.iframeGetRegion && windowParent.iframeGetRegion();
  const appnodes = appNodes._list._tail.array
    for(let i=0; i<appnodes.length; i++){
      if(nodeId === appnodes[i][0].id ){
        var appId = appnodes[i][0].app_id
      }
    }
  let url = '';
  if (tenantName) {
    const topologyUrl = topologyUrlsById.get(obj.topologyId);
    url = `/console/teams/${tenantName}/groups/${appId}/status?region=${region}&_=${new Date().getTime()}`;

    doRequest({
      url,
      success: (res) => {
        res = res || {};

        res.rank = res.cur_status;
        res = res || {};
        const data = res.data.list || {};
        dispatch({
          type:"APP_INFO",
          data
        });
      },
      error: (err) => {
        log(`Error in node details request: ${err.responseText}`);
      }
    });
  }
}
// 获取pod_name值
export function Podname(serviceAlias) {

  return new Promise((resolve, reject) => {
    const windowParent = window.parent;
    const tenantName = windowParent.iframeGetTenantName && windowParent.iframeGetTenantName();
    const region = windowParent.iframeGetRegion && windowParent.iframeGetRegion();
    let url = '';
    if (serviceAlias) {
      url = `/console/teams/${tenantName}/apps/${serviceAlias}/pods?region=${region}&_=${new Date().getTime()}`;
      doRequest({
        url,
        success: (res) => {
          res = res || {};

          res.rank = res.cur_status;
          res = res || {};
          const data = res.data.list.new_pods[0].pod_name || [];
          resolve(data)
        },
        error: (err) => {
          log(`Error in node details request: ${err.responseText}`);
          // dont treat missing node as error
        }
      });
    }
  })
}
// 获取实例中的容器信息
export async function Dateils(topologyUrlsById, currentTopologyId, options, nodeMap, dispatch, serviceAlias) {
  const padname = await Podname(serviceAlias)
  const windowParent = window.parent;
  const obj = nodeMap.last();
  const tenantName = windowParent.iframeGetTenantName && windowParent.iframeGetTenantName();
  const region = windowParent.iframeGetRegion && windowParent.iframeGetRegion();
  const groupId = windowParent.iframeGetGroupId && windowParent.iframeGetGroupId();
  if (obj && serviceAlias && tenantName && groupId && padname) {
    const topologyUrl = topologyUrlsById.get(obj.topologyId);
    let url = '';
    if (obj.id === 'The Internet') {
      url = `/console/teams/${tenantName}/${groupId}/outer-service?region=${region}&_=${new Date().getTime()}`;
    } else {
      url = `/console/teams/${tenantName}/apps/${serviceAlias}/pods/${padname}/detail?region=${region}&_=${new Date().getTime()}`;
    }

    doRequest({
      url,
      success: (res) => {
        res = res || {};
        res.rank = res.cur_status;
        if (obj.id === 'The Internet') {
          res.cur_status = 'running';
        }
        res = res || {};
        const data = res.data || {};
        const bean = data.bean || {};
        bean.id = obj.id;
        dispatch({
          type: "INSTANCE",
          bean
        });
      },
      error: (err) => {
        log(`Error in node details request: ${err.responseText}`);
      }
    });
  } else if (obj) {
    log('No details or url found for ', obj);
  }
}
export function getApiDetails(dispatch) {
  clearTimeout(apiDetailsTimer);
  const url = `${getApiPath()}/api`;
  doRequest({
    url,
    success: (res) => {
      dispatch(receiveApiDetails(res));
      if (continuePolling) {
        apiDetailsTimer = setTimeout(() => {
          getApiDetails(dispatch);
        }, API_INTERVAL);
      }
    },
    error: (req) => {
      log(`Error in api details request: ${req.responseText}`);
      receiveError(url);
      if (continuePolling) {
        apiDetailsTimer = setTimeout(() => {
          getApiDetails(dispatch);
        }, API_INTERVAL / 2);
      }
    }
  });
}

export function doControlRequest(nodeId, control, dispatch) {
  clearTimeout(controlErrorTimer);
  const url = `${getApiPath()}/api/control/${encodeURIComponent(control.probeId)}/`
    + `${encodeURIComponent(control.nodeId)}/${control.id}`;
  doRequest({
    method: 'POST',
    url,
    success: (res) => {
      dispatch(receiveControlSuccess(nodeId));
      if (res) {
        if (res.pipe) {
          dispatch(blurSearch());
          const resizeTtyControl = res.resize_tty_control &&
            { id: res.resize_tty_control, probeId: control.probeId, nodeId: control.nodeId };
          dispatch(receiveControlPipe(
            res.pipe,
            nodeId,
            res.raw_tty,
            resizeTtyControl,
            control
          ));
        }
        if (res.removedNode) {
          dispatch(receiveControlNodeRemoved(nodeId));
        }
      }
    },
    error: (err) => {
      dispatch(receiveControlError(nodeId, err.response));
      controlErrorTimer = setTimeout(() => {
        dispatch(clearControlError(nodeId));
      }, 10000);
    }
  });
}


export function doResizeTty(pipeId, control, cols, rows) {
  const url = `${getApiPath()}/api/control/${encodeURIComponent(control.probeId)}/`
    + `${encodeURIComponent(control.nodeId)}/${control.id}`;

  return doRequest({
    method: 'POST',
    url,
    data: JSON.stringify({ pipeID: pipeId, width: cols.toString(), height: rows.toString() }),
  })
    .fail((err) => {
      log(`Error resizing pipe: ${err}`);
    });
}


export function deletePipe(pipeId, dispatch) {
  const url = `${getApiPath()}/api/pipe/${encodeURIComponent(pipeId)}`;
  doRequest({
    method: 'DELETE',
    url,
    success: () => {
      log('Closed the pipe!');
    },
    error: (err) => {
      log(`Error closing pipe:${err}`);
      dispatch(receiveError(url));
    }
  });
}


export function getPipeStatus(pipeId, dispatch) {
  const url = `${getApiPath()}/api/pipe/${encodeURIComponent(pipeId)}/check`;
  doRequest({
    method: 'GET',
    url,
    complete: (res) => {
      const status = {
        204: 'PIPE_ALIVE',
        404: 'PIPE_DELETED'
      }[res.status];

      if (!status) {
        log('Unexpected pipe status:', res.status);
        return;
      }

      dispatch(receiveControlPipeStatus(pipeId, status));
    }
  });
}

export function stopPolling() {
  clearTimeout(apiDetailsTimer);
  clearTimeout(topologyTimer);
  continuePolling = false;
}

export function teardownWebsockets() {
  clearTimeout(reconnectTimer);
  if (socket) {
    socket.onerror = null;
    socket.onclose = null;
    socket.onmessage = null;
    socket.onopen = null;
    socket.close();
    socket = null;
    currentOptions = null;
  }
}
