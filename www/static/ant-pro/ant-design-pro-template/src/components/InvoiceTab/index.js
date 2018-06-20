import React, {PureComponent} from 'react';
import {connect} from 'dva';
import {Link, Switch, Route, routerRedux} from 'dva/router';
import {
		Row,
		Col,
		Card,
		Form,
		Button,
		Icon,
		Menu,
		Dropdown,
		notification,
		Select,
		Input,
		Modal,
    message,
    Table
} from 'antd';
import globalUtil from '../../utils/global';



@connect(({user, global}) => ({groups: global.groups}), null, null, {withRef: true})
@Form.create()
export default class Index extends PureComponent {
		constructor(props) {
			super(props);
			this.state = {
				filetab:this.props.data
			}
		}
	
		render() {
      const columns = [{
        title: '好雨用户',
        dataIndex: 'time',
      }, {
        title: '好雨企业',
        dataIndex: 'type',
      }, {
        title: '订单号',
        dataIndex: 'company',
      },
      {
        title: '储值金额',
        dataIndex: 'money',
      },{
        title: '储值方式',
        dataIndex: 'content',
      },{
        title: '第三方流水号',
        dataIndex: 'zt',
      },{
        title: '订单时间',
        dataIndex: 'bh',
      }];
			return (
				<Modal
					visible={true}
					onCancel={this.props.onCancel}
					onOk={this.props.onOk}
          title="发票订单详情"
          width={1000}
					>
					<Table dataSource={this.props.data} columns={columns} />
				</Modal>
			)
		}
}