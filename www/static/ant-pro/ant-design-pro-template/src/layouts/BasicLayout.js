import React, {Fragment} from 'react';
import PropTypes from 'prop-types';
import {Layout, Icon, message, notification, Modal, Button} from 'antd';
import DocumentTitle from 'react-document-title';
import {connect} from 'dva';
import {Route, Redirect, Switch, routerRedux} from 'dva/router';
import {ContainerQuery} from 'react-container-query';
import classNames from 'classnames';
import {enquireScreen} from 'enquire-js';
import GlobalHeader from '../components/GlobalHeader';
import GlobalFooter from '../components/GlobalFooter';
import SiderMenu from '../components/SiderMenu';
import NotFound from '../routes/Exception/404';
import {getRoutes} from '../utils/utils';
import userUtil from '../utils/user';
import globalUtil from '../utils/global';
import cookie from '../utils/cookie';
import Authorized from '../utils/Authorized';
import {getMenuData} from '../common/menu';
import logo from '../../public/logo-icon-35.png';
import OpenRegion from '../components/OpenRegion';
import CreateTeam from '../components/CreateTeam';
import Loading from '../components/Loading';
import ChangePassword from '../components/ChangePassword';

import CheckUserInfo from './CheckUserInfo'
import InitTeamAndRegionData from './InitTeamAndRegionData'
import PayTip from './PayTip'
import Meiqia from './Meiqia'

const {Content} = Layout;
const {AuthorizedRoute} = Authorized;

/**
 * 根据菜单取得重定向地址.
 */
const redirectData = [];
const getRedirect = (item) => {
    if (item && item.children) {
        if (item.children[0] && item.children[0].path) {
            redirectData.push({from: `/${item.path}`, to: `/${item.children[0].path}`});
            item
                .children
                .forEach((children) => {
                    getRedirect(children);
                });
        }
    }
};
getMenuData().forEach(getRedirect);

const query = {
    'screen-xs': {
        maxWidth: 575
    },
    'screen-sm': {
        minWidth: 576,
        maxWidth: 767
    },
    'screen-md': {
        minWidth: 768,
        maxWidth: 991
    },
    'screen-lg': {
        minWidth: 992,
        maxWidth: 1199
    },
    'screen-xl': {
        minWidth: 1200
    }
};

let isMobile;
enquireScreen((b) => {
    isMobile = b;
});


class BasicLayout extends React.PureComponent {
    static childContextTypes = {
        location: PropTypes.object,
        breadcrumbNameMap: PropTypes.object,
        currRegion: PropTypes.string,
        currTeam: PropTypes.string
    }
    state = {
        isMobile,
        isInit: false,
        openRegion: false,
        createTeam: false,
        showChangePassword: false,
        showWelcomeCreateTeam: false,
        canCancelOpenRegion: true
    };
    componentDidMount() {
        enquireScreen((mobile) => {
            this.setState({isMobile: mobile});
        });
        this.fetchUserInfo();
    }
    onOpenRegion = () => {
        this.setState({openRegion: true})
    }
    cancelOpenRegion = () => {
        this.setState({openRegion: false, canCancelOpenRegion: true})
    }
    onCreateTeam = () => {
        this.setState({createTeam: true})
    }
    cancelCreateTeam = () => {
        this.setState({createTeam: false})
    }
    handleCreateTeam = (values) => {
        this
            .props
            .dispatch({
                type: 'teamControl/createTeam',
                payload: values,
                callback: () => {
                    notification.success({message: `添加成功`});
                    this.cancelCreateTeam();
                    this
                        .props
                        .dispatch({type: 'user/fetchCurrent'})
                }
            })
    }
    getChildContext() {
        const {location, routerData, currTeam, currRegion} = this.props;
        return {location, breadcrumbNameMap: routerData};
    }
    
    fetchUserInfo = () => {
        //获取用户信息、保存团队和数据中心信息
        this
            .props
            .dispatch({
                type: 'user/fetchCurrent',
                callback: (user) => {
                    var load =  document.querySelector('#load');
                    if(load){
                        load.style.display = 'none'
                    }

                },
                handleError: (res) => {
                    if (res && (res.status === 403 || res.status === 404)) {
                        cookie.remove('token');
                        cookie.remove('token', {domain: ''});
                        location.reload();
                    }
                }
            });
    }
    getPageTitle() {
        const {routerData, location, rainbondInfo} = this.props;
        const {pathname} = location;
        let title = `${rainbondInfo.title} | 应用一键部署`;
        if (routerData[pathname] && routerData[pathname].name) {
            title = `${routerData[pathname].name} - ` + title;
        }
        return title;
    }
    getBashRedirect = () => {
        // According to the url parameter to redirect 这里是重定向的,重定向到 url 的 redirect 参数所示地址
        const urlParams = new URL(window.location.href);

        const redirect = urlParams
            .searchParams
            .get('redirect');
        // Remove the parameters in the url
        if (redirect) {
            urlParams
                .searchParams
                .delete('redirect');
            window
                .history
                .replaceState(null, 'redirect', urlParams.href);
        } else {
            return '/index';
        }
        return redirect;
    }
    handleMenuCollapse = (collapsed) => {
        this
            .props
            .dispatch({type: 'global/changeLayoutCollapsed', payload: collapsed});
    }
    handleNoticeClear = (type) => {
        message.success(`清空了${type}`);
        this
            .props
            .dispatch({type: 'global/clearNotices', payload: type});
    }
    handleMenuClick = ({key}) => {
        if (key === 'cpw') {
            this.showChangePass();
        }
        if (key === 'logout') {
            this
                .props
                .dispatch({type: 'user/logout'});
        }
    }
    handleNoticeVisibleChange = (visible) => {
        if (visible) {
            this
                .props
                .dispatch({type: 'global/fetchNotices'});
        }
    }
    handleTeamClick = ({key}) => {

        if (key === 'createTeam') {
            this.onCreateTeam();
            return;
        }

        cookie.set('team', key);
        const currentUser = this.props.currentUser;
        let currRegionName = globalUtil.getCurrRegionName();
        const currTeam = userUtil.getTeamByTeamName(currentUser, key);
        
        if (currTeam) {
            const regions = currTeam.region || [];
            if(!regions.length){
                notification.warning({message: '该团队下无可用数据中心!'});
                return;
            }
            const selectRegion = regions.filter((item) => {
                return item.team_region_name === currRegionName;
            })[0];
            var selectRegionName = selectRegion
                ? selectRegion.team_region_name
                : regions[0].team_region_name;
            currRegionName = selectRegionName;
        }
        location.hash = `/team/${key}/region/${currRegionName}/index`;
        location.reload();
    }

    handleRegionClick = ({key}) => {
        if (key === 'openRegion') {
            this.onOpenRegion();
            return;
        }

        location.hash = `/team/${globalUtil.getCurrTeamName()}/region/${key}/index`;
        location.reload();

    }
    showChangePass = () => {
        this.setState({showChangePassword: true})
    }
    cancelChangePass = () => {
        this.setState({showChangePassword: false})
    }
    handleChangePass = (vals) => {
        this
            .props
            .dispatch({
                type: 'user/changePass',
                payload: {
                    ...vals
                },
                callback: () => {
                    notification.success({message: "修改成功，请重新登录"})
                }
            })
    }
    
    handleInitTeamOk = () => {
        this.setState({showWelcomeCreateTeam: false});
        this.fetchUserInfo();
    }
    handleCurrTeamNoRegion = () => {
        this.setState({openRegion: true, canCancelOpenRegion: false})
    }
    handleOpenRegion = (regions) => {
        const team_name = globalUtil.getCurrTeamName();
        this.props
            .dispatch({
                type: 'teamControl/openRegion',
                payload: {
                    team_name: team_name,
                    region_names: regions.join(',')
                },
                callback: (data) => {
                    notification.success({message: `开通成功`});
                    this.cancelOpenRegion();
                    this.props.dispatch({type: 'user/fetchCurrent', callback: ()=>{
                        this.props.dispatch(routerRedux.replace(`/team/${team_name}/region/${regions[0]}/index`));
                    }});
                }
            })
    }
    render() {
        const {
            currentUser,
            collapsed,
            fetchingNotices,
            notices,
            routerData,
            match,
            location,
            notifyCount,
            isPubCloud,
            currTeam,
            currRegion,
            groups,
            rainbondInfo
        } = this.props;
        const bashRedirect = this.getBashRedirect();
        const layout = () => {

            const team = userUtil.getTeamByTeamName(currentUser, globalUtil.getCurrTeamName());
            const hasRegion = !!(team.region && team.region.length);
            var renderContent = () => {

                //当前团队没有数据中心
                if(!hasRegion){
                    return <OpenRegion mode="card" onSubmit={this.handleOpenRegion} onCancel={this.cancelOpenRegion}/>
                    return null;
                }

                const region = userUtil.hasTeamAndRegion(currentUser, currTeam, currRegion) || {};
                const isRegionMaintain = region.region_status === '3';
                //数据中心维护中
                if(isRegionMaintain){
                    return <div style={{textAlign: 'center', padding: '50px 0'}}>
                        <Icon style={{fontSize: 50, marginBottom: 32}} type="warning" />
                        <h1 style={{fontSize: 50, color: 'rgba(0, 0, 0, 0.65)', marginBottom: 8}}>数据中心维护中</h1>
                        <p>请稍后访问当前数据中心</p>
                    </div>
                }else{
                    return <Switch>
                            {redirectData.map(item => <Redirect key={item.from} exact from={item.from} to={item.to}/>)}
                            {getRoutes(match.path, routerData).map(item => {
                                return (<AuthorizedRoute
                                    key={item.key}
                                    path={item.path}
                                    component={item.component}
                                    exact={item.exact}
                                    authority={item.authority}
                                    logined={true}
                                    redirectPath={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/exception/403`} />)
                            })}

                            <Redirect exact from="/" to={bashRedirect}/>
                            <Route render={NotFound}/>
                        </Switch>
                }
            }

            return <Layout>
                    {
                        hasRegion && <SiderMenu title={rainbondInfo.title} currentUser={currentUser} logo={rainbondInfo.logo || logo} 
                        Authorized={Authorized} menuData={getMenuData(groups)} collapsed={collapsed} location={location} isMobile={this.state.isMobile} onCollapse={this.handleMenuCollapse}/>
                    }
                    
                <Layout>
                    <GlobalHeader
                        logo={logo}
                        isPubCloud={rainbondInfo.is_public}
                        notifyCount={notifyCount}
                        currentUser={currentUser}
                        fetchingNotices={fetchingNotices}
                        notices={notices}
                        collapsed={collapsed}
                        isMobile={this.state.isMobile}
                        onNoticeClear={this.handleNoticeClear}
                        onCollapse={this.handleMenuCollapse}
                        onMenuClick={this.handleMenuClick}
                        onTeamClick={this.handleTeamClick}
                        onRegionClick={this.handleRegionClick}
                        onNoticeVisibleChange={this.handleNoticeVisibleChange}
                        currTeam={currTeam}
                        currRegion={currRegion}/>
                    <Content
                        style={{
                        margin: '24px 24px 0',
                        height: '100%'
                    }}>
                        {renderContent()} 
                    </Content>
                </Layout>
            </Layout>
        }

        return (
            <Fragment>
                <DocumentTitle title={this.getPageTitle()}>
                   <CheckUserInfo rainbondInfo={this.props.rainbondInfo} onCurrTeamNoRegion={this.handleCurrTeamNoRegion} userInfo={currentUser} onInitTeamOk={this.handleInitTeamOk}>
                    <InitTeamAndRegionData>
                        <ContainerQuery query={query}>
                            {params => <div className={classNames(params)}>{layout()}</div>}
                        </ContainerQuery>
                    </InitTeamAndRegionData>
                    </CheckUserInfo>
                </DocumentTitle>
                {this.state.openRegion && <OpenRegion onSubmit={this.handleOpenRegion} onCancel={this.cancelOpenRegion}/>}
                {this.state.createTeam && <CreateTeam onOk={this.handleCreateTeam} onCancel={this.cancelCreateTeam}/>}
                {this.state.showChangePassword && <ChangePassword onOk={this.handleChangePass} onCancel={this.cancelChangePass}/>}
                <Loading/>
                {rainbondInfo.is_public && <Meiqia />}
                {this.props.payTip && <PayTip dispatch={this.props.dispatch} />}
            </Fragment>
        );
    }
}

export default connect(({user, global, loading}) => {

    return ({
        currentUser: user.currentUser,
        notifyCount: user.notifyCount,
        collapsed: global.collapsed,
        groups: global.groups,
        fetchingNotices: loading.effects['global/fetchNotices'],
        notices: global.notices,
        currTeam: globalUtil.getCurrTeamName(),
        currRegion: globalUtil.getCurrRegionName(),
        rainbondInfo: global.rainbondInfo,
        payTip: global.payTip
    })
})(BasicLayout);