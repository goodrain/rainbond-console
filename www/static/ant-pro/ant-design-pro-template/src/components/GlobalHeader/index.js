import React, {PureComponent} from 'react';
import {
    Layout,
    Menu,
    Icon,
    Spin,
    Tag,
    Dropdown,
    Avatar,
    Divider
} from 'antd';
import Ellipsis from '../Ellipsis';
import moment from 'moment';
import groupBy from 'lodash/groupBy';
import Debounce from 'lodash-decorators/debounce';
import {Link} from 'dva/router';
import NoticeIcon from '../NoticeIcon';
import HeaderSearch from '../HeaderSearch';
import styles from './index.less';
import cookie from '../../utils/cookie';
import userIcon from '../../../public/images/user-icon-small.png';

const {Header} = Layout;

export default class GlobalHeader extends PureComponent {
    componentWillUnmount() {
        this
            .triggerResizeEvent
            .cancel();
    }
    getNoticeData() {
        const {
            notices = []
        } = this.props;
        if (notices.length === 0) {
            return {};
        }
        const newNotices = notices.map((notice) => {
            const newNotice = {
                ...notice
            };
            if (newNotice.datetime) {
                newNotice.datetime = moment(notice.datetime).fromNow();
            }
            // transform id to item key
            if (newNotice.id) {
                newNotice.key = newNotice.id;
            }
            if (newNotice.extra && newNotice.status) {
                const color = ({todo: '', processing: 'blue', urgent: 'red', doing: 'gold'})[newNotice.status];
                newNotice.extra = <Tag
                    color={color}
                    style={{
                    marginRight: 0
                }}>{newNotice.extra}</Tag>;
            }
            return newNotice;
        });
        return groupBy(newNotices, 'type');
    }
    toggle = () => {
        const {collapsed, onCollapse} = this.props;
        onCollapse(!collapsed);
        this.triggerResizeEvent();
    }
    @Debounce(600)
    triggerResizeEvent() { // eslint-disable-line
        const event = document.createEvent('HTMLEvents');
        event.initEvent('resize', true, false);
        window.dispatchEvent(event);
    }
    renderTeams = () => {
        const onTeamClick = this.props.onTeamClick;
        const {currTeam} = this.props;
        const currentUser = this.props.currentUser;
        const teams = currentUser.teams || [];
        const team = teams.filter((item) => {
            item.team_name === currTeam;
        })

        return <Menu className={styles.menu} selectedKeys={[]} onClick={onTeamClick}>
            {teams.map((item) => {
                return (
                    <Menu.Item key={item.team_name}>
                        <Ellipsis tooltip>{item.team_alias}</Ellipsis>
                    </Menu.Item>
                )
            })
}
            <Menu.Divider/>
            <Menu.Item key={'createTeam'}><Icon type="plus"/>新建团队</Menu.Item>
        </Menu>
    }
    getCurrTeam = () => {
        const currTeam = this.props.currTeam;
        const currentUser = this.props.currentUser;
        const teams = currentUser.teams || [];
        return teams.filter((item) => {
            return item.team_name === currTeam;
        })[0]
    }
    renderRegions = () => {
        const onRegionClick = this.props.onRegionClick;
        const team = this.getCurrTeam();
        if (team) {
            return <Menu className={styles.menu} selectedKeys={[]} onClick={onRegionClick}>
                {(team.region || []).map((item) => {
                    return (
                        <Menu.Item key={item.team_region_name}>{item.team_region_alias}</Menu.Item>
                    )
                })
}
                <Menu.Divider/>
                <Menu.Item key={'openRegion'}><Icon type="plus"/>开通数据中心</Menu.Item>
            </Menu>
        }
        return <Menu/>;
    }
    getCurrTeamTit() {
        var team = this.getCurrTeam();
        if (team) {
            return team.team_alias;
        }
        return ''
    }
    getCurrRegionTit() {
        const {currRegion} = this.props;
        var team = this.getCurrTeam();
        if (team) {
            var regions = team.region;
            var selectedRegion = regions.filter((item) => {
                return item.team_region_name === currRegion;
            })[0]
            if (selectedRegion) {
                return selectedRegion.team_region_alias;
            }
        }

        return ''
    }
    render() {
        const {
            currentUser,
            collapsed,
            fetchingNotices,
            isMobile,
            logo,
            onNoticeVisibleChange,
            onMenuClick,
            onNoticeClear,
            notifyCount,
            isPubCloud,
            currRegion,
            currTeam
        } = this.props;

        if (!currentUser) {
            return null
        }

        const menu = (
            <Menu selectedKeys={[]} onClick={onMenuClick}>
                {/*<Menu.Item disabled><Icon type="user" />个人中心</Menu.Item>
        <Menu.Item disabled><Icon type="setting" />设置</Menu.Item>
        <Menu.Item key="triggerError"><Icon type="close-circle" />触发报错</Menu.Item>
        <Menu.Divider />*/}
                <Menu.Item key="logout"><Icon type="logout" style={{
                marginRight: 8
            }}/>退出登录</Menu.Item>
            </Menu>
        );

        const noticeData = this.getNoticeData();
        return (
            <Header className={styles.header}>
                {isMobile && ([
                    (
                        <Link to="/" className={styles.logo} key="logo">
                            <img src={logo} alt="logo" width="32"/>
                        </Link>
                    ), < Divider type = "vertical" key = "line" />
                ])}
                <Icon
                    className={styles.trigger}
                    type={collapsed
                    ? 'menu-unfold'
                    : 'menu-fold'}
                    onClick={this.toggle}/>

                <div className={styles.teamregion}>
                    <span className={styles.tit}>团队:</span>
                    <Dropdown overlay={this.renderTeams()}>
                        <span className={styles.dropdown}>
                            {this.getCurrTeamTit()
}
                            <Icon type="down"/>
                        </span>
                    </Dropdown>

                    <span className={styles.tit}>数据中心:</span>
                    <Dropdown overlay={this.renderRegions()}>
                        <span className={styles.dropdown}>
                            {this.getCurrRegionTit()
}
                            <Icon type="down"/>
                        </span>
                    </Dropdown>
                </div>

                <div className={styles.right}>
                    {/*
          <HeaderSearch
            className={`${styles.action} ${styles.search}`}
            placeholder="站内搜索"
            dataSource={['搜索提示一', '搜索提示二', '搜索提示三']}
            onSearch={(value) => {
              console.log('input', value); // eslint-disable-line
            }}
            onPressEnter={(value) => {
              console.log('enter', value); // eslint-disable-line
            }}
          />
          <NoticeIcon
            className={styles.action}
            count={notifyCount}
            onItemClick={(item, tabProps) => {
              console.log(item, tabProps); // eslint-disable-line
            }}
            onClear={onNoticeClear}
            onPopupVisibleChange={onNoticeVisibleChange}
            loading={fetchingNotices}
            popupAlign={{ offset: [20, -16] }}
          >
            <NoticeIcon.Tab
              list={noticeData['通知']}
              title="通知"
              emptyText="你已查看所有通知"
              emptyImage="https://gw.alipayobjects.com/zos/rmsportal/wAhyIChODzsoKIOBHcBk.svg"
            />
            <NoticeIcon.Tab
              list={noticeData['消息']}
              title="消息"
              emptyText="您已读完所有消息"
              emptyImage="https://gw.alipayobjects.com/zos/rmsportal/sAuJeJzSKbUmHfBQRzmZ.svg"
            />
            <NoticeIcon.Tab
              list={noticeData['待办']}
              title="待办"
              emptyText="你已完成所有待办"
              emptyImage="https://gw.alipayobjects.com/zos/rmsportal/HsIsxMZiWKrNUavQUXqx.svg"
            />
          </NoticeIcon>
        */}
                    {currentUser
                        ? (
                            <Dropdown overlay={menu}>
                                <span className={`${styles.action} ${styles.account}`}>
                                    <Avatar size="small" className={styles.avatar} src={userIcon}/>
                                    <span className={styles.name}>{currentUser.user_name}</span>
                                </span>
                            </Dropdown>
                        )
                        : <Spin
                            size="small"
                            style={{
                            marginLeft: 8
                        }}/>}
                </div>
            </Header>
        );
    }
}
