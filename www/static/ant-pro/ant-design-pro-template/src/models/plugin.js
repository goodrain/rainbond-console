import { getMyPlugins, createPlugin, getPluginInfo, getPluginVersions, getPluginVersionInfo,
getPluginVersionConfig, editPluginVersionInfo, addPluginVersionConfig, removePluginVersionConfig,
editPluginVersionConfig, removePluginVersion, createPluginVersion, buildPluginVersion,
getBuildPluginVersionStatus, getBuildVersionLog, getUsedApp, deletePlugin, getDefaultPlugin, installDefaultPlugin } from '../services/plugin';
import cookie from '../utils/cookie';

export default {
  namespace: 'plugin',
  state: {
    //组详情
    groupDetail:{},
    //应用
    apps:[]
  },
  effects: {
    *installDefaultPlugin({ payload, callback }, { call, put }) {
      const response = yield call(installDefaultPlugin, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *getDefaultPlugin({ payload, callback }, { call, put }) {
      const response = yield call(getDefaultPlugin, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *getUsedApp({ payload, callback }, { call, put }) {
      const response = yield call(getUsedApp, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *getBuildVersionLog({ payload, callback }, { call, put }) {
      const response = yield call(getBuildVersionLog, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *getBuildPluginVersionStatus({ payload, callback }, { call, put }) {
      const response = yield call(getBuildPluginVersionStatus, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *buildPluginVersion({ payload, callback }, { call, put }) {
      const response = yield call(buildPluginVersion, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *createPluginVersion({ payload, callback }, { call, put }) {
      const response = yield call(createPluginVersion, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *removePluginVersion({ payload, callback }, { call, put }) {
      const response = yield call(removePluginVersion, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *getPluginVersionConfig({ payload, callback }, { call, put }) {
      const response = yield call(getPluginVersionConfig, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *removePluginVersionConfig({ payload, callback }, { call, put }) {
      const response = yield call(removePluginVersionConfig, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *addPluginVersionConfig({ payload, callback }, { call, put }) {
      const response = yield call(addPluginVersionConfig, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *editPluginVersionConfig({ payload, callback }, { call, put }) {
      const response = yield call(editPluginVersionConfig, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *getPluginVersionInfo({ payload, callback }, { call, put }) {
      const response = yield call(getPluginVersionInfo, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *editPluginVersionInfo({ payload, callback }, { call, put }) {
      const response = yield call(editPluginVersionInfo, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *getPluginVersions({ payload, callback }, { call, put }) {
      const response = yield call(getPluginVersions, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *getMyPlugins({ payload, callback }, { call, put }) {
      const response = yield call(getMyPlugins, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *createPlugin({ payload, callback }, { call, put }) {
      const response = yield call(createPlugin, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *getPluginInfo({ payload, callback }, { call, put }) {
      const response = yield call(getPluginInfo, payload);
      if(response) {
          callback && callback(response);
      }
    },
    *deletePlugin({ payload, callback }, { call, put }) {
      const response = yield call(deletePlugin, payload);
      if(response) {
          callback && callback(response);
      }
    },
  },
  reducers: {
    clearApps(state, action){
      return {
        ...state,
        apps: []
      };
    },
  },
};
