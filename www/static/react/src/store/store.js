import {createStore, applyMiddleware} from 'redux';
import thunk from 'redux-thunk';
import reducer from '../reducers';
import {fromJS, Map} from 'immutable';

const initState = {
	userInfo:null,
	//当前是否在请求状态
	isAppLoading:false,
	//app初始化数据是否加载完成
	isAppInited:false,
	//是否是公有云
	isPublic:true,
	router:'',
	//所属的团队
	teams:null,
	//所有的数据中心
	regions:null,
	//选中的团队
	selectedTeam: '',
	//选中的数据中心
	selectedRegion: ''

}


const store = createStore(reducer, initState, applyMiddleware(thunk));
export default store;