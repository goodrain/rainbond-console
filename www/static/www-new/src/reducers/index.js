export default function reducers(state = {}, action={}) {
	switch(action.type){
		case 'SET_APP_INFO':
			return Object.assign({}, state, {appInfo: action.appInfo});
	}
	return state;
}