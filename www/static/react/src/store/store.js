import {createStore, applyMiddleware} from 'redux';
import thunk from 'redux-thunk';
import reducer from '../reducers';
import {fromJS, Map} from 'immutable';

const initState = {
	userInfo:null,
	//当前是否在请求状态
	isAppLoading:false,
	//app初始化数据是否加载完成
	initDataLoaded:false,
	//是否是公有云
	isPublic:true,
	//数据中心节点类型
	//用户管理列表
	userList:[],
	redirect:''
}


const store = createStore(reducer, initState, applyMiddleware(thunk));
export default store;