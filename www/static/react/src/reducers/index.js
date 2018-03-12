export default function reducers(state = {}, action={}) {
	switch(action.type){
		case 'ISPUBLIC' :
			return Object.assign({}, state, {isPublic:action.payload});
		case 'SHOW_LOADING' :
			return Object.assign({}, state, {isAppLoading:true});
		case 'HIDDEN_LOADING' :
			return Object.assign({}, state, {isAppLoading:false});
	    case 'LOGIN':
	    	
	    	return Object.assign({}, state, {userInfo: action.userInfo})
	    case 'LOGOUT':
	    	return Object.assign({}, state, {userInfo: null})
	    case 'INITED':
	    	return Object.assign({}, state, {isAppInited: true})
	    case 'ROUTER':
	        return Object.assign({}, state, {router: action.payload})
	}
	return state;
}