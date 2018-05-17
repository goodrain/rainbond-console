import React, { PureComponent, Fragment } from 'react';
import {  Tag, Button, Radio } from 'antd';
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
  handleSelectAll = (group_name) => {
      
      var ids = this.getGroupPerm(group_name).map((item) => {
           return item.id;
      })
      const onChange = this.props.onChange;
      ids = ids.filter((id)=>{
         return this.state.selected.indexOf(id) === -1;
      })
      this.setState({selected: this.state.selected.concat(ids)}, () => {
        onChange && onChange(this.state.selected.join(','))
      })
  }
  isInGroup = (permId, group_name) => {
    var datas = this.props.datas.filter((item)=>{
        return item.group_name === group_name;
    })[0];
    if(!datas) return false;
    datas = (datas.perms_info||[]).map((perm)=>{
        return perm.id
    });
    return datas.indexOf(permId) > -1;
  }
  getGroupPerm = (group_name) => {
    
    var datas = this.props.datas;
    var curr = datas.filter((item) => {
         return item.group_name === group_name;
    })[0];
   
    if(curr){
        return curr.perms_info || []
    }
    return []
  }
  handleUnSelectAll = (group_name) => {

   var ids =  this.state.selected.filter((id) => {
        return !this.isInGroup(id, group_name)
   })

    const onChange = this.props.onChange;
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
    const hides = this.props.hides || [];
    return (
      <div>
         {
             datas.map((item) => {
                if(hides.indexOf(item.group_name) > -1) return null
                if(!item.perms_info.length) return null;
                return <dl>
                    <dt>{this.props.showGroupName !== false ? item.group_name: ''} <Button style={{marginLeft: 16}} size="small" onClick={()=>{this.handleSelectAll(item.group_name)}} style={{marginRight: 8}}>全选</Button><Button  onClick={()=>{this.handleUnSelectAll(item.group_name)}} size="small">取消全选</Button></dt>
                    <dd>
                        {
                            item.perms_info.map((item)=>{
                                return <CheckableTag
                                    key={item.id}
                                    checked={this.state.selected.indexOf(item.id)>-1}
                                    onChange={(value)=>{this.handleChange(item, value, )}}
                                    >
                                    {item.info}
                                    </CheckableTag>
                            })
                        }
                    </dd>
                    
                </dl>
             })
         }
      </div>
    );
  }
}

export default Index;