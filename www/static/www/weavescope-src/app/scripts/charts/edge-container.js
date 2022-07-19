import React from 'react';
import { Motion, spring } from 'react-motion';
import { Map as makeMap } from 'immutable';
import { line, curveBasis } from 'd3-shape';
import { each, omit, times, constant } from 'lodash';

import { NODES_SPRING_ANIMATION_CONFIG } from '../constants/animation';
import { EDGE_WAYPOINTS_CAP } from '../constants/styles';
import Edge from './edge';


const spline = line()
  .curve(curveBasis)
  .x(d => d.x)
  .y(d => d.y);

const transformedEdge = (props, path, target) => (
  <Edge {...props} target={target} points={path}  path={spline(path)} />
);

// Converts a waypoints map of the format { x0: 11, y0: 22, x1: 33, y1: 44 }
// that is used by Motion to an array of waypoints in the format
// [{ x: 11, y: 22 }, { x: 33, y: 44 }] that can be used by D3.
const waypointsMapToArray = (waypointsMap) => {
  const waypointsArray = times(EDGE_WAYPOINTS_CAP, () => ({}));
  each(waypointsMap, (value, key) => {
    const [axis, index] = [key[0], key.slice(1)];
    waypointsArray[index][axis] = value;
  });
  return waypointsArray;
};

// Converts a waypoints array of the input format [{ x: 11, y: 22 }, { x: 33, y: 44 }]
// to an array of waypoints that is used by Motion in the format { x0: 11, y0: 22, x1: 33, y1: 44 }.
const waypointsArrayToMap = (waypointsArray) => {
  let waypointsMap = makeMap();
  waypointsArray.forEach((point, index) => {
    waypointsMap = waypointsMap.set(`x${index}`, spring(point.x, NODES_SPRING_ANIMATION_CONFIG));
    waypointsMap = waypointsMap.set(`y${index}`, spring(point.y, NODES_SPRING_ANIMATION_CONFIG));
  });
  return waypointsMap;
};


export default class EdgeContainer extends React.PureComponent {
  constructor(props, context) {
    super(props, context);
    this.state = { waypointsMap: makeMap() };
  }

  componentWillMount() {
    if (this.props.isAnimated) {
      this.prepareWaypointsForMotion(this.props.waypoints);
    }
  }

  componentWillReceiveProps(nextProps) {
    // immutablejs allows us to `===`! \o/
    if (this.props.isAnimated && nextProps.waypoints !== this.props.waypoints) {
      this.prepareWaypointsForMotion(nextProps.waypoints);
    }
  }

  render() {
    const { isAnimated, waypoints, target } = this.props;
    const forwardedProps = omit(this.props, 'isAnimated', 'waypoints');
    if (!isAnimated) {
      return transformedEdge(forwardedProps, waypoints.toJS(), target);
    }

    return (
      // For the Motion interpolation to work, the waypoints need to be in a map format like
      // { x0: 11, y0: 22, x1: 33, y1: 44 } that we convert to the array format when rendering.
      <Motion style={this.state.waypointsMap.toJS()}>
        {interpolated => transformedEdge(forwardedProps, waypointsMapToArray(interpolated), target)}
      </Motion>
    );
  }

  prepareWaypointsForMotion(waypoints) {
    waypoints = waypoints.toJS();

    // The Motion library requires the number of waypoints to be constant, so we fill in for
    // the missing ones by reusing the edge source point, which doesn't affect the edge shape
    // because of how the curveBasis interpolation is done.
    const waypointsMissing = EDGE_WAYPOINTS_CAP - waypoints.length;
    if (waypointsMissing > 0) {
      waypoints = times(waypointsMissing, constant(waypoints[0])).concat(waypoints);
    }

    this.setState({ waypointsMap: waypointsArrayToMap(waypoints) });
  }
}
