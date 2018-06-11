import React from 'react';
import { connect } from 'react-redux';
import classNames from 'classnames';
import { enterEdge, leaveEdge, setMonitorData } from '../actions/app-actions';
import { NODE_BASE_SIZE } from '../constants/styles';


class Points extends React.Component {
     constructor(arg){
       super(arg);
       this.saveRef = this.saveRef.bind(this);
       this.points = [];
       this.count = 0;
       this.state = {
         show: false
       }

        var monitor = this.props.monitor || {};
        this.maxTime = 0;
        this.minTime = 1000000;
        this.maxRequest = 0;
        this.minRequest = 10000;
        this.time = this.props.data.response_time;
        this.request = this.props.data.throughput_rate;

        for(var i = 0;i <monitor.length; i++){
          var item = monitor[i].data;
          if(item.response_time > this.maxTime){
              this.maxTime = item.response_time;
          }

          if(item.response_time > 0 && item.response_time < this.minTime){
              this.minTime = item.response_time;
          }

          if(item.throughput_rate > this.maxRequest){
              this.maxRequest = item.throughput_rate;
          }

          if(item.throughput_rate > 0 && item.throughput_rate < this.minRequest){
              this.minRequest = item.throughput_rate;
          }
        }

        this.middleTime =this.minTime + (this.maxTime - this.minTime)/2;
        this.middleRequest =this.minRequest + (this.maxRequest - this.minRequest)/2;
        this.vdist = 300;
     }
     getCount(){
         var count = 3;
         var arr = [];
         for(var i=0;i<count;i++){
          arr[i] = 1;
         }
         return arr;
     }
     removeAllPoint(){
         for(var i=0;i<this.points.length;i++){
            
            this.points[i].circle.parentNode.removeChild(this.points[i].circle);
     
         }
         this.points = []
     }
     removePoint(){
        var time = +new Date();
        for(var i=0;i<this.points.length;i++){
             var t = +this.points[i].circle.getAttribute('time');
             if(time - t > 1000 * 25){
                if(this.points[i].circle.parentNode){
                    this.points[i].circle.parentNode.removeChild(this.points[i].circle);
                    this.points.splice(i,1);
                    i--;
                }
                
             }
        }
     }
     addPoint(){
        if(!this.mounted) return;
        if(this.ref){
            this.count++;
            var circle =  document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            var path = this.props.path;
            circle.setAttribute('cx', 0);
            circle.setAttribute('cy', 0);
            circle.setAttribute('r', 5);
            circle.setAttribute('time', new Date().getTime());
            circle.style="stroke:none;fill:rgba(51, 153, 51, 0.5);";
        
            var animate = document.createElementNS('http://www.w3.org/2000/svg', 'animateMotion');
            animate.setAttribute('path', path);
            animate.setAttribute('dur', this.getTime()+'s')

            this.points.push({
                circle: circle,
                animate: animate
            })
            this.ref.appendChild(circle);
            circle.appendChild(animate);
            animate.beginElement();
            setTimeout(() => {
                this.addPoint();
                this.removePoint();
            }, this.getDelayTime());
         }
     }
     componentDidMount(){
         this.mounted = true;
         setTimeout(()=> {
            this.setState({show: true}, ()=>{
                this.addPoint();
                this.getNodeData();
            })
         },3000)
     }
     componentWillUnmount(){
         this.mounted = false;
         this.removeAllPoint();
     }
     //根据距离，速度计算时间
     getTime(){
        var points = this.props.points || [];
        const data = this.props.data;
        if(points.length>1){
             var startPoint = points[0];
             var endPoint = points[points.length-1]
             var dist = Math.sqrt((endPoint.x-startPoint.x) * (endPoint.x-startPoint.x) + (endPoint.y-startPoint.y) * (endPoint.y-startPoint.y) )
             var cumputedDist = dist/this.vdist;
             return (5*(this.time/this.middleTime) * cumputedDist)+1.5;
        }
        return 5;
     }
     getDelayTime(index){
        var points = this.props.points || [];
        var startPoint = points[0];
        var endPoint = points[points.length-1]
        var long = Math.sqrt((endPoint.x-startPoint.x) * (endPoint.x-startPoint.x) + (endPoint.y-startPoint.y) * (endPoint.y-startPoint.y) )
        var time = this.getTime()*1000;
        var dist = 80;
        var cRequest = this.middleRequest/this.request;
        var cDist = cRequest * dist;
        var r = cDist/long*time;

        if(r>5000){
           r = 5000;
        }

        if(r < 200){
           r=200
        }

        return r;
     }
     saveRef(ref){
        this.ref = ref;
     }
     getNodeData(){
         var target = this.props.target;
         var nodes = this.props.nodes;
         if(nodes){
            nodes = nodes.toJSON();
            for(var k in nodes){
                if(k === target){
                   return nodes[k]
                }
            }
         }
     }
     render(){
         var count = this.getCount() || [];
         var path = this.props.path;

         if(!this.state.show){
            return null;
         }

         return (
            <g ref={this.saveRef}>

            </g>
          )
     }
}



class Edge extends React.Component {

  constructor(props, context) {
    super(props, context);
    this.handleMouseEnter = this.handleMouseEnter.bind(this);
    this.handleMouseLeave = this.handleMouseLeave.bind(this);
    this.saveRef = this.saveRef.bind(this);
    this.state = {
      showData: false,
      x:0,
      y:0
    }
  }
  getMonitorData() {
    const target = this.props.target;
    const source = this.props.source;
    const monitor = this.props.nodeMonitorData.toJSON()||[];
    monitor.push({
        data:{
          response_time: 2,
          throughput_rate: 6000
        },
        source: '应用运行中',
        target: '监控数据'
    })
    var monitorData = monitor.filter((item)=>{
       if(item.is_web){
          item.source = 'The Internet';
       }
       return item.source === source && item.target === target;
    })[0];
    console.log(monitorData)
    return monitorData ? monitorData.data : null
  }
  saveRef(ref) {
      this.ref = ref;
      if(this.ref){
        var total = ref.getTotalLength();
        var point = ref.getPointAtLength(Math.ceil(total/2));
        this.setState({x: point.x, y: point.y})
      }
  }

  render() {
    const {
      id,
      path,
      highlighted,
      blurred,
      focused,
      scale,
      source,
      target,
      points
    } = this.props;
    const className = classNames('edge', { highlighted, blurred, focused });
    const thickness = (scale * 0.01) * NODE_BASE_SIZE;
    const strokeWidth = focused ? thickness * 3 : thickness;
    const shouldRenderMarker = (focused || highlighted) && (source !== target);
    const selectedNodeId = this.props.selectedNodeId
    const nodes = this.props.nodes.toJSON();
    const nodeData = nodes[target];

    // Draws the edge so that its thickness reflects the zoom scale.
    // Edge shadow is always made 10x thicker than the edge itself.
    
    var monitor = this.props.nodeMonitorData.toJSON()||[];
    var monitorData = this.getMonitorData();
    return (
      <g
        id={id} className={className}
        onMouseEnter={this.handleMouseEnter}
        onMouseLeave={this.handleMouseLeave}
      >
        {
          nodeData && nodeData.lineTip && <foreignObject
              className="node-labels-container"
              y={this.state.y}
              x={this.state.x}
              width={300}
              >
              <span style={{borderRadius: '6px',  border:'1px solid #dedece', padding: '10px 20px', zIndex: 9999, background: '#fff'}}>{nodeData.lineTip}</span>
          </foreignObject>
        }
        
        <path className="shadow" d={path} style={{ strokeWidth: 10 * strokeWidth }} />
        <path
          ref={this.saveRef}
          className="link"
          d={path}
          markerEnd={shouldRenderMarker ? 'url(#end-arrow)' : null}
          style={{ strokeWidth }}
        />
        {(!selectedNodeId && monitorData && monitorData.throughput_rate) && <Points monitor={monitor} data={monitorData} target={target} nodes={this.props.nodes} points={points} path={path} />}
      </g>
    );
  }

  handleMouseEnter(ev) {
    var rect = document.querySelector('.zoom-content').getBoundingClientRect();
    var dispatch = this.props.dispatch;
    const monitorData = this.getMonitorData();
    this.props.enterEdge(ev.currentTarget.id);
    monitorData && monitorData.throughput_rate && dispatch(setMonitorData({left: ev.clientX, top: ev.clientY, data: monitorData}));
  }

  handleMouseLeave(ev) {
    this.props.leaveEdge(ev.currentTarget.id);
    var dispatch = this.props.dispatch;
    dispatch(setMonitorData(null));
  }
}

function mapStateToProps(state) {
  return {
    contrastMode: state.get('contrastMode'),
    selectedNodeId: state.get('selectedNodeId'),
    nodes: state.get('nodes'),
    nodeMonitorData: state.get('nodeMonitorData')
  };
}

export default connect(
  mapStateToProps,
  { enterEdge, leaveEdge }
)(Edge);
