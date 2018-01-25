import React, {Component} from 'react';
import {Icon} from 'antd';

class Bundle extends Component {
  state = {
    // short for "module" but that's a keyword in js, so "mod"
    mod: null
  }

  componentWillMount() {
    this.load(this.props)
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.load !== this.props.load) {
      this.load(nextProps)
    }
  }

  load(props) {
    this.setState({
      mod: null
    })
    props.load((mod) => {
      this.setState({
        mod: mod.default ? mod.default : mod
      })
    })
  }

  render() {
  	 var Com = this.props.children(this.state.mod);
    return Com
  }
}

/*
  延时组件，参数为 bundle 模块类型
*/
const lazyController = (compoent) => {
  return  (props) => {
      return <Bundle load={compoent}>
        {(Com) => {
          return Com ? <Com {...props} /> : <Icon style={{fontSize: '70px', position:'absolute', width: 50, height: 50, top: '50%', left: '50%', marginTop: -25, marginLeft: -25}} type="loading" />
        }}
      </Bundle>
  }

}

export default lazyController;