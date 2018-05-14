import React, { PureComponent, Fragment } from 'react';
import {  Tag, Button } from 'antd';
const CheckableTag = Tag.CheckableTag;


class Index extends React.Component {
  constructor(props) {
    super(props);
    const value = this.props.value;
    this.state = {
        selected:value || []
    }
  }
  componentDidMount(){
    const onChange = this.props.onChange;
    onChange && onChange(this.state.selected.join(','))
  }
  handleSelectAll = () => {
      const datas = this.props.datas;
      const onChange = this.props.onChange;
      const ids = datas.map((item) => {
          return item.id;
      })
      this.setState({selected: ids}, () => {
        onChange && onChange(this.state.selected.join(','))
      })
  }
  handleUnSelectAll = () => {
    const datas = this.props.datas;
    const onChange = this.props.onChange;
    const ids = datas.filter((item) => {
        return this.state.selected.indexOf(item.id) === -1;
    }).map((item)=>{
        return item.id
    })
    this.setState({selected: ids}, () => {
      onChange && onChange(this.state.selected.join(','))
    })
  }
  handleChange = (item, value) => {
    const onChange = this.props.onChange;
    const id = item.id;
    if(value){
        this.setState({selected: this.state.selected.concat([id])}, ()=>{
            onChange && onChange(this.state.selected.join(','))
        })
    }else{
        var v = this.state.selected.filter((item=>{
            return item !== id;
        }))
        
        this.setState({selected: v}, ()=>{
            onChange && onChange(this.state.selected.join(','))
        })
    }
  }
  render() {
    const { datas, value, onChange } = this.props;
    return (
      <div>
         <Button size="small" onClick={this.handleSelectAll} style={{marginRight: 8}}>全选</Button><Button  onClick={this.handleUnSelectAll} size="small">反选</Button>
         <div></div>
         {datas.map((item)=>{
             return <CheckableTag
              key={item.id}
              checked={this.state.selected.indexOf(item.id)>-1}
              onChange={(value)=>{this.handleChange(item, value)}}
              >
              {item.info}
              </CheckableTag>
         })}
      </div>
    );
  }
}

export default Index;