import { getPorts } from '../services/app';
import cookie from '../utils/cookie';

export default {
  namespace: 'appDetail',
  state: {
    //应用详情
    detail: {},
    //应用端口信息
    ports:[]
  },
  effects: {
    *fetchPorts({ payload }, { call, put }) {
      const response = yield call(getPorts, payload);
      if(response) {
          yield put({
            type: 'savePorts',
            payload: response.list
          });
      }
    }
  },
  reducers: {
    savePorts(state, action) {
      return {
        ...state,
        ports: action.payload
      };
    }
  },
};
