import React, {Fragment} from 'react';
import userUtil from '../utils/user';
import globalUtil from '../utils/global';
import cookie from '../utils/cookie';
import {connect} from 'dva';
import {Route, Redirect, Switch, routerRedux} from 'dva/router';
import OpenRegion from '../components/OpenRegion';
import { notification } from 'antd';
import WelcomeAndCreateTeam from '../components/WelcomeAndCreateTeam'
var msg = ''
/* 检查用户信息, 包括检测团队和数据中心信息等 */
@connect()
export default class CheckUserInfo extends React.PureComponent {
    constructor(props){
        super(props);
        this.state = {
            
        }
    }
    componentDidMount = () => {
        
    }
    toDefaultTeam = () => {
        console.log('to default team')
        const user = this.props.userInfo;
        let team = userUtil.getDefaultTeam(user);
        //当前团队里没有数据中心
        var currRegion = team.region[0]? team.region[0].team_region_name : 'no-region';
        this
        .props
        .dispatch(routerRedux.replace(`/team/${team.team_name}/region/${currRegion}/index`));
        
    }
    //判断当前用户有没有团队
    hasTeam = () => {
        const currentUser = this.props.userInfo;
        if(!currentUser.teams || !currentUser.teams.length){
            return false;
        }
        return true;
    }
    //验证当前团队里是否已经开通了数据中心
    currTeamHasRegion = () => {
        const user = this.props.userInfo;
        const currTeam = globalUtil.getCurrTeamName();
        //判断当前团队里是否有数据中心
        var currTeamObj = userUtil.getTeamByTeamName(user, currTeam);
        if(currTeamObj && (!currTeamObj.region || !currTeamObj.region.length)){
            return false;
        }
        return true;
    }
    //验证url里的团队和数据中心是否有效
    checkUrlTeamRegion = () => {
        const user = this.props.userInfo;
        var currTeam = globalUtil.getCurrTeamName();
        var currRegion = globalUtil.getCurrRegionName();

       

        //没有数据中心放行，在后续页面做处理
        if(currRegion === 'no-region'){
            return true;
        }

        //url里没有team
        if(!currTeam || !currRegion){
           
            currTeam = cookie.get('team');
            currRegion = cookie.get('region_name');
            if(currTeam && currRegion){
                this
                .props
                .dispatch(routerRedux.replace(`/team/${currTeam}/region/${currRegion}/index`));
            }else{
                this.toDefaultTeam();
            }
            return false;
        }

        

        //如果当前用户没有该团队, 并且是系统管理员
        if(!userUtil.getTeamByTeamName(user, currTeam)){
            if((userUtil.isSystemAdmin(user) || currTeam === 'grdemo')){
                this.props.dispatch({
                    type: 'user/getTeamByName',
                    payload: {
                        team_name: currTeam
                    },
                    callback: (team) => {
                    },
                    fail: () => {
                        this.toDefaultTeam();
                    }
                })
            }else{
                this.toDefaultTeam();
            }
            
            return false;
        }

        //判断当前团队是否有数据中心
        let team = userUtil.getTeamByTeamName(user, currTeam);
        if(!team.region || !team.region.length){
            this
            .props
            .dispatch(routerRedux.replace(`/team/${currTeam}/region/no-region/index`));
            return false;
        }

        //判断当前浏览的数据中心是否在要访问的团队里
        var region = team.region.filter((region) => {
              return region.team_region_name === currRegion;
        })
        if(!region.length){
            this.toDefaultTeam();
            return false;
        }
        cookie.set('team', currTeam);
        cookie.set('region_name', currRegion);
        return true;
    }

    render(){
        const user = this.props.userInfo;
        const rainbondInfo = this.props.rainbondInfo;
        if(!user || !rainbondInfo) return null;

        if(!this.hasTeam()){
            return <WelcomeAndCreateTeam rainbondInfo={rainbondInfo} onOk={this.props.onInitTeamOk} />;
        }
        if(!this.checkUrlTeamRegion()){
            return null;
        }

        
        return (
            this.props.children
        )
    }
}