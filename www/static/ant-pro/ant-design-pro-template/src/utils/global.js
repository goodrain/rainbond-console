import cookie from './cookie';
const global = {
				getCurrTeamName() {
								var reg = /team\/([^\/]+)/;
								const hash = location.hash || '';
								var match = hash.match(reg);
								if (match) {
												return match[1];
								}
								return '';
				},
				getCurrRegionName() {
								var reg = /region\/([^\/]+)/;
								const hash = location.hash || '';
								var match = hash.match(reg);
								if (match) {
												return match[1];
								}
								return '';
				}
}

export default global;