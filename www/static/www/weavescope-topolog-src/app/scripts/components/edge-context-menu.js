import React from 'react';
import { connect } from 'react-redux';
import { hideEdgeContextMenu, deleteEdge } from '../actions/app-actions';
import '../../font/iconfont.css';

class EdgeContextMenu extends React.Component {
  constructor(props) {
    super(props);
    this.handleDeleteEdge = this.handleDeleteEdge.bind(this);
    this.handleOutsideClick = this.handleOutsideClick.bind(this);
  }

  handleDeleteEdge() {
    const { edgeId, onDeleteEdge, onHideMenu } = this.props;
    onHideMenu();
    onDeleteEdge(edgeId);
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

  renderMenuItem(label, onClick, iconClass) {
    const itemStyle = {
      padding: '16px 24px',
      cursor: 'pointer',
      fontSize: '15px',
      color: '#262626',
      fontWeight: '500',
      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      display: 'flex',
      alignItems: 'center',
      gap: '16px',
      position: 'relative',
      letterSpacing: '0.3px',
      borderBottom: 'none'
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
          e.currentTarget.style.backgroundColor = 'rgba(255, 77, 79, 0.08)';
          e.currentTarget.style.background = 'linear-gradient(135deg, rgba(255, 77, 79, 0.12) 0%, rgba(255, 77, 79, 0.06) 100%)';
          e.currentTarget.style.color = '#ff4d4f';
          e.currentTarget.style.paddingLeft = '28px';
          e.currentTarget.style.borderLeft = '3px solid #ff4d4f';
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
        <i className={`menu-icon iconfont ${iconClass}`} style={iconStyle}></i>
        <span style={{flex: 1}}>{label}</span>
        <span className="menu-arrow" style={arrowStyle}>→</span>
      </div>
    );
  }

  render() {
    const { visible, position, edgeId } = this.props;


    if (!visible || !position) {
      return null;
    }

    // position 已经是页面坐标了,直接使用
    const mouseX = position.get('x');
    const mouseY = position.get('y');

    // 计算菜单位置，避免超出视口
    const menuWidth = 240;
    const menuItemHeight = 57;
    const headerHeight = 68;
    const menuHeight = headerHeight + menuItemHeight;

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

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
      position: 'fixed',
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
      background: 'linear-gradient(90deg, #ff4d4f 0%, #ff7875 100%)',
      opacity: 0.8
    };

    return (
      <div
        ref={ref => this.menuRef = ref}
        style={style}
        onClick={e => e.stopPropagation()}
      >
        <div style={headerStyle}>
          <span style={{flex: 1}}>连线操作</span>
        </div>
        {this.renderMenuItem('删除连线', this.handleDeleteEdge, 'icon-shanchu2')}
      </div>
    );
  }
}

function mapStateToProps(state) {
  const edgeContextMenu = state.get('edgeContextMenu');
  return {
    visible: edgeContextMenu.get('visible'),
    edgeId: edgeContextMenu.get('edgeId'),
    position: edgeContextMenu.get('position')
  };
}

function mapDispatchToProps(dispatch) {
  return {
    onHideMenu: () => dispatch(hideEdgeContextMenu()),
    onDeleteEdge: (edgeId) => dispatch(deleteEdge(edgeId))
  };
}

export default connect(mapStateToProps, mapDispatchToProps)(EdgeContextMenu);
