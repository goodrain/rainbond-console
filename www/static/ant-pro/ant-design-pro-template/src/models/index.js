import { getTeamRegionGroups, getTeamRegionApps, getTeamRegionAppsStatus, getTeamRegionOverview, 
  getTeamRegionGroup, getNewestEvent } from '../services/team';
import cookie from '../utils/cookie';

export default {
  namespace: 'index',
  state: {
    //总览信息
    overviewInfo:{},
    //所有分组
    groups: [],
    apps: [],
    groupInfo: {},
    appsStatus:[],
    //最新动态
    events:[],
    pagination:{
      pageSize: 10,
      currentPage: 1,
      total: 0,
      order:'',
      fields:''
    }
  },
  effects: {
    *fetchEvents({ payload, callback }, { call, put }){
      const response = yield call(getNewestEvent, payload);
      if(response){
        yield put({
          type: 'saveEvents',
          payload: response.list
        });

        callback && callback(response.list)
      }
      
    },
    *fetchOverview({ payload }, { call, put }) {
      const response = yield call(getTeamRegionOverview, payload);
      yield put({
        type: 'saveOverviewInfo',
        payload: response.bean
      });
    },
    *fetchApps({ payload }, { put, select, call }) {
      const response = yield call(getTeamRegionApps, payload);
      if(response){
          yield put({
            type: 'saveApps',
            payload: response.list || []
          });

          yield put({
            type: 'savePage',
            payload: {
              total: response.total || 0
            }
          });
      }
    },
    *fetchAppsStatus({ payload }, { call, put }) {
      const response = yield call(getTeamRegionAppsStatus, payload);
      if(response){
        yield put({
          type: 'saveAppsStatus',
          payload: response.list
        });
      }
      
    }
  },

  reducers: {
    saveEvents(state, {payload}){
      return {
        ...state,
        events: payload
      };
    },
    saveOverviewInfo(state, { payload }) {
      return {
        ...state,
        overviewInfo: payload
      };
    },
    saveAppsStatus(state, action){
       return {
        ...state,
        appsStatus: action.payload
      };
    },
    saveApps(state, action) {
      return {
        ...state,
        apps: action.payload,
      };
    },
    savePage(state, action) {
      return {
        ...state,
        pagination: {
          ...state.pagination,
          ...action.payload
        },

      };
    }
  },
};
