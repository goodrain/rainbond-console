import cookie from './cookie';
const global = {
		getCurrTeamName() {
				return cookie.get('team');
		},
		getCurrRegionName() {
				return cookie.get('region_name');
		}
}

export default global;