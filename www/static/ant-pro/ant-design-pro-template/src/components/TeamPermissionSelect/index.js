import React, { PureComponent, Fragment } from 'react';
import {  Radio } from 'antd';
import debounce from 'lodash.debounce';
const RadioGroup = Radio.Group;


class UserRemoteSelect extends React.Component {
  constructor(props) {
    super(props);
  }
  render() {
    const { options, value, onChange } = this.props;
    const ops = (options || []).map((item) => {
        return {
           label: item.name,
           value: item.key
        }
    })
    return (
      <RadioGroup options={ops} defaultValue={value || ''} onChange={onChange} />
    );
  }
}

export default UserRemoteSelect;