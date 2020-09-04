/* eslint-disable class-methods-use-this */
/* eslint-disable default-case */
import * as d3 from 'd3';
import React from 'react';
import { connect } from 'react-redux';
import { clickBackground } from '../actions/app-actions';
import ZoomableCanvas from '../components/zoomable-canvas';
import {
  graphZoomLimitsSelector,
  graphZoomStateSelector
} from '../selectors/graph-view/zoom';
import NodesChartElements from './nodes-chart-elements';

require('../../styles/nodeStyle.css');


const EdgeMarkerDefinition = ({ selectedNodeId }) => {
  const markerOffset = selectedNodeId ? '35' : '40';
  const markerSize = selectedNodeId ? '10' : '30';
  return (
    <defs>
      <marker
        className="edge-marker"
        id="end-arrow"
        viewBox="1 0 10 10"
        refX={markerOffset}
        refY="3.5"
        markerWidth={markerSize}
        markerHeight={markerSize}
        orient="auto">
        <polygon className="link" points="0 0, 10 3.5, 0 7" />
      </marker>
    </defs>
  );
};

class NodesChart extends React.Component {
  constructor(props, context) {
    super(props, context);

    this.handleMouseClick = this.handleMouseClick.bind(this);
    this.loading = this.loading.bind(this);
  }

  handleMouseClick() {
    if (this.props.selectedNodeId) {
      this.props.clickBackground();
    }
  }


  loading() {
    // 为D3设置SVG
    const width = 960;
    const height = 500;
    const colors = d3.scaleOrdinal(d3.schemeCategory10);

    const svg = d3.select('body')
      .append('svg')
      .attr('oncontextmenu', 'return false;')
      .attr('width', width)
      .attr('height', height);

  // 设置初始节点和链接
// -节点是通过“id”知道的，而不是通过数组中的索引知道的。
// -节点上表示自反边(黑体圈)。
// -链接总是源<目标;边缘方向由“左”和“右”设置。
    const nodes = [
      { id: 0, reflexive: false },
      { id: 1, reflexive: true },
      { id: 2, reflexive: false }
    ];
    let lastNodeId = 2;
    const links = [
      { source: nodes[0], target: nodes[1], left: false, right: true },
      { source: nodes[1], target: nodes[2], left: false, right: true }
    ];

    // init D3力布局
    const force = d3.forceSimulation()
      .force('link', d3.forceLink().id(d => d.id).distance(150))
      .force('charge', d3.forceManyBody().strength(-500))
      .force('x', d3.forceX(width / 2))
      .force('y', d3.forceY(height / 2))
      .on('tick', tick);

    // init D3拖曳支持
    const drag = d3.drag()
      .on('start', (d) => {
        if (!d3.event.active) force.alphaTarget(0.3).restart();

        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (d) => {
        d.fx = d3.event.x;
        d.fy = d3.event.y;
      })
      .on('end', (d) => {
        if (!d3.event.active) force.alphaTarget(0);

        d.fx = null;
        d.fy = null;
      });

    // 为图形链接定义箭头标记
    svg.append('svg:defs').append('svg:marker')
      .attr('id', 'end-arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 6)
      .attr('markerWidth', 3)
      .attr('markerHeight', 3)
      .attr('orient', 'auto')
      .append('svg:path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#000');

    svg.append('svg:defs').append('svg:marker')
      .attr('id', 'start-arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 4)
      .attr('markerWidth', 3)
      .attr('markerHeight', 3)
      .attr('orient', 'auto')
      .append('svg:path')
      .attr('d', 'M10,-5L0,0L10,5')
      .attr('fill', '#000');

    // 拖动新节点时显示的行
    const dragLine = svg.append('svg:path')
      .attr('class', 'link dragline hidden')
      .attr('d', 'M0,0L0,0');

    // 链接和节点元素组的句柄
    let path = svg.append('svg:g').selectAll('path');
    let circle = svg.append('svg:g').selectAll('g');

    // mouse event vars鼠标事件var
    let selectedNode = null;
    let selectedLink = null;
    let mousedownLink = null;
    let mousedownNode = null;
    let mouseupNode = null;

    function resetMouseVars() {
      mousedownNode = null;
      mouseupNode = null;
      mousedownLink = null;
    }

    // update force layout (called automatically each iteration)更新力布局(每次迭代自动调用)
    function tick() {
      // 从节点中心用适当的填充绘制有向边
      path.attr('d', (d) => {
        const deltaX = d.target.x - d.source.x;
        const deltaY = d.target.y - d.source.y;
        const dist = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
        const normX = deltaX / dist;
        const normY = deltaY / dist;
        const sourcePadding = d.left ? 17 : 12;
        const targetPadding = d.right ? 17 : 12;
        const sourceX = d.source.x + (sourcePadding * normX);
        const sourceY = d.source.y + (sourcePadding * normY);
        const targetX = d.target.x - (targetPadding * normX);
        const targetY = d.target.y - (targetPadding * normY);

        return `M${sourceX},${sourceY}L${targetX},${targetY}`;
      });

      circle.attr('transform', d => `translate(${d.x},${d.y})`);
    }

    // 更新图(需要时调用)
    function restart() {
      // 路径(链接)
      path = path.data(links);

      // 更新现有的链接
      path.classed('selected', d => d === selectedLink)
        .style('marker-start', d => d.left ? 'url(#start-arrow)' : '')
        .style('marker-end', d => d.right ? 'url(#end-arrow)' : '');

      // 删除旧的链接
      path.exit().remove();

      // 添加新链接
      path = path.enter().append('svg:path')
        .attr('class', 'link')
        .classed('selected', d => d === selectedLink)
        .style('marker-start', d => d.left ? 'url(#start-arrow)' : '')
        .style('marker-end', d => d.right ? 'url(#end-arrow)' : '')
        .on('mousedown', (d) => {
          if (d3.event.ctrlKey) return;

          // select link选择链接
          mousedownLink = d;
          selectedLink = (mousedownLink === selectedLink) ? null : mousedownLink;
          selectedNode = null;
          restart();
        })
        .merge(path);

      // 循环(节点)组
      // NB:函数arg在这里很重要!节点是通过id知道的，而不是通过索引!
      circle = circle.data(nodes, d => d.id);

      // 更新现有节点(自反性和选定的视觉状态)
      circle.selectAll('circle')
        .style('fill', d => (d === selectedNode) ? d3.rgb(colors(d.id)).brighter().toString() : colors(d.id))
        .classed('reflexive', d => d.reflexive);

      // 删除旧的节点
      circle.exit().remove();

      // 添加新的节点
      const g = circle.enter().append('svg:g');

      g.append('svg:circle')
        .attr('class', 'node')
        .attr('r', 12)
        .style('fill', d => (d === selectedNode) ? d3.rgb(colors(d.id)).brighter().toString() : colors(d.id))
        .style('stroke', d => d3.rgb(colors(d.id)).darker().toString())
        .classed('reflexive', d => d.reflexive)
        .on('mouseover', function (d) {
          if (!mousedownNode || d === mousedownNode) return;
          // 扩大目标节点
          d3.select(this).attr('transform', 'scale(1.1)');
        })
        .on('mouseout', function (d) {
          if (!mousedownNode || d === mousedownNode) return;
          // unenlarge目标节点
          d3.select(this).attr('transform', '');
        })
        .on('mousedown', (d) => {
          if (d3.event.ctrlKey) return;

          // select node选择节点
          mousedownNode = d;
          selectedNode = (mousedownNode === selectedNode) ? null : mousedownNode;
          selectedLink = null;

          // reposition drag line重新定位拖行
          dragLine
            .style('marker-end', 'url(#end-arrow)')
            .classed('hidden', false)
            .attr('d', `M${mousedownNode.x},${mousedownNode.y}L${mousedownNode.x},${mousedownNode.y}`);

          restart();
        })
        .on('mouseup', function (d) {
          if (!mousedownNode) return;

          // needed by FFFF所需的
          dragLine
            .classed('hidden', true)
            .style('marker-end', '');

          // check for drag-to-self检查drag-to-self
          mouseupNode = d;
          if (mouseupNode === mousedownNode) {
            resetMouseVars();
            return;
          }

          // unenlarge target nodeunenlarge目标节点
          d3.select(this).attr('transform', '');

           // 向图形添加链接(如果存在，请更新)
          // NB:链接是严格的来源<目标;由布尔值分别指定的箭头
          const isRight = mousedownNode.id < mouseupNode.id;
          const source = isRight ? mousedownNode : mouseupNode;
          const target = isRight ? mouseupNode : mousedownNode;

          const link = links.filter(l => l.source === source && l.target === target)[0];
          if (link) {
            link[isRight ? 'right' : 'left'] = true;
          } else {
            links.push({ source, target, left: !isRight, right: isRight });
          }

          // select new link
          selectedLink = link;
          selectedNode = null;
          restart();
        });

      // show node IDs
      g.append('svg:text')
        .attr('x', 0)
        .attr('y', 4)
        .attr('class', 'id')
        .text(d => d.id);

      circle = g.merge(circle);

      // set the graph in motion
      force
        .nodes(nodes)
        .force('link').links(links);

      force.alphaTarget(0.3).restart();
    }

    function mousedown() {
      // because :active only works in WebKit?
      svg.classed('active', true);

      if (d3.event.ctrlKey || mousedownNode || mousedownLink) return;

      // insert new node at point
      const point = d3.mouse(this);
      const node = { id: ++lastNodeId, reflexive: false, x: point[0], y: point[1] };
      nodes.push(node);

      restart();
    }

    function mousemove() {
      if (!mousedownNode) return;

      // update drag line
      dragLine.attr('d', `M${mousedownNode.x},${mousedownNode.y}L${d3.mouse(this)[0]},${d3.mouse(this)[1]}`);

      restart();
    }

    function mouseup() {
      if (mousedownNode) {
        // hide drag line
        dragLine
          .classed('hidden', true)
          .style('marker-end', '');
      }

      // because :active only works in WebKit?
      svg.classed('active', false);

      // clear mouse event vars
      resetMouseVars();
    }

    function spliceLinksForNode(node) {
      const toSplice = links.filter(l => l.source === node || l.target === node);
      for (const l of toSplice) {
        links.splice(links.indexOf(l), 1);
      }
    }

    // only respond once per keydown
    let lastKeyDown = -1;

    function keydown() {
      d3.event.preventDefault();

      if (lastKeyDown !== -1) return;
      lastKeyDown = d3.event.keyCode;

      // ctrl
      if (d3.event.keyCode === 17) {
        circle.call(drag);
        svg.classed('ctrl', true);
      }

      if (!selectedNode && !selectedLink) return;

      switch (d3.event.keyCode) {
        case 8: // backspace
        case 46: // delete
          if (selectedNode) {
            nodes.splice(nodes.indexOf(selectedNode), 1);
            spliceLinksForNode(selectedNode);
          } else if (selectedLink) {
            links.splice(links.indexOf(selectedLink), 1);
          }
          selectedLink = null;
          selectedNode = null;
          restart();
          break;
        case 66: // B
          if (selectedLink) {
            // set link direction to both left and right
            selectedLink.left = true;
            selectedLink.right = true;
          }
          restart();
          break;
        case 76: // L
          if (selectedLink) {
            // set link direction to left only
            selectedLink.left = true;
            selectedLink.right = false;
          }
          restart();
          break;
        case 82: // R
          if (selectedNode) {
            // toggle node reflexivity
            selectedNode.reflexive = !selectedNode.reflexive;
          } else if (selectedLink) {
            // set link direction to right only
            selectedLink.left = false;
            selectedLink.right = true;
          }
          restart();
          break;
      }
    }

    function keyup() {
      lastKeyDown = -1;

      // ctrl
      if (d3.event.keyCode === 17) {
        circle.on('.drag', null);
        svg.classed('ctrl', false);
      }
    }

    // app starts here
    svg.on('mousedown', mousedown)
      .on('mousemove', mousemove)
      .on('mouseup', mouseup);
    d3.select(window)
      .on('keydown', keydown)
      .on('keyup', keyup);
    restart();
  }


  render() {
    const { selectedNodeId } = this.props;
    return (
      <div className="nodes-chart">
        <ZoomableCanvas
          onClick={this.handleMouseClick}
          zoomLimitsSelector={graphZoomLimitsSelector}
          zoomStateSelector={graphZoomStateSelector}
          disabled={selectedNodeId}>
          <EdgeMarkerDefinition selectedNodeId={selectedNodeId} />
          <NodesChartElements />
        </ZoomableCanvas>
      </div>
    );
  }
}


function mapStateToProps(state) {
  return {
    selectedNodeId: state.get('selectedNodeId'),
  };
}


export default connect(
  mapStateToProps,
  { clickBackground }
)(NodesChart);
