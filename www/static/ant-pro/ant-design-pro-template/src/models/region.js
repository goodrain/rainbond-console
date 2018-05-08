import {
    getProtocols
  } from '../services/region';
  import cookie from '../utils/cookie';
  
  export default {
    namespace : 'region',
    state : {
      //成员
      protocols: []
    },
    effects : {
      *fetchProtocols({
        payload,
        callback
      }, {call, put}) {
        const response = yield call(getProtocols, payload);
        if (response && !response.status) {
          yield put({type: 'saveProtocols', payload: response.list});
        }
      }
    },
    reducers : {
        saveProtocols(state, action) {
        return {
          ...state,
          protocols: action.payload
        };
      }
    }
  };
  