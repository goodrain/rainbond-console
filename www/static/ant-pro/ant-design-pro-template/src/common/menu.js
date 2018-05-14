import {isUrl} from '../utils/utils';
import globalUtil from '../utils/global';

const menuData = [
  {
    name: '总览',
    icon: 'dashboard',
    path: `team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/index`,
  }, {
    name: '创建应用',
    icon: 'plus',
    path: `team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/create`,
    children: [
      {
        name: '从源码创建',
        path: 'code'
      }, {
        name: '从Docker镜像创建',
        path: 'image'
      }, {
        name: '从应用市场安装',
        path: 'market'
      }
    ]
  }, {
    name: '我的应用',
    icon: 'appstore-o',
    path: `team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/groups`
  }, {
    name: '我的插件',
    icon: 'api',
    path: `team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/myplugns`
  }, {
    name: '团队管理',
    icon: 'team',
    path: `team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/team`
  }, {
    name: '连接云市',
    icon: 'usb',
    path: `team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/source`
  }, {
    name: '财务中心',
    icon: 'red-envelope',
    path: `team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/finance`
  }
];

function formatter(data, parentPath = '', parentAuthority) {
  return data.map((item) => {
    let {path} = item;
    if (!isUrl(path)) {
      path = parentPath + item.path;
    }
    const result = {
      ...item,
      path,
      authority: item.authority || parentAuthority
    };
    if (item.children) {
      result.children = formatter(item.children, `${parentPath}${item.path}/`, item.authority);
    }
    return result;
  });
}

//处理我的应用二级和三级菜单
export const getMenuData = (groups) => {

  var menus = formatter(menuData);
  if (groups && groups.length) {

    for (var i = 0; i < menus.length; i++) {
      var item = menus[i];

      if (item.path.indexOf('groups') > -1) {
        item.children = groups.map((group) => {
          var children = (group.service_list || []).map((item) => {
            return {
              name: item.service_cname,
              path: `team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/app/${item.service_alias}`,
              link: true,
              exact: true
            }
          })
          return {
            name: group.group_name,
            path: `team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/groups/${group.group_id}`,
            link: true,
            children: children,
            exact: true

          }
        })

      }
    }
  }

  return menus;

}
