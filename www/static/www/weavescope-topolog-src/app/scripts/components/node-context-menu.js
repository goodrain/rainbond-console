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
      '创建依赖': 'icon-lianxian1',
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

  renderMenuItem(label, onClick, menuType = 'normal') {
    // menuType: 'create' | 'normal' | 'delete'
    const isDelete = menuType === 'delete';
    const isCreate = menuType === 'create';

    const itemStyle = {
      padding: '16px 24px',
      cursor: 'pointer',
      borderBottom: isCreate ? '1px solid rgba(0,0,0,0.1)' : 'none',
      borderTop: isDelete ? '1px solid rgba(0,0,0,0.1)' : 'none',
      fontSize: '15px',
      color: isDelete ? '#ff4d4f' : '#262626',
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
      textAlign: 'center',
      color: isDelete ? '#ff4d4f' : 'inherit'
    };

    const arrowStyle = {
      marginLeft: 'auto',
      fontSize: '14px',
      opacity: 0,
      transition: 'all 0.3s ease',
      transform: 'translateX(-8px)',
      fontWeight: 'bold'
    };

    const hoverColor = isDelete ? '#ff4d4f' : '#1890ff';
    const hoverBgStart = isDelete ? 'rgba(255, 77, 79, 0.12)' : 'rgba(24, 144, 255, 0.12)';
    const hoverBgEnd = isDelete ? 'rgba(255, 77, 79, 0.06)' : 'rgba(24, 144, 255, 0.06)';

    return (
      <div
        style={itemStyle}
        onMouseEnter={e => {
          e.currentTarget.style.backgroundColor = isDelete ? 'rgba(255, 77, 79, 0.08)' : 'rgba(24, 144, 255, 0.08)';
          e.currentTarget.style.background = `linear-gradient(135deg, ${hoverBgStart} 0%, ${hoverBgEnd} 100%)`;
          e.currentTarget.style.color = hoverColor;
          e.currentTarget.style.paddingLeft = '28px';
          e.currentTarget.style.borderLeft = `3px solid ${hoverColor}`;
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
          e.currentTarget.style.color = isDelete ? '#ff4d4f' : '#262626';
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
        <span style={{ flex: 1 }}>{label}</span>
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
    console.log(nodeDetails, "nodeDetails=====");

    if (!nodeDetails) {
      return null;
    }
    var appStatus = nodeDetails.rank;
    var isThirdParty = nodeDetails.cur_status;
    var isKubeblocks = nodeDetails.service_source;

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

    // 根据 service_source 类型决定显示的菜单项
    const isKubeblocksOrThirdParty = isKubeblocks === 'kubeblocks' || isThirdParty === 'third_party';
    if (isKubeblocksOrThirdParty) {
      // kubeblocks 或 third_party 类型：只显示 关闭/启动（互斥）、删除

      // 启动/关闭 - 互斥显示
      if (appStatus == 'closed') {
        menuItems.push({ label: '启动组件', onClick: this.handleStart });
      } else if (appStatus != 'undeploy') {
        menuItems.push({ label: '关闭组件', onClick: this.handleStop });
      }

      // 删除
      menuItems.push({ label: '删除组件', onClick: this.handleDelete });
    } else {
      // 其他类型：显示 创建依赖、更新、关闭/启动、web终端、删除

      // 创建依赖
      menuItems.push({ label: '创建依赖', onClick: this.handleCreateEdge });

      // 更新组件
      menuItems.push({ label: '更新组件', onClick: this.handleUpdate });

      // 启动/关闭 - 互斥显示
      if (appStatus == 'closed') {
        menuItems.push({ label: '启动组件', onClick: this.handleStart });
      } else if (appStatus !== 'undeploy') {
        menuItems.push({ label: '关闭组件', onClick: this.handleStop });
      }

      // web终端 - 非undeploy状态
      if (appStatus != 'undeploy') {
        menuItems.push({ label: 'web终端', onClick: this.handleTerminal });
      }

      // 删除
      menuItems.push({ label: '删除组件', onClick: this.handleDelete });
    }

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
          <span style={{ flex: 1 }}>{nodeLabel}</span>
        </div>
        {menuItems.map((item, index) => {
          let menuType = 'normal';
          if (item.label === '创建依赖') {
            menuType = 'create';
          } else if (item.label === '删除组件') {
            menuType = 'delete';
          }
          return this.renderMenuItem(item.label, item.onClick, menuType);
        })}
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
