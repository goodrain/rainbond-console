import React from 'react';
import { connect } from 'react-redux';
import NodesChart from '../charts/nodes-chart';
import {
  isGraphViewModeSelector,
  isResourceViewModeSelector, isTableViewModeSelector
} from '../selectors/topology';
import { isTopologyEmpty } from '../utils/topology-utils';


class Nodes extends React.Component {
  render() {
    const { isGraphViewMode } = this.props;
    return (
      <div className="nodes-wrapper">
        {isGraphViewMode && <NodesChart />}
      </div>
    );
  }
}


function mapStateToProps(state) {
  return {
    isGraphViewMode: isGraphViewModeSelector(state),
    isTableViewMode: isTableViewModeSelector(state),
    isResourceViewMode: isResourceViewModeSelector(state),
    currentTopology: state.get('currentTopology'),
    nodesLoaded: state.get('nodesLoaded'),
    topologies: state.get('topologies'),
    topologiesLoaded: state.get('topologiesLoaded'),
    topologyEmpty: isTopologyEmpty(state),
  };
}


export default connect(
  mapStateToProps
)(Nodes);
