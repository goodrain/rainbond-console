import React from 'react';
import { connect } from 'react-redux';

import NodesChartEdges from './nodes-chart-edges';
import NodesChartNodes from './nodes-chart-nodes';
import { graphExceedsComplexityThreshSelector } from '../selectors/topology';
import {
  selectedScaleSelector,
  layoutNodesSelector,
  layoutEdgesSelector
} from '../selectors/graph-view/layout';
import { showEdgeContextMenu } from '../actions/app-actions';


class NodesChartElements extends React.Component {
  renderCustomEdgesVisual() {
    const { customEdges, layoutNodes, selectedEdgeId } = this.props;

    if (!customEdges || customEdges.size === 0) {
      return null;
    }

    return customEdges.map((edge, edgeId) => {
      const sourceNodeId = edge.get('source');
      const targetNodeId = edge.get('target');
      const sourceNode = layoutNodes.get(sourceNodeId);
      const targetNode = layoutNodes.get(targetNodeId);

      if (!sourceNode || !targetNode) {
        return null;
      }

      const sourceX = sourceNode.get('x');
      const sourceY = sourceNode.get('y');
      const targetX = targetNode.get('x');
      const targetY = targetNode.get('y');

      if (sourceX === undefined || sourceY === undefined ||
          targetX === undefined || targetY === undefined) {
        return null;
      }

      const path = `M${sourceX},${sourceY}L${targetX},${targetY}`;
      const isSelected = edgeId === selectedEdgeId;
      const edgeColor = isSelected ? '#FF5722' : '#2196F3';
      const edgeWidth = isSelected ? '3' : '2';

      return (
        <g key={edgeId} className="custom-edge-visual">
          <path
            d={path}
            stroke={edgeColor}
            strokeWidth={edgeWidth}
            fill="none"
            pointerEvents="none"
          />
          {isSelected && (
            <g>
              <circle
                cx={sourceX}
                cy={sourceY}
                r="4"
                fill={edgeColor}
                pointerEvents="none"
              />
              <circle
                cx={targetX}
                cy={targetY}
                r="4"
                fill={edgeColor}
                pointerEvents="none"
              />
            </g>
          )}
        </g>
      );
    }).toArray();
  }

  renderCustomEdgesInteractive() {
    const { customEdges, layoutNodes, onEdgeContextMenu } = this.props;


    if (!customEdges || customEdges.size === 0) {
      return null;
    }


    return customEdges.map((edge, edgeId) => {
      const sourceNodeId = edge.get('source');
      const targetNodeId = edge.get('target');
      const sourceNode = layoutNodes.get(sourceNodeId);
      const targetNode = layoutNodes.get(targetNodeId);

      if (!sourceNode || !targetNode) {
        return null;
      }

      const sourceX = sourceNode.get('x');
      const sourceY = sourceNode.get('y');
      const targetX = targetNode.get('x');
      const targetY = targetNode.get('y');

      if (sourceX === undefined || sourceY === undefined ||
          targetX === undefined || targetY === undefined) {
        return null;
      }

      const path = `M${sourceX},${sourceY}L${targetX},${targetY}`;


      return (
        <path
          key={edgeId}
          className="custom-edge-interactive"
          d={path}
          stroke="transparent"
          strokeWidth="20"
          fill="none"
          style={{ cursor: 'pointer' }}
          onContextMenu={(e) => {
            e.preventDefault();
            e.stopPropagation();
            // 直接使用页面坐标,不需要转换
            const position = {
              x: e.clientX,
              y: e.clientY
            };
            onEdgeContextMenu(edgeId, position);
          }}
        />
      );
    }).toArray();
  }

  render() {
    const { layoutNodes, layoutEdges, selectedScale, isAnimated } = this.props;
    return (
      <g className="nodes-chart-elements">
        <NodesChartEdges
          layoutEdges={layoutEdges}
          selectedScale={selectedScale}
          isAnimated={isAnimated} />
        {this.renderCustomEdgesVisual()}
        <NodesChartNodes
          layoutNodes={layoutNodes}
          selectedScale={selectedScale}
          isAnimated={isAnimated} />
        {this.renderCustomEdgesInteractive()}
      </g>
    );
  }
}


function mapStateToProps(state) {
  return {
    layoutNodes: layoutNodesSelector(state),
    layoutEdges: layoutEdgesSelector(state),
    selectedScale: selectedScaleSelector(state),
    isAnimated: !graphExceedsComplexityThreshSelector(state),
    customEdges: state.get('customEdges'),
    selectedEdgeId: state.get('selectedEdgeId')
  };
}

function mapDispatchToProps(dispatch) {
  return {
    onEdgeContextMenu: (edgeId, position) => {
      dispatch(showEdgeContextMenu(edgeId, position));
    }
  };
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(NodesChartElements);
