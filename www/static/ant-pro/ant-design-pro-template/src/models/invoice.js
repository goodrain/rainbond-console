import { getInovices, getOrders, confirmApplyInvoice, submitApplyInvoice,
    getInvoiceInfo } from '../services/invoice';

export default {
  namespace: 'invoice',
  state: {
    data: {
      list: []
    },
  },
  effects: {
    *getInvoiceInfo({ payload, callback }, { call, put }) {
        const response = yield call(getInvoiceInfo, payload);
        if(response){
          callback && callback(response);
        }
    },
    *confirmApplyInvoice({ payload, callback }, { call, put }) {
        const response = yield call(confirmApplyInvoice, payload);
        if(response){
          callback && callback(response);
        }
    },
    *submitApplyInvoice({ payload, callback }, { call, put }) {
        const response = yield call(submitApplyInvoice, payload);
        if(response){
          callback && callback(response);
        }
    },
    *getInovices({ payload, callback }, { call, put }) {
        const response = yield call(getInovices, payload);
        if(response){
          callback && callback(response);
        }
    },
    *getOrders({ payload, callback }, { call, put }) {
      const response = yield call(getOrders, payload);
      if(response){
        callback && callback(response);
      }
    }
  },

  reducers: {
  }
};
