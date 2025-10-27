import React from 'react';
import { connect } from 'react-redux';
import { layoutNodesSelector } from '../selectors/graph-view/layout';
import '../../font/iconfont.css';

class EdgeCreateOverlay extends React.Component {
  renderPlusIcons() {
    const { layoutNodes, sourceNodeId, isCreating } = this.props;

    if (!isCreating || !layoutNodes || layoutNodes.size === 0) {
      return null;
    }

    return layoutNodes.map((node, nodeId) => {
      if (nodeId === sourceNodeId) {
        return null;
      }

      const x = node.get('x');
      const y = node.get('y');

      if (x === undefined || y === undefined) {
        return null;
      }

      return (
        <g key={nodeId} transform={`translate(${x},${y-10})`} pointerEvents="none">
          {/* 外层光晕效果 */}
          <circle
            r="25"
            fill="rgba(76, 175, 80, 0.15)"
            stroke="none"
          >
            <animate
              attributeName="r"
              values="25;30;25"
              dur="2s"
              repeatCount="indefinite"
            />
            <animate
              attributeName="opacity"
              values="0.3;0.6;0.3"
              dur="2s"
              repeatCount="indefinite"
            />
          </circle>
          {/* 中层光晕 */}
          <circle
            r="20"
            fill="rgba(76, 175, 80, 0.25)"
            stroke="none"
          >
            <animate
              attributeName="r"
              values="20;23;20"
              dur="1.5s"
              repeatCount="indefinite"
            />
          </circle>
          {/* 主圆形背景 */}
          <circle
            r="18"
            fill="rgba(255, 255, 255, 0.98)"
            stroke="#4CAF50"
            strokeWidth="3"
            filter="url(#drop-shadow)"
          />
          {/* iconfont 连线图标 */}
          <foreignObject
            x="-12"
            y="-12"
            width="24"
            height="24"
            style={{overflow: 'visible'}}
          >
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '24px',
              height: '24px',
              fontSize: '20px',
              color: '#4CAF50',
              pointerEvents: 'none'
            }}>
              <i className="iconfont icon-jiahao"></i>
            </div>
          </foreignObject>
        </g>
      );
    }).toArray();
  }

  render() {
    const { isCreating, sourcePosition, currentMousePosition } = this.props;

    if (!isCreating) {
      return null;
    }

    const sourceX = sourcePosition.get('x');
    const sourceY = sourcePosition.get('y');
    const targetX = currentMousePosition.get('x');
    const targetY = currentMousePosition.get('y');

    return (
      <g className="edge-create-overlay">
        <line
          x1={sourceX}
          y1={sourceY}
          x2={targetX}
          y2={targetY}
          stroke="#4CAF50"
          strokeWidth="2"
          strokeDasharray="5,5"
          pointerEvents="none"
        />
        <circle
          cx={sourceX}
          cy={sourceY}
          r="5"
          fill="#4CAF50"
          pointerEvents="none"
        />
        {this.renderPlusIcons()}
      </g>
    );
  }
}

function mapStateToProps(state) {
  const edgeCreation = state.get('edgeCreation');
  return {
    isCreating: edgeCreation.get('isCreating'),
    sourceNodeId: edgeCreation.get('sourceNodeId'),
    sourcePosition: edgeCreation.get('sourcePosition'),
    currentMousePosition: edgeCreation.get('currentMousePosition'),
    layoutNodes: layoutNodesSelector(state)
  };
}

export default connect(mapStateToProps)(EdgeCreateOverlay);
