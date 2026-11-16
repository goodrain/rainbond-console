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


function NodeShape(shapeType, shapeElement, shapeProps, { id, highlighted, color, metric, isVirtualMachine }) {
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
          transform="translate(33 -33) scale(1.2)"
          style={{ pointerEvents: 'none' }}
          role="img"
          aria-label="Virtual machine (VM)"
        >
          <title>Virtual machine (VM)</title>
          <rect x="-21" y="-10" width="42" height="24" rx="7" fill="#182b4d" fillOpacity="0.16" />
          <rect x="-21" y="-12" width="42" height="24" rx="7" fill="#155eef" stroke="#fff" strokeWidth="1.6" />
          <g transform="translate(-13 -5)" fill="none" stroke="#fff" strokeWidth="1.2" strokeLinecap="round">
            <rect width="8" height="10" rx="1.5" />
            <path d="M2.5 3.5h3M2.5 6.5h3" />
          </g>
          <text x="6" y="0" style={{ fill: '#fff', fontSize: '12px', fontFamily: 'Arial, sans-serif',
            letterSpacing: '0.3px', textAnchor: 'middle', dominantBaseline: 'central', transform: 'none' }} fontWeight="700">VM</text>
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
