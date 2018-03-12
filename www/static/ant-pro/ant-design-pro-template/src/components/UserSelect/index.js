import React, { PureComponent, Fragment } from 'react';
import { search } from  '../../services/user';
import { Select, Form, Spin } from 'antd';
import debounce from 'lodash.debounce';
const Option = Select.Option;


class UserRemoteSelect extends React.Component {
  constructor(props) {
    super(props);
    this.lastFetchId = 0;
    this.fetchUser = debounce(this.fetchUser, 800);
    this.state = {
  	    data: [],
  	    value: [],
  	    fetching: false
  	}
  }
  
  fetchUser = (value) => {
  	
    this.lastFetchId += 1;
    const fetchId = this.lastFetchId;
    this.setState({ data: [], fetching: true });
    search({key: value}).then((response)=>{
    	if(response){
	    	 var data = response.list || [];
	       this.setState({ data: data, fetching: false });
	    }
    })
  }
  handleChange = (value) => {

    this.setState({
      value,
      fetching: false,
    });
    this.props.onChange && this.props.onChange(value)
  }
  render() {
    const { fetching, data, value, members } = this.state;
    return (
      <Select
        mode="multiple"
        labelInValue
        value={value}
        placeholder="输入用户名称进行搜索"
        notFoundContent={fetching ? <Spin size="small" /> : null}
        filterOption={false}
        onSearch={this.fetchUser}
        onChange={this.handleChange}
        style={{ width: '100%' }}
      >
        {data.map(d => <Option key={d.user_id}>{d.nick_name}</Option>)}
      </Select>
    );
  }
}

export default UserRemoteSelect;