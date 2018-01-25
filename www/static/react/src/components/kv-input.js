import React, { Component } from 'react';
import { Form, Checkbox, Row, Col, Select, Input, Button } from 'antd';
import { connect } from 'react-redux';

let uuid = 0;
class KvInput extends Component {
	constructor(props) {
		super(props);
		this.state = {
			values: [{key:'', value:''}]
		}
		this.initFromProps();
	}
	add = () => {
		var values = this.state.values;
		this.setState({values: values.concat({key:'', value:''})})
	}
	componentWillReceiveProps(nextProps) {
	    if ('value' in nextProps) {
	      const value = nextProps.value;
	      this.initFromProps(value);
	    }
	}

	initFromProps(value) {
		var value =value || this.props.value;
		if(value) {
			var res = [];
			var valArr = value.split('&');
			for(var i =0;i<valArr.length;i++){
				res.push({key: valArr[i].split('=')[0], value: valArr[i].split('=')[1]});
			}
			this.setValues(res);
		}
	}
	setValues(arr){
		arr = arr ||[];
		if(!arr.length) {arr.push({key:'', value:''})};
		this.setState({values: arr});
	}
	remove = (index) => {
		var values = this.state.values;
		values.splice(index, 1);
		this.setValues(values);
		this.triggerChange(values);
	}
	triggerChange(values){
		var res = [];
		for(var i=0;i<values.length;i++){

			res.push(values[i].key + '=' + values[i].value);
			
			
		}
		var onChange = this.props.onChange;
		onChange && onChange(res.join('&'));
	}
	onKeyChange =(index, e) => {
		var values = this.state.values;
		values[index].key = e.target.value;
		this.triggerChange(values);
		this.setValues(values);
		
	}
	onValueChange = (index, e) => {
		var values = this.state.values;
		values[index].value = e.target.value;
		this.triggerChange(values);
		this.setValues(values);
	}
	render() {
		const keyPlaceholder = this.props.keyPlaceholder || '请输入key值';
		const valuePlaceholder = this.props.valuePlaceholder || '请输入value值';
		const values = this.state.values;
		return (
			<div>
				{
					values.map((item, index) => {
						 uuid++;
						 return (<Row key={index}>
							      <Col span={8}><Input name="key" onChange={this.onKeyChange.bind(this, index)} value={item.key} placeholder={keyPlaceholder} /></Col>
							      <Col span={2} style={{textAlign: 'center'}}>=</Col>
							      <Col span={8}><Input name="value" onChange={this.onValueChange.bind(this, index)} value={item.value} placeholder={valuePlaceholder} /></Col>
							      <Col span={6} style={{textAlign: 'center'}}>
							      	  {index == 0 ? <Button onClick={this.add} type="primary">添加</Button> : <Button onClick={this.remove.bind(this, index)}>删除</Button>}
							      </Col>
							   </Row>)
					})
				}
			</div>
		)
	}
}


export default KvInput;
