import React, {PureComponent, Fragment} from 'react';
import {
  Row,
  Col,
  Button,
  Modal,
  Dropdown,
  Menu,
  Table,
  Card
} from 'antd';
import {connect} from 'dva';
import {Link} from 'dva/router';
import DescriptionList from '../../components/DescriptionList';
import globalUtil from '../../utils/global';
const {Description} = DescriptionList;

/*
  access_type : no_port|无端口、
                http_port|http协议，可以对外访问 、
                not_http_outer|非http、
                可以对外访问的、
                not_http_inner|非http对内，如mysql,
                http_inner| http对内
*/

@connect(({user, appControl, global}) => ({visitInfo: appControl.visitInfo}))
class Index extends PureComponent {
  constructor(props) {
    super(props);
    this.state = {
      showModal: false
    }
    this.mount = false;
  }
  componentDidMount() {
    this.mount = true;
    this.fetchVisitInfo();
  }
  componentWillUnmount() {
    this.mount = false;
    this
      .props
      .dispatch({type: 'appControl/clearVisitInfo'})
  }
  fetchVisitInfo = () => {
    if (!this.mount) 
      return;
    const appAlias = this.props.app_alias;
    this
      .props
      .dispatch({
        type: 'appControl/fetchVisitInfo',
        payload: {
          team_name: globalUtil.getCurrTeamName(),
          app_alias: appAlias
        }
      })
    setTimeout(() => {
      this.fetchVisitInfo();
    }, 4000)

  }

  showModal = () => {
    this.setState({showModal: true})
  }
  hiddenModal = () => {
    this.setState({showModal: false})
  }
  getHttpLinks = (accessInfo) => {
    var res = [];
    for (var i = 0; i < accessInfo.length; i++) {
      res = res.concat((accessInfo[i].access_urls || []));
    }
    return res;
  }
  handleClickLink = (item) => {
    window.open(item.key);
  }
  render() {
    const {appAlias, visitInfo} = this.props;
    const {showModal} = this.state;
    var demo = visitInfo;

    if (!demo) {
      return null;
    }

    if (demo.access_type === 'no_port') {
      return <Fragment>
        <Button onClick={this.showModal}>访问</Button>
        {showModal && <Modal
          title="提示"
          visible={true}
          onCancel={this.hiddenModal}
          footer={[ < Button onClick = {
            this.hiddenModal
          } > 关闭 < /Button>]}>
          <div
            style={{
            textAlign: 'center',
            fontSize: 16
          }}>
            如需要提供访问服务, 请<Link onClick={this.hiddenModal} to={'/app/' + appAlias + '/port'}>配置端口</Link>
          </div>
        </Modal>}
      </Fragment>
    }

    if (demo.access_type === 'http_port') {
      const links = this.getHttpLinks(demo.access_info || {});
      if (links.length === 1) {
        return <Button onClick={() => {
          window.open(links[0])
        }}>访问</Button>;
      } else if (links.length === 0) {
        return <Fragment>
          <Button onClick={this.showModal}>访问</Button>
          {showModal && <Modal
            title="提示"
            visible={true}
            onCancel={this.hiddenModal}
            footer={[ < Button onClick = {
              this.hiddenModal
            } > 关闭 < /Button>]}>
            <div
              style={{
              textAlign: 'center',
              fontSize: 16
            }}>
              http协议端口需打开外部访问服务, 去<Link onClick={this.hiddenModal} to={'/app/' + appAlias + '/port'}>打开</Link>
            </div>
          </Modal>}
        </Fragment>
      } else {
        return <Dropdown
          overlay={(
          <Menu onClick={this.handleClickLink}>
            {links.map((item) => {
              return <Menu.Item key={item}>{item}</Menu.Item>
            })}
          </Menu>
        )}
          placement="bottomRight">
          <Button>
            <a href={links[0]} target="_blank">访问</a>
          </Button>
        </Dropdown>
      }
      return <Fragment>
        <Button onClick={this.showModal}>访问</Button>
        {showModal && <Modal
          title="提示"
          visible={true}
          onCancel={this.hiddenModal}
          footer={[ < Button onClick = {
            this.hiddenModal
          } > 关闭 < /Button>]}>
          <div
            style={{
            textAlign: 'center',
            fontSize: 16
          }}>
            需要配置端口信息, 去<Link onClick={this.hiddenModal} to={'/app/' + appAlias + '/port'}>配置</Link>
          </div>
        </Modal>}
      </Fragment>
    }

    if ((demo.access_type === 'not_http_outer')) {
      var res = demo.access_info || [];
      return <Fragment>
        <Button onClick={this.showModal}>访问</Button>
        {showModal && <Modal
          title="访问信息"
          width="800px"
          visible={true}
          onCancel={this.hiddenModal}
          footer={[ < Button onClick = {
            this.hiddenModal
          } > 关闭 < /Button>]}>

          {res.map((item, i) => {

            return <Card
              style={{
              marginBottom: 24
            }}
              title={< DescriptionList col = "2" > <Description term="访问地址">{item.access_url}</Description> < Description term = "访问协议" > {
              item.protocol
            } < /Description> </DescriptionList >}>
              {!item.connect_info.length
                ? '-'
                : <Fragment>
                  <table style={{
                    width: '100%'
                  }}>
                    <thead>
                      <tr>
                        <th>变量名</th>
                        <th>变量值</th>
                        <th>说明</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(item.connect_info || []).map((item) => {

                        if (item.attr_name.indexOf('_PORT') > -1 || item.attr_name.indexOf('_HOST') > -1) {
                          return null;
                        }

                        return <tr>
                          <td width="150">{item.attr_name}</td>
                          <td>{item.attr_value}</td>
                          <td>{item.name}</td>
                        </tr>
                      })
}
                    </tbody>
                  </table>
                </Fragment>
}

            </Card>

          })
}

        </Modal>}
      </Fragment>
    }

    if ((demo.access_type === 'not_http_inner')) {
      var res = demo.access_info || [];
      return <Fragment>
        <Button onClick={this.showModal}>访问</Button>
        {showModal && <Modal
          title="访问信息"
          width="800px"
          visible={true}
          onCancel={this.hiddenModal}
          footer={[ < Button onClick = {
            this.hiddenModal
          } > 关闭 < /Button>]}>
          <p
            style={{
            fontSize: 14,
            fontWeight: 'normal',
            color: '#838383',
            marginBottom: 8,
            textAlign: 'right'
          }}>其他应用依赖此应用后来访问</p>
          {res.map((item, i) => {

            return <Card
              style={{
              marginBottom: 24
            }}
              title={< DescriptionList col = "2" > <Description term="访问地址">{item.access_url}</Description> < Description term = "访问协议" > {
              item.protocol
            } < /Description> </DescriptionList >}>
              {!item.connect_info.length
                ? '-'
                : <Fragment>
                  <table style={{
                    width: '100%'
                  }}>
                    <thead>
                      <tr>
                        <th>变量名</th>
                        <th>变量值</th>
                        <th>说明</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(item.connect_info || []).map((item) => {

                        if (item.attr_name.indexOf('_PORT') > -1 || item.attr_name.indexOf('_HOST') > -1) {
                          return null;
                        }

                        return <tr>
                          <td width="150">{item.attr_name}</td>
                          <td>{item.attr_value}</td>
                          <td>{item.name}</td>
                        </tr>
                      })
}
                    </tbody>
                  </table>
                </Fragment>
}
            </Card>
          })
}
        </Modal>}
      </Fragment>
    }

  }
}

export default Index;