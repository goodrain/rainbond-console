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
				},
				replaceUrlTeam(team){
					var href = location.href;
					var reg = /team\/([^/]+)/;
					href = href.replace(reg, (string, g1)=> {
						return string.replace(new RegExp(g1), team);
					})
					return href;
				},
				replaceUrlRegion(region){
					var href = location.href;
					var reg = /region\/([^/]+)/;
					href = href.replace(reg, (string, g1)=> {
						return string.replace(new RegExp(g1), region);
					})
					return href;
				},
				replaceUrlTeamAndTegion(team, region){
					var href = location.href;
					var reg = /team\/([^/]+)\/region\/([^/]+)/;
					href = href.replace(reg, (string, g1, g2)=> {
						console.log(2222)
						return string.replace(new RegExp(g1), team).replace(new RegExp(g2), region);
					})
					return href;
				}
}

export default global;