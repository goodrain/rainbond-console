import React, {Fragment} from 'react';
import {connect} from 'dva';
import globalUtil from '../utils/global';

@connect()
export default class Index extends React.PureComponent {
    componentWillMount(){
        const currTeam = globalUtil.getCurrTeamName();
        const currRegion = globalUtil.getCurrRegionName();
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
    render(){
        return (
            this.props.children
        )
    }
}