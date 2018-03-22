import React, {PureComponent, Fragment} from 'react';
import debounce from 'lodash.debounce';
import globalUtil from '../../utils/global';
import {connect} from 'dva';
import {routerRedux} from 'dva/router';
import config from '../../config/config'

@connect()
class Index extends React.Component {
  constructor(props) {
    super(props);
  }
  componentDidMount(){
  
  }
  componentWillMount() {
    const team_name = globalUtil.getCurrTeamName();
    const groupId = this.props.group_id;
    var self = this;
    try {

      window.iframeGetNodeUrl = function () {
        return config.baseUrl + '/console/teams/' + team_name + '/topological?group_id=' + groupId+'&region='+globalUtil.getCurrRegionName();
      }

      window.iframeGetMonitor = function (fn) {
        self.props.dispatch({
            type: 'groupControl/groupMonitorData',
            payload: {
              team_name: globalUtil.getCurrTeamName(),
              group_id: groupId
            },
            callback: (data) => {
              fn && fn(data || {})
            }
        })

        return config.baseUrl + '/console/teams/' + team_name + '/topological?group_id=' + groupId+'&region='+globalUtil.getCurrRegionName();
      }

      window.iframeGetTenantName = function () {
        return team_name;
      }

      window.iframeGetRegion = function () {
        return globalUtil.getCurrRegionName();
      }

      window.iframeGetGroupId = function () {
        return groupId;
      }

      //拓扑图点击服务事件
      window.handleClickService = function (nodeDetails) {
        self
          .props
          .dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/app/${nodeDetails.service_alias}/overview`))
      }

      //拓扑图点击依赖服务事件
      window.handleClickRelation = function (relation) {
        self
          .props
          .dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/app/${relation.service_alias}/overview`))
      }

    } catch (e) {}
  }
  render() {
    return ((
      <iframe
        src={config.baseUrl + '/static/www/weavescope/index.html'}
        style={{
        width: '100%',
        height: '500px'
      }}
        frameborder="no"
        border="0"
        marginwidth="0"
        marginheight="0"></iframe>
    ));
  }
}

export default Index;