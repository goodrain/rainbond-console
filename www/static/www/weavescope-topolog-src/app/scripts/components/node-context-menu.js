import React from 'react';
import { connect } from 'react-redux';
import { hideNodeContextMenu, startEdgeCreate, clickCloseDetails } from '../actions/app-actions';
import '../../font/iconfont.css';

class NodeContextMenu extends React.Component {
  constructor(props) {
    super(props);
    this.handleCreateEdge = this.handleCreateEdge.bind(this);
    this.handleTerminal = this.handleTerminal.bind(this);
    this.handleVisit = this.handleVisit.bind(this);
    this.handleBuild = this.handleBuild.bind(this);
    this.handleUpdate = this.handleUpdate.bind(this);
    this.handleStart = this.handleStart.bind(this);
    this.handleStop = this.handleStop.bind(this);
    this.handleDelete = this.handleDelete.bind(this);
    this.handleOutsideClick = this.handleOutsideClick.bind(this);
  }

  getNodeDetails() {
    const { nodeId, nodes } = this.props;

    if (!nodes) {
      return null;
    }

    const nodesObj = nodes.toJSON();
    const nodeData = nodesObj[nodeId];

    return nodeData || null;
  }

  handleCreateEdge() {
    const { nodeId, position, onStartEdgeCreate, onHideMenu } = this.props;
    onHideMenu();
    onStartEdgeCreate(nodeId, position);
  }

  handleTerminal() {
    const { onHideMenu } = this.props;
    const nodeDetails = this.getNodeDetails();
    onHideMenu();
    window.parent && window.parent.handleClickTerminal && window.parent.handleClickTerminal(nodeDetails);
  }

  handleVisit() {
    const { onHideMenu } = this.props;
    const nodeDetails = this.getNodeDetails();
    onHideMenu();
    window.parent && window.parent.handleClickVisit && window.parent.handleClickVisit(nodeDetails);
  }

  handleBuild() {
    const { onHideMenu } = this.props;
    const nodeDetails = this.getNodeDetails();
    onHideMenu();
    window.parent && window.parent.handleClickBuild && window.parent.handleClickBuild('build', nodeDetails);
  }

  handleUpdate() {
    const { onHideMenu } = this.props;
    const nodeDetails = this.getNodeDetails();
    onHideMenu();
    window.parent && window.parent.handleClickUpdate && window.parent.handleClickUpdate('update', nodeDetails);
  }

  handleStart() {
    const { onHideMenu } = this.props;
    const nodeDetails = this.getNodeDetails();
    onHideMenu();
    window.parent && window.parent.handleClickStart && window.parent.handleClickStart('start', nodeDetails);
  }

  handleStop() {
    const { onHideMenu } = this.props;
    const nodeDetails = this.getNodeDetails();
    onHideMenu();
    window.parent && window.parent.handleClickCloses && window.parent.handleClickCloses('closes', nodeDetails);
  }

  handleDelete() {
    const { onHideMenu } = this.props;
    const nodeDetails = this.getNodeDetails();
    onHideMenu();
    window.parent && window.parent.handleClickDelete && window.parent.handleClickDelete('deleteApp', nodeDetails);
  }

  componentDidMount() {
    document.addEventListener('click', this.handleOutsideClick);
  }

  componentWillUnmount() {
    document.removeEventListener('click', this.handleOutsideClick);
  }

  handleOutsideClick(e) {
    if (this.menuRef && !this.menuRef.contains(e.target)) {
      this.props.onHideMenu();
    }
  }

  getMenuIcon(label) {
    const iconMap = {
      '创建连线': 'icon-lianxian1',
      '访问地址': 'icon-icon_web',
      'web终端': 'icon-terminalzhongduan',
      '构建组件': 'icon-dabaoxiazai',
      '更新组件': 'icon-shuaxin',
      '启动组件': 'icon-qidong1',
      '关闭组件': 'icon-guanbi',
      '删除组件': 'icon-shanchu2'
    };
    return iconMap[label] || 'icon-lianxian1';
  }

  renderMenuItem(label, onClick, isLast = false) {
    const itemStyle = {
      padding: '16px 24px',
      cursor: 'pointer',
      borderBottom: isLast ? 'none' : '1px solid rgba(0,0,0,0.06)',
      fontSize: '15px',
      color: '#262626',
      fontWeight: '500',
      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      display: 'flex',
      alignItems: 'center',
      gap: '16px',
      position: 'relative',
      letterSpacing: '0.3px'
    };

    const iconStyle = {
      fontSize: '20px',
      transition: 'transform 0.3s ease',
      width: '24px',
      textAlign: 'center'
    };

    const arrowStyle = {
      marginLeft: 'auto',
      fontSize: '14px',
      opacity: 0,
      transition: 'all 0.3s ease',
      transform: 'translateX(-8px)',
      fontWeight: 'bold'
    };

    return (
      <div
        style={itemStyle}
        onMouseEnter={e => {
          e.currentTarget.style.backgroundColor = 'rgba(24, 144, 255, 0.08)';
          e.currentTarget.style.background = 'linear-gradient(135deg, rgba(24, 144, 255, 0.12) 0%, rgba(24, 144, 255, 0.06) 100%)';
          e.currentTarget.style.color = '#1890ff';
          e.currentTarget.style.paddingLeft = '28px';
          e.currentTarget.style.borderLeft = '3px solid #1890ff';
          const icon = e.currentTarget.querySelector('.menu-icon');
          const arrow = e.currentTarget.querySelector('.menu-arrow');
          if (icon) icon.style.transform = 'scale(1.15) rotate(8deg)';
          if (arrow) {
            arrow.style.opacity = '1';
            arrow.style.transform = 'translateX(0)';
          }
        }}
        onMouseLeave={e => {
          e.currentTarget.style.backgroundColor = 'white';
          e.currentTarget.style.background = 'white';
          e.currentTarget.style.color = '#262626';
          e.currentTarget.style.paddingLeft = '24px';
          e.currentTarget.style.borderLeft = 'none';
          const icon = e.currentTarget.querySelector('.menu-icon');
          const arrow = e.currentTarget.querySelector('.menu-arrow');
          if (icon) icon.style.transform = 'scale(1) rotate(0deg)';
          if (arrow) {
            arrow.style.opacity = '0';
            arrow.style.transform = 'translateX(-8px)';
          }
        }}
        onClick={onClick}
      >
        <i className={`menu-icon iconfont ${this.getMenuIcon(label)}`} style={iconStyle}></i>
        <span style={{flex: 1}}>{label}</span>
        <span className="menu-arrow" style={arrowStyle}>→</span>
      </div>
    );
  }

  render() {
    const { visible, position, nodeLabel, userPermission, teamName, visitinfo } = this.props;

    if (!visible) {
      return null;
    }

    const nodeDetails = this.getNodeDetails();

    if (!nodeDetails) {
      return null;
    }

    const curStatus = nodeDetails.cur_status;

    // 计算 permissionObj (从 node-details.js 复制的逻辑)
    const permission = userPermission && userPermission.data || [];
    const team_name = teamName && teamName.tenantName || null;

    const filterByName = (aim, name) => {
      if (aim.length > 0 && name) {
        return aim.filter(item => item.team_name == name);
      }
      return [];
    };

    const filtered = filterByName(permission, team_name);

    const user_permission = filtered.length > 0
      ? filtered[0].tenant_actions.team.sub_models
      : [];

    const component_permission = [];
    user_permission.map((item) => {
      if (item.component) {
        item.component.perms.map((v) => {
          component_permission.push(v);
        });
      }
    });

    let oldList = { ...component_permission };
    let permissionObj = {};
    Object.keys(oldList).map(item => {
      const key = Object.keys(oldList[item])[0];
      const value = Object.values(oldList[item])[0];
      Object.assign(permissionObj, { [key]: value });
    });

    // 获取 visit 和 portList
    const visit = visitinfo && visitinfo.data && visitinfo.data.access_urls || [];
    const portList = nodeDetails.port_list || {};
    const hasVisitUrl = visit.length > 0 && Object.keys(portList).length > 0;

    const menuItems = [];

    // 创建连线 - 始终显示
    menuItems.push({ label: '创建连线', onClick: this.handleCreateEdge });

    // 访问 - 根据条件显示
    if (hasVisitUrl && curStatus === 'running') {
      menuItems.push({ label: '访问地址', onClick: this.handleVisit });
    }

    // 终端 - 非undeploy状态且有权限
    if (curStatus !== 'undeploy') {
      menuItems.push({ label: 'web终端', onClick: this.handleTerminal });
    }

    // 构建 - undeploy或closed状态且有构建权限
    if ((curStatus === 'undeploy' || curStatus === 'closed')) {
      menuItems.push({ label: '构建组件', onClick: this.handleBuild });
    }
    // 更新 - 其他状态且有更新权限
    else {
      menuItems.push({ label: '更新组件', onClick: this.handleUpdate });
    }

    // 启动 - closed状态且有启动权限
    if (curStatus === 'closed') {
      menuItems.push({ label: '启动组件', onClick: this.handleStart });
    }
    // 关闭 - 非undeploy状态且有停止权限
    else if (curStatus !== 'undeploy') {
      menuItems.push({ label: '关闭组件', onClick: this.handleStop });
    }

    // 删除 - 有删除权限
    menuItems.push({ label: '删除组件', onClick: this.handleDelete });

    // 计算菜单位置，避免超出视口
    const menuWidth = 240;
    const menuItemHeight = 57; // 16px padding-top + 16px padding-bottom + 15px font + 10px border
    const headerHeight = 68; // 20px padding-top + 20px padding-bottom + 16px font + 12px decorLine
    const menuHeight = headerHeight + (menuItems.length * menuItemHeight);

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const mouseX = position.get('x');
    const mouseY = position.get('y');

    // 计算菜单的最终位置
    let menuX = mouseX;
    let menuY = mouseY;

    // 如果菜单右侧超出视口，向左偏移
    if (mouseX + menuWidth > viewportWidth) {
      menuX = viewportWidth - menuWidth - 10;
    }

    // 如果菜单底部超出视口，向上偏移
    if (mouseY + menuHeight > viewportHeight) {
      menuY = viewportHeight - menuHeight - 10;
    }

    // 确保不会超出左边界和上边界
    if (menuX < 10) {
      menuX = 10;
    }
    if (menuY < 10) {
      menuY = 10;
    }

    const style = {
      position: 'absolute',
      left: `${menuX}px`,
      top: `${menuY}px`,
      backgroundColor: 'white',
      border: 'none',
      borderRadius: '12px',
      boxShadow: '0 12px 48px rgba(0,0,0,0.18), 0 0 1px rgba(0,0,0,0.1)',
      zIndex: 1000,
      minWidth: '240px',
      overflow: 'hidden',
      backdropFilter: 'blur(10px)'
    };

    const headerStyle = {
      padding: '20px 24px',
      fontWeight: '600',
      fontSize: '16px',
      color: '#262626',
      borderBottom: 'none',
      background: 'linear-gradient(135deg, #f8f9fa 0%, #f0f2f5 100%)',
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      position: 'relative'
    };

    const decorLineStyle = {
      position: 'absolute',
      bottom: 0,
      left: 0,
      right: 0,
      height: '3px',
      background: 'linear-gradient(90deg, #1890ff 0%, #36cfc9 100%)',
      opacity: 0.8
    };

    return (
      <div
        ref={ref => this.menuRef = ref}
        style={style}
        onClick={e => e.stopPropagation()}
      >
        <style>
          {`
            @keyframes pulse {
              0%, 100% { opacity: 1; }
              50% { opacity: 0.5; }
            }
          `}
        </style>
        <div style={headerStyle}>
          <span style={{flex: 1}}>{nodeLabel}</span>
        </div>
        {menuItems.map((item, index) =>
          this.renderMenuItem(item.label, item.onClick, index === menuItems.length - 1)
        )}
      </div>
    );
  }
}

function mapStateToProps(state) {
  const nodeContextMenu = state.get('nodeContextMenu');
  return {
    visible: nodeContextMenu.get('visible'),
    nodeId: nodeContextMenu.get('nodeId'),
    nodeLabel: nodeContextMenu.get('nodeLabel'),
    position: nodeContextMenu.get('position'),
    nodes: state.get('nodes'),
    userPermission: state.get('userPermission'),
    teamName: state.get('teamName'),
    visitinfo: state.get('visitinfo')
  };
}

function mapDispatchToProps(dispatch, ownProps) {
  return {
    onHideMenu: () => dispatch(hideNodeContextMenu()),
    onStartEdgeCreate: (nodeId, position) => {
      dispatch((dispatch, getState) => {
        const state = getState();
        const layoutNodes = require('../selectors/graph-view/layout').layoutNodesSelector(state);
        const node = layoutNodes.get(nodeId);
        if (node) {
          const nodePosition = {
            x: node.get('x'),
            y: node.get('y')
          };
          dispatch(startEdgeCreate(nodeId, nodePosition));
        }
      });
    },
    onDeleteNode: (nodeId) => {
      dispatch(clickCloseDetails());
    }
  };
}

export default connect(mapStateToProps, mapDispatchToProps)(NodeContextMenu);
