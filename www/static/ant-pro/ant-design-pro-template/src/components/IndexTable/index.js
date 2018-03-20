import React, { PureComponent, Fragment } from 'react';
import moment from 'moment';
import { Link } from 'dva/router';
import { Table, Alert, Badge, Divider } from 'antd';
import appUtil from '../../utils/app';
import styles from './index.less';
import globalUtil from '../../utils/global';

const statusMap = ['default', 'processing', 'success', 'error'];
class StandardTable extends PureComponent {
  state = {
    selectedRowKeys: [],
    totalCallNo: 0,
  };

  componentWillReceiveProps(nextProps) {
  
  }

  handleTableChange = (pagination, filters, sorter) => {
    this.props.onChange(pagination, filters, sorter);
  }



  render() {
    const { selectedRowKeys, totalCallNo } = this.state;
    const { list, pagination, status } = this.props;

    

    const columns = [
      {
        title: '应用名称',
        dataIndex: 'service_cname',
        render: (val, data) => {
            return <Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/app/${data.service_alias}/overview`}>{val}</Link>
        }
      },
      {
        title: '应用组',
        dataIndex: 'group_name',

        render: (val,data) => {
            return val=== null ? <Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/groups/-1`}>未分组</Link> : <Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/groups/${data.group_id}`}>{val}</Link>
        }
      },
      {
        title: '内存',
        dataIndex: 'min_memory',
        width: 150,
        render: val => {
            return (!val ? '0' : val) + 'MB'
        }
      },
      {
        title: '状态',
        width: 150,
        dataIndex: 'status_cn',
        render(val, data) {
          return <Badge status={appUtil.appStatusToBadgeStatus(data.status)} text={val} />;
        },
      }
    ];

    const paginationProps = {
      ...pagination,
    };

    return (
      <div className={styles.standardTable}>
        <Table
          dataSource={list}
          columns={columns}
          pagination={paginationProps}
          onChange={this.handleTableChange}
        />
      </div>
    );
  }
}

export default StandardTable;
