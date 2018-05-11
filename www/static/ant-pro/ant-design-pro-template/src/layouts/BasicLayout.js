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

//美洽 
class Meiqia extends React.PureComponent {
    componentDidMount(){
        (function(m, ei, q, i, a, j, s) {
            m[a] = m[a] || function() {
                (m[a].a = m[a].a || []).push(arguments)
          };
            j = ei.createElement(q),
                s = ei.getElementsByTagName(q)[0];
            j.async = true;
            j.charset = 'UTF-8';
            j.src = i;
            s.parentNode.insertBefore(j, s)
        })(window, document, 'script', '//eco-api.meiqia.com/dist/meiqia.js', '_MEIQIA');
        _MEIQIA('entId', 5732);
    }
    render(){
        return null;
    }
}

//提示充值
class PayTip extends React.PureComponent {
    handleCancel = () => {
        this.props.dispatch({
            type: 'global/hidePayTip'
        })
    }
    handleClick = () => {
        window.open('https://www.goodrain.com/spa/#/personalCenter/my/recharge')
        this.handleCancel();
    }
    getRegionId = () => {
        var regionName = globalUtil.getCurrRegionName();
        let regionId = '';
        if(regionName == 'ali-hz') {
        regionId = 2;
        }
        if(regionName == 'ali-sh'){
        regionId = 1;
        }
        return regionId;
    }
    handleBuySource = () => {
        const regionId = this.getRegionId();
        if(regionId){
            window.open(`https://www.goodrain.com/spa/#/resBuy/${regionId}`)
        }else{
            notification.warning({message: '当前数据中心不可购买'})
        }
        this.handleCancel();
    }
    componentDidMount(){
    }
    render(){
        const regionId = this.getRegionId();
        return <Modal
            visible={true}
            title="提示"
            onCancel={this.handleCancel}
            footer={[regionId ? <Button onClick={this.handleBuySource} type="primary" size="sm">购买资源</Button> : null, 
            <Button onClick={this.handleClick} size="sm">账户充值</Button>]}
        >
             <h4 style={{textAlign: 'center'}}>资源及企业账户余额不足</h4>
        </Modal>;
    }
}

class NoTeamTip extends React.PureComponent {
    componentDidMount(){
        Modal.warning({
            title: '您还没有团队，无法使用云帮',
            content: '请联系管理人员'
        })
    }
    render(){
        return null;
    }
}


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
        showChangePassword: false
    };
    onOpenRegion = () => {
        this.setState({openRegion: true})
    }
    cancelOpenRegion = () => {
        this.setState({openRegion: false})
    }
    handleOpenRegion = (regions) => {
        const team_name = globalUtil.getCurrTeamName();
        this
            .props
            .dispatch({
                type: 'teamControl/openRegion',
                payload: {
                    team_name: team_name,
                    region_names: regions.join(',')
                },
                callback: () => {
                    notification.success({message: `开通成功`});
                    this.cancelOpenRegion();
                    this
                        .props
                        .dispatch({type: 'user/fetchCurrent'});

                }
            })
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
    componentDidMount() {
        enquireScreen((mobile) => {
            this.setState({isMobile: mobile});
        });
        this.fetchUserInfo();
    }
    fetchUserInfo = () => {
        //获取用户信息、保存团队和数据中心信息
        this
            .props
            .dispatch({
                type: 'user/fetchCurrent',
                callback: (user) => {
                    var currTeam = globalUtil.getCurrTeamName();
                    var currRegion = globalUtil.getCurrRegionName();

                    //验证路径里的团队是否有效
                    if (!currTeam || !currRegion) {
                        if (!currTeam) {
                            let cookieTeam = cookie.get('team');
                            if(cookieTeam){
                                currTeam = cookieTeam;
                            }else{
                                let team = userUtil.getDefaultTeam(user);
                                if (team) {
                                    currTeam = team.team_name
                                }
                            }
                            

                        }
                        if (!currRegion) {
                            let cookieRegion = cookie.get('region_name');
                            if(cookieRegion){
                                currRegion = cookieRegion;
                            }else{
                                let region = userUtil.getDefaultRegionName(user);
                                if (region) {
                                    currRegion = region;
                                }
                            }
                            
                        }
                        this
                            .props
                            .dispatch(routerRedux.replace(`/team/${currTeam}/region/${currRegion}/index`));
                        location.reload();
                        return;
                    }

                    var commCode = () => {
                        
                        

                        //如果没有当前团队和数据中心
                        if(!userUtil.hasTeamAndRegion(user, currTeam, currRegion)){
                            let team = userUtil.getDefaultTeam(user);
                            if (team) {
                                currTeam = team.team_name
                            }
                            let region = userUtil.getDefaultRegionName(user);
                            if (region) {
                                currRegion = region;
                            }
                            this
                                .props
                                .dispatch(routerRedux.replace(`/team/${currTeam}/region/${currRegion}/index`));
                            location.reload();
                            return;
                        }
                        cookie.set('team', currTeam);
                        cookie.set('region_name', currRegion);
                        //获取群组
                        this
                            .props
                            .dispatch({
                                type: 'global/fetchGroups',
                                payload: {
                                    team_name: currTeam,
                                    region_name: currRegion
                                }
                            });

                        this
                            .props
                            .dispatch({
                                type: 'global/saveCurrTeamAndRegion',
                                payload: {
                                    currTeam: currTeam,
                                    currRegion: currRegion
                                }
                            })
                        //获取当前数据中心的协议
                        this.props.dispatch({
                            type: 'region/fetchProtocols',
                            payload: {
                                team_name: currTeam,
                                region_name: currRegion
                            }
                        })
                    }


                    //如果当前用户没有该团队, 并且是系统管理员
                    if(!userUtil.getTeamByTeamName(user, currTeam) && (userUtil.isSystemAdmin(user) || currTeam === 'grdemo')){
                        this.props.dispatch({
                            type: 'user/getTeamByName',
                            payload: {
                                team_name: currTeam
                            },
                            callback: (team) => {
                                commCode();
                            },
                            fail: () => {
                                commCode();
                            }
                        })
                    }else{
                        commCode();
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
        const {routerData, location} = this.props;
        const {pathname} = location;
        let title = '好雨云帮 | 应用一键部署';
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
    isInited = () => {

        const currTeam = this.props.currTeam;
        const currRegion = this.props.currRegion;
        const currentUser = this.props.currentUser;
        const rainbondInfo = this.props.rainbondInfo;
        const groups = this.props.groups;

        //还没有加载完用户信息
        if (!rainbondInfo || !currentUser || !currTeam || !currRegion || !groups) {
            return false;
        }

        var load = document.getElementById('load');
        if (load) {
            document
                .body
                .removeChild(load);
        }

        return true;
    }
    handleNoticeVisibleChange = (visible) => {
        if (visible) {
            this
                .props
                .dispatch({type: 'global/fetchNotices'});
        }
    }
    checkTeamAndRegion = () => {
        var currTeam = globalUtil.getCurrTeamName();
        var currRegion = globalUtil.getCurrRegionName();
        var user = this.props.currentUser;
        //判断当前url上的团队和数据中心是在在用户的信息里
        if(!userUtil.getTeamByTeamName(user, currTeam) || !userUtil.hasTeamAndRegion(user, currTeam, currRegion)){
            location.href = "/";
            return false;
        }
        return true;
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
    checkHasTeam = () => {
        const currentUser = this.props.currentUser;
        if(!currentUser.teams || !currentUser.teams.length){
           
            return false;
        }
        return true;
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

        if (!this.isInited()) {
            return null;
        }

        if(!this.checkHasTeam()){
            return <NoTeamTip />;
        }

        if(!this.checkTeamAndRegion()){
            return null;
        }

        const region = userUtil.hasTeamAndRegion(currentUser, currTeam, currRegion) || {};
        const isRegionMaintain = region.region_status === '3';

        const layout = (
            <Layout>
                {
                    isRegionMaintain ? null :
                    <SiderMenu currentUser={currentUser} logo={logo} // 不带Authorized参数的情况下如果没有权限,会强制跳到403界面
                    // If you do not have the Authorized parameter
                    // you will be forced to jump to the 403 interface without permission
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
                        
                        {
                            !isRegionMaintain ? 
                            <Switch>
                                {redirectData.map(item => <Redirect key={item.from} exact from={item.from} to={item.to}/>)
    }
                                {getRoutes(match.path, routerData).map(item => {
                                    return (<AuthorizedRoute
                                        key={item.key}
                                        path={item.path}
                                        component={item.component}
                                        exact={item.exact}
                                        authority={item.authority}
                                        logined={true}
                                        redirectPath={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/exception/403`} />)
                                })
    }

                                <Redirect exact from="/" to={bashRedirect}/>
                                <Route render={NotFound}/>
                            </Switch>
                            :
                            <div style={{textAlign: 'center', padding: '50px 0'}}>
                               <Icon style={{fontSize: 50, marginBottom: 32}} type="warning" />
                               <h1 style={{fontSize: 50, color: 'rgba(0, 0, 0, 0.65)', marginBottom: 8}}>数据中心维护中</h1>
                               <p>请稍后访问当前数据中心</p>
                            </div>
                        }
                        
                    </Content>
                    <GlobalFooter
                        links={[
                        {
                            key: 'Pro 首页',
                            title: 'Pro 首页',
                            href: 'http://pro.ant.design',
                            blankTarget: true
                        }, {
                            key: 'github',
                            title: <Icon type="github"/>,
                            href: 'https://github.com/ant-design/ant-design-pro',
                            blankTarget: true
                        }, {
                            key: 'Ant Design',
                            title: 'Ant Design',
                            href: 'http://ant.design',
                            blankTarget: true
                        }
                    ]}
                        copyright={< div > Copyright < Icon type = "copyright" /> 2018 蚂蚁金服体验技术部出品 < /div>}/>
                </Layout>
            </Layout>
        );

        return (
            <Fragment>
                <DocumentTitle title={this.getPageTitle()}>
                    <ContainerQuery query={query}>
                        {params => <div className={classNames(params)}>{layout}</div>}
                    </ContainerQuery>
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
        currTeam: global.currTeam,
        currRegion: global.currRegion,
        rainbondInfo: global.rainbondInfo,
        payTip: global.payTip
    })
})(BasicLayout);