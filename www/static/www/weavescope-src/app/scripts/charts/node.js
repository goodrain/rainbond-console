import classnames from "classnames";
import { List as makeList, Map as makeMap } from "immutable";
import React from "react";
import { connect } from "react-redux";
import { clickNode, enterNode, leaveNode } from "../actions/app-actions";
import MatchedResults from "../components/matched-results";
import MatchedText from "../components/matched-text";
import { NODE_BASE_SIZE } from "../constants/styles";
import { getStatusColor } from "../utils/color-utils";
import NodeNetworksOverlay from "./node-networks-overlay";
import NodeShapeStack from "./node-shape-stack";
import {
  NodeShapeCircle,
  NodeShapeCloud,
  NodeShapeHeptagon,
  NodeShapeHexagon,
  NodeShapeSquare,
} from "./node-shapes";

const labelWidth = 1.2 * NODE_BASE_SIZE;
const nodeShapes = {
  circle: NodeShapeCircle,
  hexagon: NodeShapeHexagon,
  heptagon: NodeShapeHeptagon,
  square: NodeShapeSquare,
  cloud: NodeShapeCloud,
};

function stackedShape(Shape, stackNum) {
  const factory = React.createFactory(NodeShapeStack);
  return (props) =>
    factory(Object.assign({}, props, { shape: Shape, stackNum }));
}

function getNodeShape({ shape, stack, stackNum }) {
  const nodeShape = nodeShapes[shape];
  if (!nodeShape) {
    throw new Error(`Unknown shape: ${shape}!`);
  }
  return stack ? stackedShape(nodeShape, stackNum) : nodeShape;
}

class Node extends React.Component {
  constructor(props, context) {
    super(props, context);
    this.state = {
      hovered: false,
    };

    this.handleMouseClick = this.handleMouseClick.bind(this);
    this.handleMouseEnter = this.handleMouseEnter.bind(this);
    this.handleMouseLeave = this.handleMouseLeave.bind(this);
    this.saveShapeRef = this.saveShapeRef.bind(this);
  }

  renderSvgLabels(labelClassName, labelMinorClassName, labelOffsetY) {
    const { label, labelMinor } = this.props;
    return (
      <g className="node-labels-container">
        <text
          className={labelClassName}
          y={13 + labelOffsetY}
          textAnchor="middle"
        >
          {label}
        </text>
        <text
          className={labelMinorClassName}
          y={30 + labelOffsetY}
          textAnchor="middle"
        >
          {labelMinor}
        </text>
      </g>
    );
  }

  renderStandardLabels(
    labelClassName,
    labelMinorClassName,
    labelOffsetY,
    mouseEvents
  ) {
    const { label, labelMinor, matches = makeMap() } = this.props;
    const matchedMetadata = matches.get("metadata", makeList());
    const matchedParents = matches.get("parents", makeList());
    const matchedNodeDetails = matchedMetadata.concat(matchedParents);

    return (
      <foreignObject
        className="node-labels-container"
        y={labelOffsetY}
        x={-0.5 * labelWidth}
        width={labelWidth}
        height="5em"
      >
        <div className="node-label-wrapper" {...mouseEvents}>
          <div className={labelClassName}>
            <MatchedText text={label} match={matches.get("label")} />
          </div>
          <div className={labelMinorClassName}>
            <MatchedText text={labelMinor} match={matches.get("labelMinor")} />
          </div>
          <MatchedResults matches={matchedNodeDetails} />
        </div>
      </foreignObject>
    );
  }

  render() {
    const {
      focused,
      highlighted,
      networks,
      pseudo,
      rank,
      label,
      transform,
      exportingGraph,
      showingNetworks,
      stack,
      id,
      metric,
      appNodes,
    } = this.props;
    const { hovered } = this.state;

    const color = getStatusColor(rank);
    const truncate = !focused && !hovered;
    const labelOffsetY = showingNetworks && networks ? 40 : 28;

    const nodeClassName = classnames("node", { highlighted, hovered, pseudo });
    const labelClassName = classnames("node-label", { truncate });
    const labelMinorClassName = classnames("node-label-minor", { truncate });

    const NodeShapeType = getNodeShape(this.props);
    const mouseEvents = {
      onClick: this.handleMouseClick,
      onMouseEnter: this.handleMouseEnter,
      onMouseLeave: this.handleMouseLeave,
    };
    return (
      <g className={nodeClassName} transform={transform}>
        {exportingGraph
          ? this.renderSvgLabels(
              labelClassName,
              labelMinorClassName,
              labelOffsetY
            )
          : this.renderStandardLabels(
              labelClassName,
              labelMinorClassName,
              labelOffsetY,
              mouseEvents
            )}

        <g
          {...mouseEvents}
          ref={this.saveShapeRef}
          style={{ pointerEvents: 'bounding-box' }}
        >
          <NodeShapeType
            id={id}
            highlighted={highlighted}
            color={color}
            metric={metric}
            contrastMode={this.props.contrastMode}
          />
        </g>

        {showingNetworks && (
          <NodeNetworksOverlay networks={networks} stack={stack} />
        )}
      </g>
    );
  }

  saveShapeRef(ref) {
    this.shapeRef = ref;
  }

  handleMouseClick(ev) { 
    console.log(ev);
    ev.stopPropagation();
    this.props.clickNode(
      this.props.id,
      this.props.label,
      this.shapeRef.getBoundingClientRect(),
      this.props.serviceAlias
    );
  }

  handleMouseEnter() {
    this.props.enterNode(this.props.id);
    this.setState({ hovered: true });
  }

  handleMouseLeave() {
    this.props.leaveNode(this.props.id);
    this.setState({ hovered: false });
  }
}

function mapStateToProps(state) {
  return {
    exportingGraph: state.get("exportingGraph"),
    showingNetworks: state.get("showingNetworks"),
    currentTopology: state.get("currentTopology"),
    contrastMode: state.get("contrastMode"),
    appNodes:state.get('appNodes')
  };
}

export default connect(mapStateToProps, { clickNode, enterNode, leaveNode })(
  Node
);
