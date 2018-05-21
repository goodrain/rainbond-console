import React, {PureComponent, Fragment} from 'react';
import moment from 'moment';
import {Table, Alert, Badge, Divider, Tag} from 'antd';
import teamUtil from '../../utils/team';
import roleUtil from '../../utils/role';


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
      onEdit,
      team
    } = this.props;

    const columns = [
      {
        title: '角色名称',
        dataIndex: 'role_name'
      }, {
        title: '权限',
        dataIndex: 'role_perm',
        width: '60%',
        render(val) {
          val = val ||[];
          var category = {}, i=0;
          for(;i<val.length;i++){
            if(!category[val[i].group_name]){
              category[val[i].group_name] = [val[i]]
            }else{
              category[val[i].group_name].push(val[i])
            }
          }
          var keys = Object.keys(category);

          return <div>
            {keys.map((name) => {
                return <dl>
                    <dt>{name}</dt>
                    <dd>{
                    (category[name] || []).map((item)=>{
                          return <Tag>{item.perm_info}</Tag>
                      })
                  }</dd>
                  </dl>
            })}
          </div>
        }
      }, {
        title: '操作',
        dataIndex: 'action',
        render(val, data) {
          return <div>
            

            {(!data.is_default && teamUtil.canEditRole(team)) &&  <a
              style={{
              marginRight: 8
            }}
              onClick={() => {
              onEdit(data)
            }}
              href="javascript:;">修改</a>
}
            {(!data.is_default && teamUtil.canDelRole(team))  && <a
              href="javascript:;"
              onClick={() => {
              onDelete(data)
            }}>删除</a>
}

          </div>

        }
      }
    ];

    return (<Table
      pagination={pagination}
      dataSource={list}
      columns={columns}
      />);
  }
}

export default TeamMemberTable;
