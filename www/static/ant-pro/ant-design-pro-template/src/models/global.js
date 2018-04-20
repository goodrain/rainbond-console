import {
  queryNotices,
  isPubCloud,
  getRainbondInfo,
  bindGithub,
  syncMarketApp,
  getMarketApp,
  syncMarketAppDetail,
  authEnterprise,
  getCompanyInfo,
  getRegionOneDayMoney,
  getRegionSource,
  offlineMarketApp
} from '../services/api';
import {getTeamRegionGroups} from '../services/team'

export default {
  namespace : 'global',

  state : {
    collapsed: false,
    notices: [],
    //是否是共有云帮
    isPubCloud: null,
    //当前团队和数据中心的群组
    groups: null,
    currTeam: '',
    currRegion: '',
    //云帮平台信息
    rainbondInfo: null,
    apploadingnum: 0,
    //显示充值提示
    payTip: false
  },
  effects : {
    *offlineMarketApp({
      payload,
      callback
    }, {call, put}) {
      const data = yield call(offlineMarketApp, payload);
      if (data) {
        callback && callback(data)
      }
    },
    *getRegionSource({
      payload,
      callback
    }, {call, put}) {
      const data = yield call(getRegionSource, payload);
      if (data) {
        callback && callback(data)
      }
    },
    *getRegionOneDayMoney({
      payload,
      callback
    }, {call, put}) {
      const data = yield call(getRegionOneDayMoney, payload);
      if (data) {
        callback && callback(data)
      }
    },
    *getCompanyInfo({
      payload,
      callback
    }, {call, put}) {
      const data = yield call(getCompanyInfo, payload);
      if (data) {
        callback && callback(data)
      }
    },
    *authEnterprise({
      payload,
      callback
    }, {call, put}) {
      const data = yield call(authEnterprise, payload);
      if (data) {
        callback && callback(data)
      }
    },
    *syncMarketAppDetail({
      payload,
      callback
    }, {call, put}) {
      const data = yield call(syncMarketAppDetail, payload);
      if (data) {
        callback && callback(data)
      }

    },
    *getMarketApp({
      payload,
      callback
    }, {call, put}) {
      const data = yield call(getMarketApp, payload);
      if (data) {
        callback && callback(data)
      }

    },
    *syncMarketApp({
      payload,
      callback
    }, {call, put}) {
      const data = yield call(syncMarketApp, payload);
      if (data) {
        callback && callback(data)
      }

    },
    *fetchRainbondInfo({
      callback
    }, {call, put}) {
      const data = yield call(getRainbondInfo);
      if (data) {
        yield put({type: 'saveRainBondInfo', payload: data.bean})
        setTimeout(() => {
          callback && callback();
        })
      }

    },
    *fetchIsPublic(_, {call, put}) {
      const data = yield call(isPubCloud);
      yield put({
        type: 'saveIsPubCloud',
        payload: !!data.bean.is_public
      })
    },
    *fetchNotices(_, {call, put}) {
      const data = yield call(queryNotices);
      yield put({type: 'saveNotices', payload: data});
      yield put({type: 'user/changeNotifyCount', payload: data.length});
    },
    *clearNotices({
      payload
    }, {put, select}) {
      yield put({type: 'saveClearedNotices', payload});
      const count = yield select(state => state.global.notices.length);
      yield put({type: 'user/changeNotifyCount', payload: count});
    },
    *fetchGroups({
      payload,
      callback
    }, {put, call}) {

      const response = yield call(getTeamRegionGroups, payload);
      if (response) {
        yield put({
          type: 'saveGroups',
          payload: response.list || []
        })
        callback && callback();
      }
    },
    *bindGithub({
      payload,
      callback
    }, {put, call}) {
      const response = yield call(bindGithub, payload);
      if (response) {
        callback && callback();
      }
    }
  },

  reducers : {
    showPayTip(state){
      return {
        ...state,
        payTip: true
      };
    },
    hidePayTip(state){
      return {
        ...state,
        payTip: false
      };
    },
    saveRainBondInfo(state, {payload}) {

      return {
        ...state,
        rainbondInfo: payload
      };
    },
    saveIsPubCloud(state, {payload}) {
      return {
        ...state,
        isPubCloud: payload
      };
    },
    changeLayoutCollapsed(state, {payload}) {
      return {
        ...state,
        collapsed: payload
      };
    },
    saveNotices(state, {payload}) {
      return {
        ...state,
        notices: payload
      };
    },
    saveClearedNotices(state, {payload}) {
      return {
        ...state,
        notices: state
          .notices
          .filter(item => item.type !== payload)
      };
    },
    saveGroups(state, {payload}) {
      return {
        ...state,
        groups: payload
      };
    },
    saveCurrTeamAndRegion(state, {payload}) {
      return {
        ...state,
        ...payload
      }
    },
    showLoading(state, {}) {
      return {
        ...state,
        apploadingnum: state.apploadingnum + 1
      }
    },
    hiddenLoading(state, {}) {
      return {
        ...state,
        apploadingnum: state.apploadingnum - 1
      }
    }
  },

  subscriptions : {
    setup({history}) {
      // Subscribe history(url) change, trigger `load` action if pathname is `/`
      return history.listen(({pathname, search}) => {
        if (typeof window.ga !== 'undefined') {
          window.ga('send', 'pageview', pathname + search);
        }
      });
    }
  }
};
