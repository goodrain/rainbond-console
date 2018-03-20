import React, {PureComponent, Fragment} from 'react';
import moment from 'moment';
import {Table, Alert, Badge, Divider} from 'antd';
import teamUtil from '../../utils/team';

const statusMap = ['default', 'processing', 'success', 'error'];
class TeamMemberTable extends PureComponent {
  state = {
    selectedRowKeys: [],
    totalCallNo: 0
  };

  componentWillReceiveProps(nextProps) {}

  handleTableChange = (pagination, filters, sorter) => {
    this
      .props
      .onChange(pagination, filters, sorter);
  }

  render() {
    const {selectedRowKeys, totalCallNo} = this.state;
    const {
      list,
      pagination,
      onDelete,
      onEditAction,
      onMoveTeam,
      team
    } = this.props;

    const columns = [
      {
        title: '用户名',
        dataIndex: 'user_name'
      }, {
        title: '邮箱',
        dataIndex: 'email'
      }, {
        title: '权限',
        dataIndex: 'identity',
        render(val) {
          return <span>{teamUtil.actionToCN(val)}</span>
        }
      }, {
        title: '操作',
        dataIndex: 'action',
        render(val, data) {
          return <div>
            {teamUtil.canDeleteMember(team) && <a
              href="javascript:;"
              onClick={() => {
              onDelete(data)
            }}>删除</a>
}

            {teamUtil.canEditMemberAction(team) && <a
              style={{
              marginLeft: 6
            }}
              onClick={() => {
              onEditAction(data)
            }}
              href="javascript:;">编辑权限</a>
}

            {teamUtil.canChangeOwner(team) && <a
              style={{
              marginLeft: 6
            }}
              onClick={() => {
              onMoveTeam(data)
            }}
              href="javascript:;">移交团队</a>
}

          </div>

        }
      }
    ];

    return (<Table
      pagination={pagination}
      dataSource={list}
      columns={columns}
      onChange={this.handleTableChange}/>);
  }
}

export default TeamMemberTable;
