import React, {PureComponent, Fragment} from 'react';
import { Button, Icon, Card, Modal, Form, Input, Select } from 'antd';
import { connect } from 'dva';
import globalUtil from '../../utils/global';

@connect()
export default class ShowKeyModal extends PureComponent {
  constructor(props){
    super(props);
    this.state = {
      key: ''
    }
  }
  componentDidMount(){
      const team_name = globalUtil.getCurrTeamName();
      const region_name = globalUtil.getCurrRegionName();
      this.props.dispatch({
        type: 'teamControl/getRegionKey',
        payload: {
           team_name,
           region_name
        },
        callback: (data) => {
           this.setState({key: data.public_key})
        }
      })
  }
  render(){
    const { onCancel } = this.props;
    return (
      <Modal
        title="配置授权Key"
        visible={true}
        onCancel={onCancel}
        footer={[<Button onClick={onCancel}>已授权</Button>]}
      >
        <p><Icon type="info-circle-o" /> 请拷贝如下Key到您的私有Git仓库进行授权，云帮平台方可访问您的私有Git仓库</p>
        <p style={{border: '1px dotted #dcdcdc', padding: '20px', wordWrap: 'break-word', wordBreak: 'normal' }}>
          {this.state.key || '加载中...'}
        </p>
      </Modal>
    )
  }
}