import { createAppByCode, createAppByCompose, createAppByDockerrun, getMarketApp, installApp , queryExport,appExport,getExport,
getAppsByComposeId,uploadApp,importApp,queryImportApp,importDir,queryImportDirApp } from '../services/createApp';

export default {
  namespace: 'createApp',

  state: {
     extend_method: '',
     min_memory: '',
     service_runtimes:'',
     service_server:'',
     service_dependency:''
  },
  effects: {
    *getAppsByComposeId({payload, callback}, {call, put}) {
      const data = yield call(getAppsByComposeId, payload);
      if(data){
          callback && callback(data);
      }
    },
    *installApp({payload, callback}, {call, put}) {
      const data = yield call(installApp, payload);
      if(data){
          callback && callback(data);
      }
    },
    *createAppByCode({payload, callback}, {call, put}) {
      const data = yield call(createAppByCode, payload);
      if(data){
          setTimeout(()=>{
              callback && callback(data);
          })
      }
    },
    *createAppByCompose({payload, callback}, {call, put}) {
      const data = yield call(createAppByCompose, payload);
      if(data){
          setTimeout(()=>{
              callback && callback(data);
          })
      }
      
    },
    *createAppByDockerrun({payload, callback}, {call, put}) {
      const data = yield call(createAppByDockerrun, payload);
      if(data){
          setTimeout(()=>{
              callback && callback(data);
          })
      }
    },
    *getMarketApp({payload, callback}, {call, put}) {
      const data = yield call(getMarketApp, payload);
      if(data){
          callback && callback(data);
      }
    },
    *queryExport({payload, callback}, {call, put}) {
      const data = yield call(queryExport, payload);
      if(data){
          callback && callback(data);
      }
    },
    *appExport({payload, callback}, {call, put}) {
      const data = yield call(appExport, payload);
      if(data){
          callback && callback(data);
      }
    },
    *getExport({payload, callback}, {call, put}) {
      const data = yield call(getExport, payload);
      if(data){
          callback && callback(data);
      }
    },
    *uploadApp({payload, callback}, {call, put}) {
      const data = yield call(uploadApp, payload);
      if(data){
          callback && callback(data);
      }
    },
    *importApp({payload, callback}, {call, put}) {
      const data = yield call(importApp, payload);
      if(data){
          callback && callback(data);
      }
    },
    *queryImportApp({payload, callback}, {call, put}) {
      const data = yield call(queryImportApp, payload);
      if(data){
          callback && callback(data);
      }
    },
    *importDir({payload, callback}, {call, put}) {
      const data = yield call(importDir, payload);
      if(data){
          callback && callback(data);
      }
    },
     *queryImportDirApp({payload, callback}, {call, put}) {
      const data = yield call(queryImportDirApp, payload);
      if(data){
          callback && callback(data);
      }
    }
  },
 
  reducers: {
    saveRuntimeInfo(state, {payload}){
       console.log(payload)
       return {
        ...state,
        ...payload
      }
    },
    clearRuntimeInfo(state){
      return {
        extend_method: '',
        min_memory: '',
        service_runtimes:'',
        service_server:'',
        service_dependency:''
      }
    }
  }
};
