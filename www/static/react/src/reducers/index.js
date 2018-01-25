export default function reducers(state = {}, action={}) {
	switch(action.type){
		case 'ISPUBLIC' :
			return Object.assign({}, state, {isPublic:action.payload});
		case 'SHOW_LOADING' :
			return Object.assign({}, state, {isAppLoading:true});
		case 'HIDDEN_LOADING' :
			return Object.assign({}, state, {isAppLoading:false});
		case 'SET_HOME_PAGINATION' :
		    const pagination = Object.assign({}, state.homeTablePagination, action.pagination||{});
			return Object.assign({}, state, {homeTablePagination:pagination});
		case 'SET_HOME_LIST_DATASOURCE' :
		    return Object.assign({}, state, {homeList:action.list||[]});
	    case 'CLEAN_HOME_STATE' :
	    	return Object.assign({}, state, {
	    		homeList:[],
	    		homeSelectedKeys:[],
	    		homeTablePagination:{
					current:1,
					total:0,
					pageSize:50
				}
	    	})
	    case 'SET_HOME_SELECTED_KEYS':
	    	return Object.assgin({}, state, {
	    		homeSelectedKeys:action.selectedKeys
	    	})
	    case 'SET_DATACENTER_LIST' : 
	    	return Object.assign({}, state, {
	    		dataCenterList: action.list || []
	    	})
	    case 'SET_USER_LIST': 
	    	return Object.assign({}, state, {userList: action.list})
	    case 'CLEAR_USER_LIST': 
	    	return Object.assign({}, state, {userList: []})
	    case 'SET_CLUSTER_LIST':
	    	return Object.assign({}, state, {clusterList: action.list})
	    case 'CLEAR_CLUSTER_LIST':
	    	return Object.assign({}, state, {clusterList: []});
	    case 'LOGIN':
	    	return Object.assign({}, state, {userInfo: action.userInfo})
	    case 'LOGOUT':
	    	return Object.assign({}, state, {userInfo: null})
	    case 'SET_REDIRECT':
	    	return Object.assign({}, state, {redirect: action.redirect})


	}
	return state;
}