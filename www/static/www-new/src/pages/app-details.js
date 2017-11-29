import React, {Component} from 'react';
import ReactDOM from 'react-dom';
import store from '../store/store';
import {Provider, browserHistory, connect} from 'react-redux';
import { NavLink } from 'react-router-dom';
import {HashRouter as Router, Route, Redirect, Switch} from 'react-router-dom';
import AppDeploy from './app-deploy';
import AppMonitor from './app-monitor';
import AppLog from './app-log';
import AppCost from './app-cost';
import AppExpansion from './app-expansion';
import AppRelation from './app-relation';
import AppStorage from './app-storage';
import AppPort from './app-port';
import AppSetting from './app-setting';

import { getAppInfoAction } from '../actions/app-actions';

class AppDetail extends Component {
	constructor(props){
		super(props);
	}
	componentWillMount(){
		const tenantName  = document.querySelector('#input-tenantName').value;
		const serviceAlias = document.querySelector('#input-serviceAlias').value;
		//获取应用的基本信息
		this.props.dispatch(getAppInfoAction(
			tenantName,
			serviceAlias
		))
	}
	render(){
		const appInfo = this.props.appInfo || {};

		return (
				<div>
				{ 
					appInfo ?  
						(<Router history={this.props.history}>
						<div>
							 <div className="clearfix">
						        <h3 className="tit-color pull-left" id="appname">{appInfo.service['service_cname']}</h3>
						        <ul className="nav nav-pills pull-left" id="nav-tabs">
						            <li>
						        		<NavLink to="/deployed" activeClassName="active">概览</NavLink>
						        	</li>
						        	
						            {
						            	appInfo.monitor_control ? 
						            	<li>
							            	<NavLink to="/monitor" activeClassName="active">监控</NavLink>
							            </li>
							            :
							            ''
						            }
						            <li>
						            	<NavLink to="/applog" activeClassName="active">日志</NavLink>
						            </li>
						            {
						            	appInfo.community ? 
						            	<li>
							            	<NavLink to="/cost" activeClassName="active">费用</NavLink>
							            </li>
							            :
							            ''
						            }
						            <li>
						            	<NavLink to="/expansion" activeClassName="active">扩容</NavLink>
						            </li>
						            <li>
						        		<NavLink to="/relations" activeClassName="active">依赖</NavLink>
						        	</li>
						        	<li>
						        		<NavLink to="/storage" activeClassName="active">存储</NavLink>
						        	</li>
						            <li>
						        		<NavLink to="/port" activeClassName="active">端口</NavLink>
						        	</li>
						            <li>
						            	<NavLink to="/settings" activeClassName="active">设置</NavLink>
						            </li>
						        </ul>
						    </div>
						    <section>
						    	<Switch>
									<Route exact path="/deployed" component={AppDeploy}></Route>
									<Route path="/monitor" component={AppMonitor}></Route>
									<Route path="/applog" component={AppLog}></Route>
									<Route exact path="/cost" component={AppCost}></Route>
									<Route exact path="/expansion" component={AppExpansion}></Route>
									<Route path="/relations" component={AppRelation}></Route>
									<Route path="/storage" component={AppStorage}></Route>
									<Route path="/port" component={AppPort}></Route>
									<Route path="/settings" component={AppSetting}></Route>
									<Redirect from='/' to='/deployed'/>
								</Switch>  
						    </section>
						</div>
						</Router>)
						:
						''
				}
				</div>
		)
	}
}



const ConnectedAppDetails = connect((state, props) => {
	return {
		appInfo: state.appInfo
	}
})(AppDetail);

ReactDOM.render((
	<Provider store={store}>
		<ConnectedAppDetails />
	</Provider>
), document.querySelector('#app-detail-wrapper'))