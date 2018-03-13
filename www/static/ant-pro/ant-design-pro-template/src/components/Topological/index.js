import React, {PureComponent, Fragment} from 'react';
import debounce from 'lodash.debounce';
import globalUtil from '../../utils/global';
import {connect} from 'dva';
import {routerRedux} from 'dva/router';

@connect()
class Index extends React.Component {
  constructor(props) {
    super(props);
  }
  componentWillMount() {
    const team_name = globalUtil.getCurrTeamName();
    const groupId = this.props.group_id;
    var self = this;
    try {

      window.iframeGetNodeUrl = function () {
        return '/console/teams/' + team_name + '/topological?group_id=' + groupId;
      }

      window.iframeGetTenantName = function () {
        return team_name;
      }

      window.iframeGetGroupId = function () {
        return groupId;
      }

      //拓扑图点击服务事件
      window.handleClickService = function (nodeDetails) {
        self
          .props
          .dispatch(routerRedux.push("/app/" + nodeDetails.service_alias + "/overview"))
      }

      //拓扑图点击依赖服务事件
      window.handleClickRelation = function (relation) {
        self
          .props
          .dispatch(routerRedux.push("/app/" + relation.service_alias + "/overview"))
      }

    } catch (e) {}
  }
  render() {
    return ((
      <iframe
        src='/static/www/weavescope/index.html'
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