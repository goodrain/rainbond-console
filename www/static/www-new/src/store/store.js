import {createStore, applyMiddleware} from 'redux';
import thunk from 'redux-thunk';
import reducer from '../reducers';
import {fromJS, Map} from 'immutable';

const initState = {
	//应用基本信息
	appInfo: null
}


const store = createStore(reducer, initState, applyMiddleware(thunk));
export default store;