import React, {Component} from 'react';
import { Layout, Icon, Row, Col } from 'antd';
import config from '../config/config';
const { Footer }  = Layout;

class SiteFooter extends Component {
	constructor(props) {
		super(props);
	}
	handleLogout = () => {
		logout(this.props.dispatch)
	}
	render() {
		return (
			<Footer>
				<div class="footbtm">
					<div class="clearfix insidebox">
						<p><span>Copyright © 2017 北京好雨科技有限公司 </span><span>京ICP备15028663</span></p>
					</div>
				</div>
			</Footer>
		)
	}
}
export default SiteFooter;