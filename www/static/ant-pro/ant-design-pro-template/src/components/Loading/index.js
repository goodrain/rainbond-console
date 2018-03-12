import React, {Component, PureComponent, Fragment } from 'react';  
import { connect } from 'dva';
import { Progress } from 'antd';

@connect(({ global }) => ({
  apploadingnum: global.apploadingnum
}), null, null, {pure:false})
export default class Loading extends Component {
	constructor(props) {
		super(props);
		this.width = 0;
		this.timer = null;
		this.total = 0;
		this.loaded = 0;
        this.state = {
            width: 0,
            show: false
        }
	}
	getCurrentWidth(){
        var totalWidth = 100, pWidth = 0;
        this.state.width += (totalWidth - this.state.width) * 0.01;
        return this.state.width > 90 ? 90 : this.state.width;
    }
    componentWillReceiveProps(nextprops){
    	var apploadingnum = this.props.apploadingnum;
    	var nextApploadingnum = nextprops.apploadingnum;

    	if(apploadingnum !== nextApploadingnum){

    		if(nextApploadingnum>0){
    			this.start();
    			this.computedWidth();
    		}else if(nextApploadingnum === 0){
    			this.completed();
    		}
    	}
    }
    start(){
    	if(!this.timer){
            this.setState({width: 0, show: true});
	        this.computedWidth();
	        this.timer = setInterval(() => {
	            this.computedWidth();
	        }, this.props.interval || 800);
    	}
       
    }
    computedWidth(){
        var width = this.getCurrentWidth();
        this.setState({width: width})
    }
    addRequest(){
        if(!this.timer){
            this.start();
        }else{
            this.computedWidth();
        }
    }
    removeRequest(){
        this.loaded ++;
        if(this.total == this.loaded){
            this.completed();
        }else{
            this.computedWidth();
        }
    }
    completed(){
        var self = this;
        this.total = this.loaded = 0;
        this.setState({width: 100}, ()=>{
            setTimeout(()=>{
                 this.setState({show: false}, ()=>{
                     this.setState({width:0})
                 })
            }, 500)
        })
        clearInterval(this.timer);
        this.timer = null;
    }
    saveRef = (ref) => {
    	this.element = ref;
    }
	render() {
		return (
			<div ref={this.saveRef} className="loadingbar" style={{display:this.state.show ? 'block': 'none',zIndex:9999999,height:"3px",position:"fixed",left:0,top:-10,width:'100%'}}>
			  <Progress status="active"  size="small"  percent={this.state.width} />
            </div>
		)
	}
}


