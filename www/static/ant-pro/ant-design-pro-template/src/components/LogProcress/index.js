import React, { PureComponent, Fragment } from 'react';
import moment from 'moment';
import { connect } from 'dva';
import { Link } from 'dva/router';
import { Card, Button, Table, notification, Badge } from 'antd';
import LogSocket from '../../utils/logSocket';
import domUtil from '../../utils/dom-util';

export default class Index extends PureComponent {
	constructor(props){
		super(props);
		this.state = {
			datas: []
		}
		this.socketUrl = this.props.socketUrl;
		this.eventId = this.props.eventId;
		this.idMap = {

		}
	}
	findProgressById = (id) => {
		const datas = this.state.datas;
		const d = datas.filter((data) => {
			return data.message.id === id
		})[0];
		return d;
	}
	createTmpElement(){
		this.ele = document.createElement('p');
		this.ele.style.marginBottom = 0
	}
	componentDidMount(){
		const resover = this.props.resover;
		this.createTmpElement();
		this.socket = new LogSocket({
			eventId: this.eventId,
			url: this.socketUrl,
			onClose: () => {
		    	this.props.onClose && this.props.onClose()
		  	},
		  	onSuccess: (data) => {
		    	this.props.onSuccess && this.props.onSuccess(data)
			},
			onTimeout: (data) => {
				this.props.onTimeout && this.props.onTimeout(data)
			},
		  	onFail:  (data) =>{
		    	this.props.onFail && this.props.onFail(data)
		  	},
			onMessage: (data) => {
				var ele = this.ele.cloneNode();
				try{
					if(this.ref){
						data.message = JSON.parse(data.message);
						var msg = data.message;
						ele.innerHTML = this.getItemHtml(data);
						if(msg.id){
							const dom = this.idMap[msg.id]
							if(dom){
								this.ref.replaceChild(ele, dom);
								
							}else{
								domUtil.prependChild(this.ref, ele);
							}
							this.idMap[msg.id] = ele;
						}else{
							domUtil.prependChild(this.ref, ele);
						}
					}
				}catch(e){
					ele.innerHTML = this.getItemHtml(data);
					domUtil.prependChild(this.ref, ele);
					console.log(e)

				}
			},
			onComplete: () => {
				this.props.onComplete && this.props.onComplete()
			}
		})
	}
	componentWillUnmount(){
		if(this.socket){
			this.socket.close();
			this.socket = null;
		}
		this.state.datas = [];
		this.idMap = {};
	}

	getItemHtml = (data) => {

		if(typeof data.message === 'string'){
			var msg = data.message;
			return `<span className="time" style="margin-right: 8px">${moment(data.time).format("HH:mm:ss")}</span><span>${msg||''}</span>`
		}else{
			try{
				const message = data.message;
				var msg = '';
				if(message.id){
					msg += message.id+':'
				}
				msg += (message.status||'');
				msg += (message.progress||'');
				if(data.step != 'build-progress'){
					return `<span className="time" style="margin-right: 8px">${moment(data.time).format("HH:mm:ss")}</span><span>${msg||''}</span>`
				}else{
					return `<span className="time" style="margin-right: 8px">${moment(data.time).format("HH:mm:ss")}</span><span>${message.stream}</span>`
				}
			}catch(e){
				return '';
			}
		}
	}
	saveRef = (ref) => {
		this.ref = ref;
	}
	render(){
		const datas = this.state.datas || [];

		return (

			<div style={{maxHeight: 300, overflowY: 'auto'}} ref={this.saveRef}>

			</div>
		)
	}
}
