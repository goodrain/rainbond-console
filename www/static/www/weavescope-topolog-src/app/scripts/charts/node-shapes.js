import React from 'react';
import classNames from 'classnames';

import { NODE_BASE_SIZE } from '../constants/styles';
import {
  getMetricValue,
  getMetricColor,
  getClipPathDefinition,
} from '../utils/metric-utils';
import {
  pathElement,
  circleElement,
  rectangleElement,
  cloudShapeProps,
  circleShapeProps,
  squareShapeProps,
  hexagonShapeProps,
  heptagonShapeProps,
} from '../utils/node-shape-utils';


function NodeShape(shapeType, shapeElement, shapeProps, { id, highlighted, color, metric, isVirtualMachine, markerColor }) {
  const { height, hasMetric, formattedValue } = getMetricValue(metric);
  const className = classNames('shape', `shape-${shapeType}`, { metrics: hasMetric });
  const metricStyle = { fill: getMetricColor(metric) };
  const clipId = `metric-clip-${id}`;

  return (
    <g className={className}>
      {highlighted && shapeElement({
        className: 'highlight-border',
        transform: `scale(${NODE_BASE_SIZE * 0.5})`,
        ...shapeProps,
      })}
      {highlighted && shapeElement({
        className: 'highlight-shadow',
        transform: `scale(${NODE_BASE_SIZE * 0.5})`,
        ...shapeProps,
      })}
      {shapeElement({
        className: 'background',
        transform: `scale(${NODE_BASE_SIZE * 0.48})`,
        ...shapeProps,
      })}
      {hasMetric && getClipPathDefinition(clipId, height, 0.48)}
      {hasMetric && shapeElement({
        className: 'metric-fill',
        transform: `scale(${NODE_BASE_SIZE * 0.48})`,
        clipPath: `url(#${clipId})`,
        style: metricStyle,
        ...shapeProps,
      })}
      {shapeElement({
        className: 'shadow',
        transform: `scale(${NODE_BASE_SIZE * 0.49})`,
        ...shapeProps,
      })}
      {shapeElement({
        className: 'border',
        transform: `scale(${NODE_BASE_SIZE * 0.5})`,
        stroke: color,
        ...shapeProps,
      })}
      {hasMetric && highlighted ?
        <text>{formattedValue}</text> :
        <circle className="node" r={NODE_BASE_SIZE * 0.1} />
      }
      {isVirtualMachine && (
        <g
          className="virtual-machine-badge"
          transform="translate(31 -32) scale(0.65)"
          style={{ pointerEvents: 'none' }}
          role="img"
          aria-label="Virtual machine (VM)"
        >
          <title>Virtual machine (VM)</title>
          <rect className="background" x="-17" y="-10" width="34" height="20" rx="6" />
          <rect
            x="-17"
            y="-10"
            width="34"
            height="20"
            rx="6"
            fill={markerColor}
            fillOpacity="0.14"
            stroke={markerColor}
            strokeOpacity="0.5"
            strokeWidth="1.5"
          />
          <text x="0" y="0" style={{ fill: markerColor }} fontWeight="600">VM</text>
        </g>
      )}
    </g>
  );
}

export const NodeShapeCloud = props => NodeShape('cloud', pathElement, cloudShapeProps, props);
export const NodeShapeCircle = props => NodeShape('circle', circleElement, circleShapeProps, props);
export const NodeShapeHexagon = props => NodeShape('hexagon', pathElement, hexagonShapeProps, props);
export const NodeShapeHeptagon = props => NodeShape('heptagon', pathElement, heptagonShapeProps, props);
export const NodeShapeSquare = props => NodeShape('square', rectangleElement, squareShapeProps, props);
