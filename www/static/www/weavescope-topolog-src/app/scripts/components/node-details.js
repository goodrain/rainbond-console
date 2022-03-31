import debug from 'debug';
import React from 'react';
import classNames from 'classnames';
import { connect } from 'react-redux';
import { Map as makeMap } from 'immutable';

import { clickCloseDetails, clickShowTopologyForNode, clickRelative } from '../actions/app-actions';
import { brightenColor, getNeutralColor, getNodeColorDark, getStatusColor } from '../utils/color-utils';
import { isGenericTable, isPropertyList, statusCN, getContainerMemory, getPodNum, getPodMemory, showDetailContent, getNodeList } from '../utils/node-details-utils';
import { resetDocumentTitle, setDocumentTitle } from '../utils/title-utils';

import MatchedText from './matched-text';
import NodeDetailsControls from './node-details/node-details-controls';
import NodeDetailsGenericTable from './node-details/node-details-generic-table';
import NodeDetailsPropertyList from './node-details/node-details-property-list';
import NodeDetailsHealth from './node-details/node-details-health';
import NodeDetailsInfo from './node-details/node-details-info';
import NodeDetailsRelatives from './node-details/node-details-relatives';
import NodeDetailsTable from './node-details/node-details-table';
import Warning from './warning';
import CloudFeature from './cloud-feature';
import NodeDetailsImageStatus from './node-details/node-details-image-status';
import '../../font/iconfont.css'

const log = debug('scope:node-details');

function getTruncationText(count) {
  return 'This section was too long to be handled efficiently and has been truncated'
    + ` (${count} extra entries not included). We are working to remove this limitation.`;
}

class NodeDetails extends React.Component {
  constructor(props, context) {
    super(props, context);
    this.handleClickClose = this.handleClickClose.bind(this);
    this.handleShowTopologyForNode = this.handleShowTopologyForNode.bind(this);
    this.handleRelativeClick = this.handleRelativeClick.bind(this);
    this.state = {
      shows: false,
      count: 0
    }
  }

  handleClickClose(ev) {
    ev.preventDefault();
    this.props.clickCloseDetails(this.props.nodeId);
  }

  handleShowTopologyForNode(ev) {
    ev.preventDefault();
    this.props.clickShowTopologyForNode(this.props.topologyId, this.props.nodeId);
  }

  componentDidMount() {
    this.updateTitle();
  }

  componentWillUnmount() {
    resetDocumentTitle();
  }

  renderTools() {
    const showSwitchTopology = this.props.nodeId !== this.props.selectedNodeId;
    const topologyTitle = `View ${this.props.label} in ${this.props.topologyId}`;

    return (
      <div className="node-details-tools-wrapper">
        <div className="node-details-tools">
          <span title="Close details" className="fa fa-close" onClick={this.handleClickClose} />
        </div>
      </div>
    );
  }

  renderLoading() {
    const node = this.props.nodes.get(this.props.nodeId);
    const label = node ? node.get('label') : this.props.label;
    // NOTE: If we start the fa-spin animation before the node details panel has been
    // mounted, the spinner is displayed blurred the whole time in Chrome (possibly
    // caused by a bug having to do with animating the details panel).
    const spinnerClassName = classNames('fa fa-circle-o-notch', { 'fa-spin': this.props.mounted });
    const nodeColor = (node ?
      getNodeColorDark(node.get('rank'), label, node.get('pseudo')) :
      getNeutralColor());
    const tools = this.renderTools();
    const styles = {
      header: {
        backgroundColor: nodeColor
      }
    };


    const nodeInfo = this.props.nodes.get(this.props.id).toJS();
    return (
      <div className={'node-details'}>
        {tools}
        <div className="node-details-header" style={{ backgroundColor: getStatusColor(nodeInfo.cur_status) }}>
          <div className="node-details-header-wrapper">

            <h2 className="node-details-header-label">
              {
                nodeInfo.id == 'The Internet' ?
                  <span className="node-details-text truncate">{label} </span>
                  :
                  <a href="javascript:;" onClick={this.handleClickService.bind(this, nodeInfo)}>
                    <span className="node-details-text truncate">{label} </span>
                    <span style={{ verticalAlign: 'middle' }} className="icon-angle-right"></span>
                  </a>
              }
            </h2>

            <div className="node-details-relatives truncate">
              Loading...
            </div>
          </div>
        </div>
        <div className="node-details-content">
          <div className="node-details-content-loading">
            <span className={spinnerClassName} />
          </div>
        </div>
      </div>
    );
  }

  renderNotAvailable() {
    const tools = this.renderTools();
    return (
      <div className="node-details">
        {tools}
        <div className="node-details-header node-details-header-notavailable">
          <div className="node-details-header-wrapper">
            <h2 className="node-details-header-label">
              {this.props.label}
            </h2>
            <div className="node-details-relatives truncate">
              n/a
            </div>
          </div>
        </div>
        <div className="node-details-content">
          <p className="node-details-content-info">
            <strong>{this.props.label}</strong> is not visible to Scope when it
            is not communicating.
            Details will become available here when it communicates again.
          </p>
        </div>
      </div>
    );
  }

  handleRelativeClick(ev, nodeId, topologyId, label, serviceAlias) {
    ev.preventDefault();
    // trackMixpanelEvent('scope.node.relative.click', {
    //   topologyId: this.props.topologyId,
    // });
    this.props.dispatch(clickRelative(
      nodeId,
      topologyId,
      label,
      //this.node.getBoundingClientRect()
      {},
      serviceAlias
    ));
  }

  render() {
    if (this.props.notFound) {
      return this.renderNotAvailable();
    }

    if (this.props.details) {
      return this.renderDetails();
    }

    return this.renderLoading();
  }

  handleClickService(nodeDetails) {
    //调用父页面预留的接口
    window.parent && parent.handleClickService && parent.handleClickService(nodeDetails);
  }

  handleClickRelation(relation) {
    //调用父页面预留的接口
    window.parent && parent.handleClickRelation && parent.handleClickRelation(relation);
  }
  handleClickTerminal(relation) {
    //调用父页面预留的接口 web终端
    window.parent && parent.handleClickTerminal && parent.handleClickTerminal(relation);
  }
  handleClickVisit(relation) {
    //调用父页面预留的接口访问
    window.parent && parent.handleClickVisit && parent.handleClickVisit(relation);
  }
  handleClickUpdate(relation, detailes) {
    //调用父页面预留的接口更新
    window.parent && parent.handleClickUpdate && parent.handleClickUpdate(relation, detailes);
  }
  handleClickBuild(relation, detailes) {
    //调用父页面预留的接口构建
    window.parent && parent.handleClickBuild && parent.handleClickBuild(relation, detailes);
  }
  handleClickCloses(relation, detailes) {
    //调用父页面预留的接口关闭
    window.parent && parent.handleClickCloses && parent.handleClickCloses(relation, detailes);
  }
  handleClickGiveMoney(nodeDetails) {
    window.parent && parent.handleClickGiveMoney && parent.handleClickGiveMoney(nodeDetails);
  }
  handleClickStart(relation, detailes) {
    //调用父页面预留的接口启动点击事件
    window.parent && parent.handleClickStart && parent.handleClickStart(relation, detailes);
  }
  handleClickDelete(relation, detailes) {
    //调用父页面预留的接口删除点击事件
    window.parent && parent.handleClickDelete && parent.handleClickDelete(relation, detailes);
  }
  iframeGetMonitor(fn, errcallback) {
    window.parent && parent.iframeGetMonitor && parent.iframeGetMonitor(fn, errcallback);
  }
  visit() {
    this.setState({
      shows: true
    })
  }
  visitout() {
    this.setState({
      shows: false
    })
  }
  renderDetails() {
    const { details, nodeControlStatus, nodeMatches = makeMap(), selectedNodeId, bean, disk, visitinfo, pods } = this.props;
    const { shows } = this.state
    const nodeDetails = details;
    const showControls = details.controls && details.controls.length > 0;
    const instanceDetail = bean && bean.bean.containers || [];
    const instancePods = pods && pods.data || []
    const visit = visitinfo && visitinfo.data.access_urls || [];
    const disks = disk && disk.data.disk && Math.round(disk.data.disk) || 0
    const nodeColor = getNodeColorDark(details.rank, details.label, details.pseudo);
    const { error, pending } = nodeControlStatus ? nodeControlStatus.toJS() : {};
    const tools = this.renderTools();
    const nodeInfo = this.props.nodes.get(this.props.id).toJS();
    //服务列表
    const portList = nodeDetails.port_list || {};
    //此属性只有云节点有
    const nodeList = getNodeList(nodeDetails);
    //依赖列表
    const relationList = nodeDetails.relation_list || {};
    const show = showDetailContent(nodeDetails);
    const container_memory = nodeDetails.container_memory;
    // 实例平均占用内存
    const podMemory = getPodMemory(nodeDetails);
    const styles = {
      controls: {
        backgroundColor: brightenColor(nodeColor)
      },
      header: {
        backgroundColor: nodeColor
      }
    };
    let instance_count = 0;
    instancePods.map((item, index) => {
      if (item.pod_status == 'RUNNING') {
        instance_count++
      }
      return instance_count
    })
    // const nodeInfo = this.props.nodes.get(this.props.label).toJS();
    //计算运行时间
    var day = Math.floor(new Date().getTime() / 1000) - (new Date(nodeDetails.start_time).getTime() / 1000),
      day2 = Math.floor(day / (24 * 3600)),
      day3 = day2 * 24 * 3600,
      day4 = day - day3,
      day5 = Math.floor(day4 / 3600),
      day6 = day4 - day5 * 3600,
      day7 = Math.floor(day6 / 60),
      day8 = day6 - day7 * 60;
    

    return (
      <div className={'node-details'}>
        {tools}
        <div className="node-details-header" style={{ backgroundColor: getStatusColor(nodeDetails.cur_status) }}>
          <div className="node-details-header-wrapper" style={{ padding: '16px 36px 0px 36px' }}>

            <h2 className="node-details-header-label" title={nodeInfo.label}>
              {
                nodeDetails.id == 'The Internet' ?
                  <span className="node-details-text truncate"><MatchedText text={nodeInfo.label} match={nodeMatches.get('label')} /> </span>
                  :
                  <a href="javascript:;" onClick={this.handleClickService.bind(this, nodeDetails)}>
                    <span className="node-details-text truncate"><MatchedText text={nodeInfo.label} match={nodeMatches.get('label')} /> </span>
                    <span style={{ verticalAlign: 'middle' }} className="icon-angle-right"></span>
                  </a>
              }

            </h2>

            {
              nodeDetails.id == 'The Internet' ? null :
                nodeDetails.cur_status == "third_party" ?
                  <div className="node-details-header-relatives">
                    <table style={{ width: '100%' }}>
                      <tr>
                        <td style={{ width: '100%', textAlign: 'center' }}>第三方服务</td>
                      </tr>
                    </table>
                  </div> :
                  <div className="node-details-header-relatives" style={{ width: '121%', paddingTop: '6px', marginLeft: '-36px' }}>
                    <table style={{ width: '100%', padding: '5px 0px', background: 'rgba(255,255,255,0.2)' }}>
                      <tr style={{ display: 'flex', justifyContent: 'start', alignItems: 'center', padding: '0px 34px' }}>
                        {
                          // nodeDetails.cur_status != 'abnormal' && nodeDetails.cur_status != 'undeploy' && nodeDetails.cur_status != 'starting' &&  nodeDetails.cur_status != 'closed' &&  nodeDetails.cur_status != 'creating' &&
                          (visit.length > 0 && Object.keys(portList).length > 0) && nodeDetails.cur_status == 'running' &&
                          (<td style={{ cursor: 'pointer', position: 'relative', marginRight: '40px' }}>
                            <div onMouseOver={() => { this.visit() }} title="访问" style={{ fontSize: '20px' }} className="iconfont icon-icon_web"></div>
                            {shows && (
                              <div onMouseLeave={() => { this.visitout() }} style={{ position: 'absolute', left: '-20%', top: '85%', paddingTop: '15px' }}>
                              <div style={{ width: '360px', background: '#fff', padding: '0px 10px', fontSize: '12px', boxShadow: '0 2px 8px rgb(0 0 0 / 15%)', borderRadius: '4px', maxHeight:'200px', overflow:'auto' }}>
                                {Object.keys(portList).map((key, index) => {
                                  let portItem = portList[key];
                                  return (
                                    <tbody>
                                        {
                                          portItem.outer_url && (
                                            <div>
                                              {
                                                portItem.protocol === 'stream' ?
                                                  <a style={{ color: 'rgba(0,0,0,.65)', lineHeight: '30px', textDecoration:'underline', display:'block' }} href="javascript:;" target="_blank">{portItem.outer_url.split(':')[0]}</a>
                                                  : <a style={{ color: 'rgba(0,0,0,.65)', lineHeight: '30px', textDecoration:'underline', display:'block' }} href={portItem.protocol + '://' + portItem.outer_url} target="_blank">{portItem.outer_url.split(':')[0]}</a>
                                              }
                                            </div>
                                          )
                                        }
                                        {
                                          (portItem.domain_list || []).map((domain, index) => {
                                            return (
                                              <a style={{ color: 'rgba(0,0,0,.65)', lineHeight: '30px', textDecoration:'underline', display:'block' }} href={domain} target="_blank">{domain}</a>
                                            );
                                          })
                                        }
                                    </tbody>
                                  )
                                })}
                              </div>
                                    </div>
                            )}
                          </td>)
                        }
                        {nodeDetails.cur_status == 'undeploy' ? (
                          null
                        ):(
                          <td style={{ cursor: 'pointer', marginRight: '40px' }}>
                            <a onClick={this.handleClickTerminal.bind(this, nodeDetails)} target="_blank" title="终端" style={{ fontSize: '20px', fontWeight: '600' }} className="iconfont icon-terminalzhongduan"></a>
                          </td>
                        )}
                        
                        {nodeDetails.cur_status == 'undeploy' || nodeDetails.cur_status == 'closed' ? (
                          <td style={{ cursor: 'pointer', marginRight: '40px' }} title="构建">
                            <a onClick={this.handleClickBuild.bind(this, 'build', nodeDetails)} style={{ fontSize: '20px', fontWeight: '600' }} className="iconfont icon-dabaoxiazai"></a>
                          </td>
                        ) : (
                          <td style={{ cursor: 'pointer', marginRight: '40px' }} title="更新">
                            <a onClick={this.handleClickUpdate.bind(this, 'update', nodeDetails)} style={{ fontSize: '20px', fontWeight: '600' }} className="iconfont icon-shuaxin"></a>
                          </td>
                        )}
                        {nodeDetails.cur_status == 'undeploy' ? (
                          <div>
                          </div>
                        ) : (
                          <div style={{ marginRight: '40px', cursor: 'pointer' }}>
                            {(nodeDetails.cur_status == 'closed') ? (
                              <td style={{ cursor: 'pointer' }} title="启动">
                                <a onClick={this.handleClickStart.bind(this, 'start', nodeDetails)} style={{ fontSize: '20px', fontWeight: '600' }} className="iconfont icon-qidong1"></a>
                              </td>
                            ) : (
                              <td style={{ cursor: 'pointer' }} title="关闭">
                                <a onClick={this.handleClickCloses.bind(this, 'closes', nodeDetails)} style={{ fontSize: '20px', fontWeight: '600' }} className="iconfont icon-guanbi"></a>
                              </td>
                            )}
                          </div>
                        )}
                        <td style={{ cursor: 'pointer' }} title="删除">
                          <a onClick={this.handleClickDelete.bind(this, 'deleteApp', nodeDetails)} style={{ fontSize: '20px' }} className="iconfont icon-shanchu2"></a>
                        </td>
                      </tr>
                    </table>
                  </div>
            }
          </div>
        </div>
        <div className="node-details-content">
          {nodeDetails.id == 'The Internet' ? null :
            nodeDetails.cur_status == "third_party" ? null :
              // nodeDetails.cur_status == "closed" ? null :
              <div>
                <div className="node-details-content-section">
                  <div className="node-details-content-section-header" style={{ fontSize: '15px' }}>基本信息</div>
                  <div style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'center' }}>
                      <div style={{ textAlign: 'right', width: '40%' }}>运行状态：</div>
                      <div style={{ textAlign: 'left', width: '60%' }}>{nodeDetails.status_cn || '部分实例异常'}</div>
                    </div>
                    <div style={{ display: 'flex' }}>
                      <div style={{ textAlign: 'right', width: '40%' }}>内存：</div>
                      <div style={{ textAlign: 'left', width: '60%' }}>{nodeDetails.total_memory + 'MB' || ''}</div>
                    </div>
                    <div style={{ display: 'flex' }}>
                      <div style={{ textAlign: 'right', width: '40%' }}>CPU：</div>
                      <div style={{ textAlign: 'left', width: '60%' }}>{nodeDetails.container_cpu ? nodeDetails.container_cpu + 'm' : '不限制'}</div>
                    </div>
                    <div style={{ display: 'flex' }}>
                      <div style={{ textAlign: 'right', width: '40%' }}>磁盘：</div>
                      <div style={{ textAlign: 'left', width: '60%' }}>{disks + 'MB'}</div>
                    </div>
                    <div style={{ display: 'flex' }}>
                      <div style={{ textAlign: 'right', width: '40%' }}>运行时间：</div>
                      {(nodeDetails.start_time == "" || !nodeDetails.start_time) ? (
                        <div style={{ textAlign: 'left', width: '60%' }}>{'当前状态无运行时间'}</div>
                      ) : (
                        <div style={{ textAlign: 'left', width: '60%' }}>{`${day2}天${day5}小时${day7}分钟${day8}秒`}</div>
                      )}
                    </div>
                    <div style={{ display: 'flex' }}>
                      <div style={{ textAlign: 'right', width: '40%' }}>版本号：</div>
                      {(nodeDetails.deploy_version == '' || nodeDetails.deploy_version == 'undefined') ? (
                        <div style={{ textAlign: 'left', width: '60%' }}>{'当前状态无版本号'}</div>
                      ) : (
                        <div style={{ textAlign: 'left', width: '60%' }}>{nodeDetails.deploy_version}</div>
                      )}
                    </div>
                    <div style={{ display: 'flex' }}>
                      <div style={{ textAlign: 'right', width: '40%' }}>运行实例数量：</div>
                      <div style={{ textAlign: 'left', width: '60%' }}>{instance_count}</div>
                    </div>
                  </div>
                </div>
              </div>
          }
          {nodeDetails.id == 'The Internet' ? null :
            nodeDetails.cur_status == "third_party" ? null :
              <div>
                {instanceDetail.length > 0 && instanceDetail == null ? null :
                  nodeDetails.cur_status == "closed" ? null :
                  nodeDetails.cur_status == "undeploy" ? null : (
                    <div className="node-details-content-section">
                      <div className="node-details-content-section-header" style={{ fontSize: '15px' }}>实例中的容器</div>
                      <div style={{ width: '100%' }}>
                        <table style={{ tableLayout: 'fixed', width: '100%' }}>
                          <thead>
                            <tr>
                              <th style={{ textAlign: 'left', width: '40%' }}>镜像名称</th>
                              <th style={{ width: '25%', textAlign: 'center' }}>状态</th>
                              <th style={{ width: '35%', textAlign: 'center' }}>说明</th>
                            </tr>
                          </thead>
                          {instanceDetail.length > 0 && instanceDetail.map((item, index) => {
                            return (
                              < tbody >
                                <tr>
                                  <td className="node-details-info-field-value truncate" style={{ textAlign: 'left' }} title={item.image}>{item.image}</td>
                                  <td style={{ textAlign: 'center' }}>{item.state == 'Running' ? '运行中' : item.state == 'Waiting' ? '等待中' : '---'}</td>
                                  <td className="node-details-info-field-value truncate" title={item.reason} style={{ textAlign: 'center' }}>{item.reason ? item.reason : '---'}</td>
                                </tr>
                              </tbody>
                            )
                          })}
                        </table>
                      </div>
                    </div>
                  )}
              </div>
          }
          <div className="node-details-content-section" style={{ display: show ? 'block' : 'none' }}>
            {
              nodeList.length > 0 && (<div className="node-details-content-section">
                <table style={{ width: '100%', tableLayout: 'fixed' }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left' }}>服务</th>
                      <th style={{ width: '80px', textAlign: 'right' }}>端口</th>
                    </tr>
                  </thead>
                  {
                    nodeList.map((node, index) => {
                      let portMap = node.port_map || {};
                      return Object.keys(portMap).map((key, index) => {
                        let portItem = portMap[key];
                        return (
                          <tbody>
                            {
                              portItem.outer_url && (
                                <tr>
                                  <td style={{ textAlign: 'left', textDecoration: 'underline', cursor: 'pointer' }}><a style={{ color: '#3c3c5a' }} href={portItem.protocol + '://' + portItem.outer_url} target="_blank">{portItem.outer_url.split(':')[0]}</a></td>
                                  <td style={{ textAlign: 'right' }}>{portItem.outer_url.split(':')[1]}</td>
                                </tr>
                              )
                            }
                            {
                              (portItem.domain_list || []).map((domain, index) => {
                                return (
                                  <tr>
                                    <td style={{ textAlign: 'left', textDecoration: 'underline', cursor: 'pointer' }}><a style={{ color: '#3c3c5a' }} href={domain} target="_blank">{domain}</a></td>
                                    <td style={{ textAlign: 'right' }}>80</td>
                                  </tr>
                                );
                              })
                            }
                            {
                              (portItem.is_inner_service) && (
                                <tr>
                                  <td style={{ textAlign: 'left' }}>{node.service_cname}</td>
                                  <td style={{ textAlign: 'right' }}>{portItem.mapping_port}</td>
                                </tr>
                              )
                            }
                            <tr>
                              <td>&nbsp;</td>
                              <td>&nbsp;</td>
                            </tr>
                          </tbody>
                        )
                      })
                    })
                  }
                </table>
              </div>)
            }

            {
              Object.keys(portList).length > 0 && (<div className="node-details-content-section">
                <table style={{ width: '100%', tableLayout: 'fixed' }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left' }}>服务</th>
                      <th style={{ width: '80px', textAlign: 'right' }}>端口</th>
                    </tr>
                  </thead>
                  {
                    Object.keys(portList).map((key, index) => {
                      let portItem = portList[key];
                      return (

                        <tbody>
                          {
                            portItem.outer_url && (
                              <tr>
                                {
                                  portItem.protocol === 'stream' ?
                                    <td style={{ textAlign: 'left' }}><a style={{ color: '#3c3c5a' }} href="javascript:;" target="_blank">{portItem.outer_url.split(':')[0]}</a></td>
                                    :
                                    <td style={{ textAlign: 'left', textDecoration: 'underline', cursor: 'pointer' }}><a style={{ color: '#3c3c5a' }} href={portItem.protocol + '://' + portItem.outer_url} target="_blank">{portItem.outer_url.split(':')[0]}</a></td>
                                }

                                <td style={{ textAlign: 'right' }}>{portItem.outer_url.split(':')[1]}</td>
                              </tr>
                            )
                          }
                          {
                            (portItem.domain_list || []).map((domain, index) => {
                              return (
                                <tr>
                                  <td style={{ textAlign: 'left', textDecoration: 'underline', cursor: 'pointer' }}><a style={{ color: '#3c3c5a' }} href={domain} target="_blank">{domain}</a></td>
                                  <td style={{ textAlign: 'right' }}>80</td>
                                </tr>
                              );
                            })
                          }
                          {
                            (portItem.is_inner_service) && (
                              <tr>
                                <td style={{ textAlign: 'left' }}>{nodeDetails.service_cname}</td>
                                <td style={{ textAlign: 'right' }}>{portItem.mapping_port}</td>
                              </tr>
                            )
                          }
                        </tbody>
                      )
                    })
                  }
                </table>
              </div>)
            }


            {
              Object.keys(relationList).length > 0 && (<div className="node-details-content-section">
                <table style={{ width: '100%', tableLayout: 'fixed' }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left' }}>依赖服务</th>
                      <th style={{ width: '80px', textAlign: 'right' }}>端口</th>
                    </tr>
                  </thead>
                  <tbody>
                    {
                      Object.keys(relationList).map((key, index) => {
                        let relationListItem = relationList[key] || [];
                        return relationListItem.map((item, index) => {
                          return (
                            <tr>
                              <td onClick = {this.handleClickRelation.bind(this, item)} style={{ textAlign: 'left', textDecoration: 'underline', cursor: 'pointer' }}>{item.service_cname}</td>
                              <td style={{ textAlign: 'right' }}>{item.mapping_port}</td>
                            </tr>
                          );
                        });
                      })
                    }
                  </tbody>
                </table>
              </div>)
            }

            {
              ((nodeDetails.pod_list || []).length > 0) && (
                <div className="node-details-content-section">
                  <table style={{ width: '100%', tableLayout: 'fixed' }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'left' }}>实例</th>
                        <th style={{ width: '80px', textAlign: 'right' }}>使用内存</th>
                      </tr>
                    </thead>
                    <tbody>
                      {
                        (nodeDetails.pod_list || []).map((value, index) => {
                          return (
                            <tr>
                              <td style={{ textAlign: 'left' }}>{value.pod_name}</td>
                              <td style={{ textAlign: 'right' }}>{container_memory}M</td>
                            </tr>
                          );
                        })
                      }
                    </tbody>
                  </table>
                </div>
              )
            }

            <div className="node-details-content-section">
              <table style={{ width: '100%', tableLayout: 'fixed' }}>
                <tbody>
                  <tr>
                    <td style={{ textAlign: 'left' }}></td>

                  </tr>
                </tbody>
              </table>
            </div>

          </div>
        </div>
      </div >
    );
  }

  renderTable(table) {
    const { nodeMatches = makeMap() } = this.props;

    if (isGenericTable(table)) {
      return (
        <NodeDetailsGenericTable
          rows={table.rows} columns={table.columns}
          matches={nodeMatches.get('tables')}
        />
      );
    } else if (isPropertyList(table)) {
      return (
        <NodeDetailsPropertyList
          rows={table.rows} controls={table.controls}
          matches={nodeMatches.get('property-lists')}
        />
      );
    }

    log(`Undefined type '${table.type}' for table ${table.id}`);
    return null;
  }

  componentDidUpdate() {
    this.updateTitle();
  }

  updateTitle() {
    setDocumentTitle(this.props.details && this.props.details.label);
  }
}

function mapStateToProps(state, ownProps) {
  const currentTopologyId = state.get('currentTopologyId');
  return {
    tenantName: localStorage.getItem('tenantName'),
    groupId: localStorage.getItem('groupId'),
    nodeMatches: state.getIn(['searchNodeMatches', currentTopologyId, ownProps.id]),
    nodes: state.get('nodes'),
    selectedNodeId: state.get('selectedNodeId'),
    bean: state.get('nodedetailes'),
    disk: state.get('diskdetail'),
    visitinfo: state.get('visitinfo'),
    pods: state.get('getpods'),
  };
}

export default connect(
  mapStateToProps,
  { clickCloseDetails, clickShowTopologyForNode }
)(NodeDetails);
