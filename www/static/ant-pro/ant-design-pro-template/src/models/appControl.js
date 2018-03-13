import {getGroupApps} from '../services/group';
import {
  getDetail,
  getPorts,
  deletePort,
  changePortProtocal,
  openPortOuter,
  closePortOuter,
  openPortInner,
  closePortInner,
  bindDomain,
  editPortAlias,
  unbindDomain,
  addPort,
  getInnerEnvs,
  addInnerEnvs,
  getOuterEnvs,
  addOuterEnvs,
  deleteEvns,
  editEvns,
  getRunningProbe,
  getStartProbe,
  addStartProbe,
  addRunningProbe,
  editStartProbe,
  editRunningProbe,
  getBaseInfo,
  deleteMnt,
  getVolumes,
  addVolume,
  deleteVolume,
  getAppRequestTime,
  getAppRequestTimeRange,
  getAppRequest,
  getAppRequestRange,
  getAppOnlineNumber,
  getAppOnlineNumberRange,
  getCodeBranch,
  setCodeBranch,
  getAppDisk,
  getAppMemory,
  getExtendInfo,
  getPods,
  getVisitInfo,
  managePods,
  getTags,
  deleteTag,
  addTags,
  editName,
  moveGroup,
  setMemberAction,
  getMembers,
  deleteMember,
  editMemberAction,
  getRuntimeInfo,
  editRuntimeInfo,
  editAppCreateInfo,
  deleteApp,
  getPlugins,
  installPlugin,
  unInstallPlugin,
  startPlugin,
  stopPlugin,
  getPluginConfigs,
  editPluginConfigs,
  getAnalyzePlugins
} from '../services/app';

import {getCertificates, addCertificate} from '../services/team';
import cookie from '../utils/cookie';

export default {
  namespace : 'appControl',
  state : {
    //标签信息
    tags: null,
    //应用的扩展信息
    extendInfo: null,
    //应用
    apps: [],
    //应用详情
    appDetail: {},
    baseInfo: {},
    //应用端口信息
    ports: [],
    //添加域名是所需要证书
    certificates: [],
    //应用的环境变量
    innerEnvs: [],
    //依赖里的环境变量
    outerEnvs: [],
    //某个依赖的应用的对外环境变量
    relationOuterEnvs: [],
    //启动时检测信息
    startProbe: {},
    //运行时检测信息
    runningProbe: {},
    //应用的代码分支
    branchs: [],
    //应用的持久化路径
    volumes: [],
    //应用当前时间在线人数
    onlineNumber: {},
    //应用一段时间内在线人数
    onlineNumberRange: {},
    //应用当前时间吞吐率
    appRequest: {},
    //应用一段内时间吞吐率
    appRequestRange: {},
    //应用当前时间响应时间
    requestTime: {},
    //应用一段时间内的响应时间
    requestTimeRange: {},
    //应用的分支
    codeBranch: [],
    //应用磁盘使用量
    appDisk: {},
    //应用内存使用量
    appMemory: {},
    //应用实例
    pods: [],
    //应用的访问信息
    visitInfo: null,
    //设置了权限的团队成员
    members: []
  },
  effects : {
    *getAnalyzePlugins({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(getAnalyzePlugins, payload);
      if (response) {
        callback && callback(response);
      }
    },
    *getPluginConfigs({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(getPluginConfigs, payload);
      if (response) {
        callback && callback(response);
      }
    },
    *editPluginConfigs({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(editPluginConfigs, payload);
      if (response) {
        callback && callback(response);
      }
    },
    *startPlugin({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(startPlugin, payload);
      if (response) {
        callback && callback(response);
      }
    },
    *stopPlugin({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(stopPlugin, payload);
      if (response) {
        callback && callback(response);
      }
    },
    *unInstallPlugin({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(unInstallPlugin, payload);
      if (response) {
        callback && callback(response);
      }
    },
    *installPlugin({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(installPlugin, payload);
      if (response) {
        callback && callback(response);
      }
    },
    *getPlugins({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(getPlugins, payload);
      if (response) {
        callback && callback(response);
      }
    },
    *editAppCreateInfo({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(editAppCreateInfo, payload);
      if (response) {
        callback && callback(response);
      }
    },
    *getRuntimeInfo({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(getRuntimeInfo, payload);
      if (response) {
        callback && callback(response);
      }
    },
    *editRuntimeInfo({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(editRuntimeInfo, payload);
      if (response) {
        callback && callback(response);
      }
    },
    *addTag({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(addTags, payload);
      if (response) {
        callback && callback();
      }
    },
    *deleteTag({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(deleteTag, payload);
      if (response) {
        callback && callback();
      }
    },
    *fetchTags({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(getTags, payload);
      if (response) {
        yield put({type: 'saveTags', payload: response.bean});
        callback && callback();
      }
    },
    *managePod({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(managePods, payload);
      if (response) {
        callback && callback();
      }
    },
    *fetchVisitInfo({
      payload
    }, {call, put}) {
      const response = yield call(getVisitInfo, payload);
      if (response) {
        yield put({type: 'saveVisitInfo', payload: response.bean});
      }
    },
    *fetchPods({
      payload
    }, {call, put}) {

      const response = yield call(getPods, payload);
      if (response) {
        yield put({type: 'savePods', payload: response.list});
      }
    },
    *fetchExtendInfo({
      payload,
      handleError
    }, {call, put}) {

      const response = yield call(getExtendInfo, payload, handleError);
      if (response) {
        yield put({type: 'saveExtendInfo', payload: response.bean});
      }
    },
    *editName({
      payload,
      callback
    }, {call, put}) {

      const response = yield call(editName, payload);
      if (response) {
        callback && callback();
      }

    },
    *fetchDetail({
      payload,
      callback,
      handleError
    }, {call, put}) {

      const response = yield call(getDetail, payload, handleError);
      if (response) {
        yield put({type: 'saveDetail', payload: response.bean});
        callback && callback(response.bean);
      }

    },
    *fetchApps({
      payload
    }, {call, put}) {
      const response = yield call(getGroupApps, payload);
      if (response) {
        yield put({type: 'saveApps', payload: response.list});
      }
    },
    *fetchPorts({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(getPorts, payload);
      if (response) {
        yield put({type: 'savePorts', payload: response.list});
        callback && callback(response);
      }
    },
    *deletePort({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(deletePort, payload);
      if (response) {
        callback && callback();
      }
    },
    *changeProtocol({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(changePortProtocal, payload);
      if (response) {
        callback && callback();
      }
    },
    *openPortOuter({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(openPortOuter, payload);
      if (response) {
        callback && callback();
      }
    },
    *closePortOuter({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(closePortOuter, payload);
      if (response) {
        callback && callback();
      }
    },
    *openPortInner({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(openPortInner, payload);
      if (response) {
        callback && callback();
      }
    },
    *closePortInner({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(closePortInner, payload);
      if (response) {
        callback && callback();
      }
    },
    *bindDomain({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(bindDomain, payload);
      if (response) {
        callback && callback();
      }
    },
    *unbindDomain({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(unbindDomain, payload);
      if (response) {
        callback && callback();
      }
    },
    *editPortAlias({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(editPortAlias, payload);
      if (response) {
        callback && callback();
      }
    },
    *addPort({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(addPort, payload);
      if (response) {
        callback && callback();
      }
    },
    *moveGroup({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(moveGroup, payload);
      if (response) {
        callback && callback();
      }
    },
    *fetchCertificates({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(getCertificates, payload);
      if (response) {

        yield put({type: 'saveCertificates', payload: response.list});
      }
    },
    *addCertificate({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(addCertificate, payload);
      if (response) {
        callback && callback();
      }
    },
    *fetchInnerEnvs({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(getInnerEnvs, payload);
      if (response) {
        yield put({type: 'saveInnerEnvs', payload: response.list});
        callback && callback(response);
      }
    },
    *addInnerEnvs({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(addInnerEnvs, payload);
      if (response) {
        callback && callback();
      }
    },
    *fetchOuterEnvs({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(getOuterEnvs, payload);
      if (response) {
        yield put({type: 'saveOuterEnvs', payload: response.list});
      }
    },
    *fetchRelationOuterEnvs({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(getOuterEnvs, payload);
      if (response) {
        yield put({type: 'saveRelationOuterEnvs', payload: response.list});
      }
    },
    *addOuterEnvs({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(addOuterEnvs, payload);
      if (response) {
        callback && callback();
      }
    },
    *deleteEnvs({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(deleteEvns, payload);
      if (response) {
        callback && callback();
      }
    },
    *editEvns({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(editEvns, payload);
      if (response) {
        callback && callback();
      }
    },
    *fetchStartProve({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(editEvns, payload);
      if (response) {
        callback && callback();
      }
    },
    *fetchRunningProbe({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(getRunningProbe, payload);
      if (response) {
        yield put({type: 'saveRunningProbe', payload: response.bean});
      }
    },
    *fetchStartProbe({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(getStartProbe, payload);
      if (response) {
        yield put({type: 'saveStartProbe', payload: response.bean});
      }
    },
    *addStartProbe({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(addStartProbe, payload);
      if (response) {
        callback && callback();
      }
    },
    *addRunProbe({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(addRunningProbe, payload);
      if (response) {
        callback && callback();
      }
    },
    *editStartProbe({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(editStartProbe, payload);
      if (response) {
        callback && callback();
      }
    },
    *editRunProbe({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(editRunningProbe, payload);
      if (response) {
        callback && callback();
      }
    },
    *fetchBaseInfo({
      payload,
      callback
    }, {call, put}) {

      const response = yield call(getBaseInfo, payload);
      if (response) {
        yield put({type: 'saveBaseInfo', payload: response.bean});
      }
    },
    *deleteMnt({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(deleteMnt, payload);
      if (response) {
        callback && callback();
      }
    },
    *fetchVolumes({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(getVolumes, payload);
      if (response) {
        yield put({
          type: 'saveVolumes',
          payload: response.list || []
        });
        callback && callback(response);
      }
    },
    *addVolume({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(addVolume, payload);
      if (response) {
        callback && callback();
      }
    },
    *deleteVolume({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(deleteVolume, payload);
      if (response) {
        callback && callback();
      }
    },
    //响应时间
    *fetchRequestTime({
      payload,
      callback,
      complete
    }, {call, put}) {
      const response = yield call(getAppRequestTime, payload);
      if (response) {
        yield put({type: 'saveRequestTime', payload: response.bean});
        callback && callback();
      }
      complete && complete();
    },
    //响应时间
    *fetchRequestTimeRange({
      payload,
      callback,
      complete
    }, {call, put}) {
      const response = yield call(getAppRequestTimeRange, payload);
      if (response) {
        yield put({type: 'saveRequestTimeRange', payload: response.bean});
        callback && callback();
      }
      complete && complete();
    },
    //吞吐率
    *fetchRequest({
      payload,
      callback,
      complete
    }, {call, put}) {
      const response = yield call(getAppRequest, payload);
      if (response) {
        yield put({type: 'saveRequest', payload: response.bean});
        callback && callback();
      }
      complete && complete();
    },
    //吞吐率
    *fetchRequestRange({
      payload,
      callback,
      complete
    }, {call, put}) {
      const response = yield call(getAppRequestRange, payload);

      if (response) {
        yield put({type: 'saveRequestRange', payload: response.bean});
        callback && callback();
      }
      complete && complete();
    },
    //磁盘使用量
    *fetchDisk({
      payload,
      callback,
      complete
    }, {call, put}) {
      const response = yield call(getAppDisk, payload);
      if (response) {
        yield put({type: 'saveAppDisk', payload: response.bean});
        callback && callback();
      }
      complete && complete();
    },
    //内存使用量
    *fetchMemory({
      payload,
      callback,
      complete
    }, {call, put}) {
      const response = yield call(getAppMemory, payload);
      if (response) {
        yield put({type: 'saveAppMemory', payload: response.bean});
        callback && callback();
      }
      complete && complete();
    },
    //在线人数
    *fetchOnlineNumber({
      payload,
      callback,
      complete
    }, {call, put}) {
      const response = yield call(getAppOnlineNumber, payload);
      if (response) {
        yield put({type: 'saveOnlineNumber', payload: response.bean});
        callback && callback();
      }
      complete && complete();
    },
    //在线人数
    *fetchOnlineNumberRange({
      payload,
      callback,
      complete
    }, {call, put}) {
      const response = yield call(getAppOnlineNumberRange, payload);
      if (response) {
        yield put({type: 'saveOnlineNumberRange', payload: response.bean});
        callback && callback();
      }
      complete && complete();
    },
    //获取分支
    *fetchBranch({
      payload,
      callback,
      complete
    }, {call, put}) {
      const response = yield call(getCodeBranch, payload);
      if (response) {
        yield put({type: 'saveBranch', payload: response.list});
        callback && callback();
      }
      complete && complete();
    },
    //设置分支
    *setBranch({
      payload,
      callback,
      complete
    }, {call, put}) {
      const response = yield call(setCodeBranch, payload);
      if (response) {
        callback && callback();
      }
      complete && complete();
    },
    //设置用户权限
    *setMemberAction({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(setMemberAction, payload);
      console.log(response);
      if (response) {
        callback && callback();
      }
    },
    *fetchMember({
      payload
    }, {call, put}) {

      const response = yield call(getMembers, payload);
      if (response) {
        yield put({type: 'saveMember', payload: response.list});
      }
    },
    *deleteMember({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(deleteMember, payload);

      if (response) {
        callback && callback();
      }
    },
    *editMemberAction({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(editMemberAction, payload);
      if (response) {
        callback && callback();
      }
    },
    *deleteApp({
      payload,
      callback
    }, {call, put}) {
      const response = yield call(deleteApp, payload);
      if (response) {
        callback && callback();
      }
    }
  },
  reducers : {
    clearMembers(state, action) {
      return {
        ...state,
        members: []
      };
    },
    saveMember(state, action) {
      return {
        ...state,
        members: action.payload
      };
    },
    saveVisitInfo(state, action) {
      return {
        ...state,
        visitInfo: action.payload
      };
    },
    clearVisitInfo(state, action) {
      return {
        ...state,
        visitInfo: null
      };
    },
    clearPods(state, action) {
      return {
        ...state,
        pods: []
      };
    },
    savePods(state, action) {
      return {
        ...state,
        pods: action.payload
      };
    },
    clearExtendInfo(state, action) {
      return {
        ...state,
        extendInfo: null
      };
    },
    saveExtendInfo(state, action) {
      return {
        ...state,
        extendInfo: action.payload
      };
    },
    saveBranch(state, action) {
      return {
        ...state,
        codeBranch: action.payload
      };
    },
    saveApps(state, action) {
      return {
        ...state,
        apps: action.payload
      };
    },
    clearPorts(state, action) {
      return {
        ...state,
        ports: []
      };
    },
    savePorts(state, action) {
      return {
        ...state,
        ports: action.payload
      };
    },
    clearInnerEnvs(state, action) {
      return {
        ...state,
        innerEnvs: []
      };
    },
    saveInnerEnvs(state, action) {
      return {
        ...state,
        innerEnvs: action.payload
      };
    },
    clearOuterEnvs(state, action) {
      return {
        ...state,
        outerEnvs: []
      };
    },
    saveOuterEnvs(state, action) {
      return {
        ...state,
        outerEnvs: action.payload
      };
    },
    clearRelationOuterEnvs(state, action) {
      return {
        ...state,
        relationOuterEnvs: []
      };
    },
    saveRelationOuterEnvs(state, action) {
      return {
        ...state,
        relationOuterEnvs: action.payload
      };
    },
    clearRunningProbe(state, action) {
      return {
        ...state,
        runningProbe: {}
      };
    },
    saveRunningProbe(state, action) {
      return {
        ...state,
        runningProbe: action.payload
      };
    },
    clearStartProbe(state, action) {
      return {
        ...state,
        startProbe: {}
      };
    },
    saveStartProbe(state, action) {
      return {
        ...state,
        startProbe: action.payload
      };
    },
    saveBaseInfo(state, action) {
      return {
        ...state,
        baseInfo: action.payload
      };
    },
    clearVolumes(state, action) {
      return {
        ...state,
        volumes: []
      };
    },
    saveVolumes(state, action) {
      return {
        ...state,
        volumes: action.payload
      };
    },
    saveCertificates(state, action) {
      return {
        ...state,
        certificates: action.payload
      };
    },
    clearRequesTime(state, action) {
      return {
        ...state,
        requestTime: {}
      };
    },
    saveRequestTime(state, action) {
      return {
        ...state,
        requestTime: action.payload
      };
    },
    clearRequesTimeRange(state, action) {
      return {
        ...state,
        requestTimeRange: {}
      };
    },
    saveRequestTimeRange(state, action) {
      return {
        ...state,
        requestTimeRange: action.payload
      };
    },
    clearAppDisk(state, action) {
      return {
        ...state,
        appDisk: {}
      };
    },
    saveAppDisk(state, action) {
      return {
        ...state,
        appDisk: action.payload
      };
    },
    clearAppMemory(state, action) {
      return {
        ...state,
        appMemory: {}
      };
    },
    saveAppMemory(state, action) {
      return {
        ...state,
        appMemory: action.payload
      };
    },
    clearRequest(state, action) {
      return {
        ...state,
        appRequest: {}
      };
    },
    saveRequest(state, action) {
      return {
        ...state,
        appRequest: action.payload
      };
    },
    clearRequestRange(state, action) {
      return {
        ...state,
        appRequestRange: {}
      };
    },
    saveRequestRange(state, action) {

      return {
        ...state,
        appRequestRange: action.payload
      };
    },
    clearOnlineNumber(state, action) {
      return {
        ...state,
        onlineNumber: {}
      };
    },
    saveOnlineNumber(state, action) {
      return {
        ...state,
        onlineNumber: action.payload
      };
    },
    clearOnlineNumberRange(state, action) {
      return {
        ...state,
        onlineNumberRange: {}
      };
    },
    saveOnlineNumberRange(state, action) {
      return {
        ...state,
        onlineNumberRange: action.payload
      };
    },
    clearDetail(state, action) {
      return {
        ...state,
        appDetail: {}
      };
    },
    saveTags(state, action) {
      return {
        ...state,
        tags: action.payload
      };
    },
    clearTags(state, action) {
      return {
        ...state,
        tags: null
      };
    },
    saveDetail(state, action) {
      return {
        ...state,
        appDetail: action.payload
      };
    }
  }
};
