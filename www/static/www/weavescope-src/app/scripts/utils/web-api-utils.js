import debug from 'debug';
import reqwest from 'reqwest';
import defaults from 'lodash/defaults';
import { Map as makeMap, List } from 'immutable';

import { blurSearch, clearControlError, closeWebsocket, openWebsocket, receiveError,
  receiveApiDetails, receiveNodesDelta, receiveNodeDetails, receiveControlError,
  receiveControlNodeRemoved, receiveControlPipe, receiveControlPipeStatus,
  receiveControlSuccess, receiveTopologies, receiveNotFound,
  receiveNodesForTopology, receiveNodesMonitor } from '../actions/app-actions';

import { layersTopologyIdsSelector } from '../selectors/resource-view/layout';
import { API_INTERVAL, TOPOLOGY_INTERVAL } from '../constants/timer';

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
let topologyTimer = 0;
let apiDetailsTimer = 0;
let controlErrorTimer = 0;
let createWebsocketAt = 0;
let firstMessageOnWebsocketAt = 0;
let continuePolling = true;

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
  get:function getCookie(name)
  {
    var arr,reg=new RegExp("(^| )"+name+"=([^;]*)(;|$)");
    if(arr=document.cookie.match(reg))
    return unescape(arr[2]);
    else
    return null;
  },
  set: function(name,value, option={})
  {
    var Days = (option.days != void 0) ? option.days : 30;
    var exp = new Date();
    exp.setTime(exp.getTime() + Days*24*60*60*1000);
    var domain = option.domain ? ';domain='+option.domain : '';
    var path = (option.path != void 0) ? (";path="+option.path) : ";path=/";
    const cookie = name + "="+ escape (value) + ";expires=" + exp.toGMTString()+domain+path;
    document.cookie = cookie;
  },
  remove: function(name, option={})
  {
    var exp = new Date();
    exp.setTime(exp.getTime() - 1);
    var cval=this.get(name);
    var domain = option.domain ? ';domain='+option.domain : '';
    if(cval!=null)
    document.cookie= name + "="+cval+";expires="+exp.toGMTString()+domain;
  }
}

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
    config.headers = Object.assign({}, config.headers, { 'X-CSRF-Token': csrfToken});
  }
  config.headers = config.headers || {};

  var token = cookie.get('token');
  if(token){
     config.headers.Authorization = 'GRJWT '+ token;
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

  dispatch(()=>{

    return (dispatch, getState) => {
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
    };

  })


  return;
  // Used to resume polling when navigating between pages in Weave Cloud.
  continuePolling = initialPoll === true ? true : continuePolling;
  clearTimeout(topologyTimer);
  const optionsQuery = buildOptionsQuery(options);
  const url = `${getApiPath()}/api/topology?${optionsQuery}`;
  doRequest({
    url,
    success: (res) => {
      if (continuePolling) {
        dispatch(receiveTopologies(res));
        topologyTimer = setTimeout(() => {
          getTopologies(options, dispatch);
        }, TOPOLOGY_INTERVAL);
      }
    },
    error: (req) => {
      log(`Error in topology request: ${req.responseText}`);
      dispatch(receiveError(url));
      // Only retry in stand-alone mode
      if (continuePolling) {
        topologyTimer = setTimeout(() => {
          getTopologies(options, dispatch);
        }, TOPOLOGY_INTERVAL);
      }
    }
  });
}


 // 转换好雨云的数据到weaveScope的数据
function goodrainData2scopeData(data = {}) {


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
     id:'The Internet',
     service_alias:'internet', 
     service_cname:'The Internet', 
     label:'The Internet',
     shape:'cloud',
     stack:true,
     stackNum:1,
     linkable:true,
     rank:'internet',
     cur_status: 'running', 
     adjacency:[]
  }

  if(!keys.length){
      window.parent && window.parent.onNodesEmpty && window.parent.onNodesEmpty();
  }

  function getStackNum(item){
    if(item.cur_status !== 'running'){
      return 1;
    }
    item.node_num = item.node_num || 1;
    return item.node_num > 3 ? 3 : item.node_num;
  }

  keys.forEach((k) => {
    if (Object.prototype.hasOwnProperty.call(data.json_data, k)) {
      node = {};
      item = data.json_data[k];
      node.cur_status = item.cur_status;
      node.service_cname = item.service_cname;
      node.service_id = item.service_id;
      node.service_alias = item.service_alias;
      node.id = k;
      node.label = item.service_cname;
      node.lineTip = item.lineTip;
      node.labelMinor = '';
      //根据状态改变颜色用
      node.rank = node.cur_status;
      node.shape = 'hexagon';
      node.stack = true;
      node.stackNum = getStackNum(item);
      node.linkable = item.cur_status === 'running' ? 1 : 0;
      node.adjacency = data.json_svg[k] || [];
      add.push(node);
      if(item.is_internet){
        cloud.adjacency.push(k);
      }
    }
  });
  if (add.length && cloud.adjacency.length) {
    add.unshift(cloud);
  }
  scopeData.add = add;
  return scopeData;
}


// TODO: topologyUrl and options are always used for the current topology so they as arguments
// can be replaced by the `state` and then retrieved here internally from selectors.
export function getNodesDelta(topologyUrl, options, dispatch) {
if(location.href.indexOf('test-data')> -1){
    //调试数据
    var data = {
      "status":200,
      "json_svg":{
          "应用运行中":[
            '应用启动中,关闭中...',
            '监控数据'
          ],
          "应用异常、关闭等":[

          ],
          "应用未部署":[

          ]
      },
      "json_data":{
          "应用运行中":{
              "node_num":1,
              "service_id":"8993009fdb4406c4c9888f3f0cb89110",
              "cur_status":"running",
              "service_alias":"goodrain_labor",
              "service_cname":"应用运行中",
              "is_internet":true,
              
          },
          "应用异常、关闭等":{
              "node_num":1,
              "service_id":"dcbf56bb7a906ba1260ee7e9241f11d8",
              "cur_status":"closed",
              "service_alias":"discourse-redis",
              "service_cname":"应用异常、关闭等",
              "is_internet":true
          },
          "应用未部署":{
              "node_num":1,
              "service_id":"2ed5222913bb5bce882bc7395ec95fb9",
              "cur_status":"undeploy",
              "service_alias":"grc95fb9",
              "service_cname":"应用未部署",
              "is_internet":true,
              //"lineTip":"表示可以外网访问本应用"

          },
          "应用启动中,关闭中...":{
              "node_num":1,
              "service_id":"2ed5222913bb5bce882bc7395ec95fb9",
              "cur_status":"starting",
              "service_alias":"grc95fb9",
              "service_cname":"应用启动中,关闭中...",
              "is_internet":false,
              //"lineTip":"表示可以外网访问本应用"

          },
          "监控数据":{
              "node_num":1,
              "service_id":"2ed5222913bb5bce882bc7395ec95fb9",
              "cur_status":"running",
              "service_alias":"grc95fb9",
              "service_cname":"监控数据",
              "lineTip":"点表示应用的响应时间和吞吐率",
              "is_internet":false

          }
          
      }
    }
    //调试用数据
    const scopeData = goodrainData2scopeData(data);
    dispatch(receiveNodesDelta(scopeData));
    return;
}




 //如果父级window有挂载获取节点的方法， 则优先调用它
 if(window.parent && window.parent.weavescope){
    var config = window.parent.weavescope || {};
    config.getNodes && dispatch(receiveNodesDelta(config.getNodes()));
    return false;
 }else {
    var windowParent = window.parent;
    const url = (windowParent && windowParent.iframeGetNodeUrl && windowParent.iframeGetNodeUrl()) || '';
    doRequest({
      url : url,
      success: (res) => {
        if (res.code === 200) {
          const scopeData = goodrainData2scopeData(res.data.bean);
          dispatch(receiveNodesDelta(scopeData));
        }
      },
      error: () => {
        dispatch(receiveError(url));
      }
    });
 }


  const optionsQuery = buildOptionsQuery(options);
  // Only recreate websocket if url changed or if forced (weave cloud instance reload);
  // Check for truthy options and that options have changed.
  const isNewOptions = currentOptions && currentOptions !== optionsQuery;
  const isNewUrl = topologyUrl !== currentUrl || isNewOptions;
  // `topologyUrl` can be undefined initially, so only create a socket if it is truthy
  // and no socket exists, or if we get a new url.
  if ((topologyUrl && !socket) || (topologyUrl && isNewUrl)) {
    //createWebsocket(topologyUrl, optionsQuery, dispatch);
    currentUrl = topologyUrl;
    currentOptions = optionsQuery;
  }

  getNodeMonitorData(dispatch);

  setTimeout(function(){
    getNodesDelta(topologyUrl, options, dispatch)
  }, 5000)
}

export function getNodeMonitorData(dispatch){
  var windowParent = window.parent;
  var getDataFn = windowParent.iframeGetMonitor && windowParent.iframeGetMonitor;
  if(getDataFn){
       getDataFn(function(data){
          dispatch(receiveNodesMonitor(data.list));
       })
       
  }
 
}

export function getNodeDetails(topologyUrlsById, currentTopologyId, options, nodeMap, dispatch, serviceAlias) {
  // get details for all opened nodes

  var windowParent = window.parent;
  const obj = nodeMap.last();
  const tenantName = windowParent.iframeGetTenantName && windowParent.iframeGetTenantName();
  const region  = windowParent.iframeGetRegion && windowParent.iframeGetRegion();
  const groupId = windowParent.iframeGetGroupId && windowParent.iframeGetGroupId();
  if (obj && serviceAlias && tenantName && groupId) {
    const topologyUrl = topologyUrlsById.get(obj.topologyId);
    // let urlComponents = [getApiPath(), topologyUrl, '/', encodeURIComponent(obj.id)];
    // if (currentTopologyId === obj.topologyId) {
    //   // Only forward filters for nodes in the current topology
    //   const optionsQuery = buildOptionsQuery(options);
    //   urlComponents = urlComponents.concat(['?', optionsQuery]);
    // }
    // const url = urlComponents.join('');
    let url = '';

    if( obj.id === 'The Internet' ){
      url = '/console/teams/'+tenantName+'/'+groupId+'/outer-service?region='+region+'&_='+new Date().getTime();
    }else {
      url = '/console/teams/'+tenantName+'/topological/services/'+serviceAlias+'?region='+region+'&_='+new Date().getTime();
    }


    //调试用数据
    // var res = {"service_cname": "dev-goodrain-app", "total_memory": 128, "service_id": "c234ddbcecb76686c6ad1bc521bae7ee", "deploy_version": "20170704174434", "replicas": 1, "service_alias": "dev-goodrain-app", "cur_status": "running", 
    // "port_list": {"5000": {"is_outer_service": true, "is_inner_service": false, "service_id": "c234ddbcecb76686c6ad1bc521bae7ee", "port_alias": "APPLICATION", "container_port": 5000, "mapping_port": 0, "protocol": "http", "tenant_id": "b7584c080ad24fafaa812a7739174b50", "outer_url": "dev-goodrain-app.goodrain.ali-sh.goodrain.net:10080", "ID": 9436}}, 
    // "relation_list": {
    //   "36fbdf6b3b6dfaef716d04f4bfe06363": [{"mapping_port": 9204, "service_cname": "\u65e5\u5fd7\u5206\u67902", "service_alias": "bbb"}, {"mapping_port": 9304, "service_cname": "\u65e5\u5fd7\u5206\u67902", "service_alias": "gre06363"}], "e1a0c13176acf2b1374370bfc6c5d2e8": [{"mapping_port": 3307, "service_cname": "user_mysql", "service_alias": "bbb"}], "689a72457cecfa981e89f08aa4b3b277": [{"mapping_port": 5004, "service_cname": "zyq-debug", "service_alias": "zyq-debug"}], "90dfd8b86e2c7c94b4432abcf4dc0e3c": [{"mapping_port": 11212, "service_cname": "user_cache", "service_alias": "bbb"}], "dcbf56bb7a906ba1260ee7e9241f11d8": [{"mapping_port": 6383, "service_cname": "discourse-redis", "service_alias": "bbb"}]}, "container_cpu": 40, "tenant_id": "b7584c080ad24fafaa812a7739174b50", "pod_list": [{"pod_ip": "192.168.0.103", "phase": "Running", "pod_name": "345528949c9a806a5b41b02929186814-a0000", "node_name": "10.0.4.17"}], "container_memory": 256, "service_region": "ali-sh", "status": 200}
    // res.id = obj.id;

    // dispatch(receiveNodeDetails(res));
    // return;

    doRequest({
      url,
      success: (res) => {
        // make sure node is still selected
        // if (nodeMap.has(res.node.id)) {
        //   dispatch(receiveNodeDetails(res.node));
        // }

        res = res || {};
        
        res.rank = res.cur_status;
        if(obj.id === 'The Internet'){
          res.cur_status = 'running';
        }
        res = res || {};
        var data = res.data || {};
        var bean = data.bean || {};
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
            {id: res.resize_tty_control, probeId: control.probeId, nodeId: control.nodeId};
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
    data: JSON.stringify({pipeID: pipeId, width: cols.toString(), height: rows.toString()}),
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
