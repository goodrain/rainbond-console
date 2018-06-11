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



    const nodeInfo = this.props.nodes.get(this.props.label).toJS();
    return (
      <div className={'node-details'}>
        {tools}
        <div className="node-details-header"  style={{backgroundColor: getStatusColor(nodeInfo.cur_status)}}>
          <div className="node-details-header-wrapper">
            
            <h2 className="node-details-header-label">
              {
                nodeInfo.id == 'The Internet' ? 
                   <span className="node-details-text truncate">{label} </span>
                   :
                    <a href="javascript:;" onClick={this.handleClickService.bind(this, nodeInfo)}>
                    <span className="node-details-text truncate">{label} </span>
                    <span style={{verticalAlign: 'middle'}} className="icon-angle-right"></span>
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

  handleClickService(nodeDetails){
    //调用父页面预留的接口
    window.parent && parent.handleClickService && parent.handleClickService(nodeDetails);
  }

  handleClickRelation(relation){
     //调用父页面预留的接口
    window.parent && parent.handleClickRelation && parent.handleClickRelation(relation);
  }

  handleClickGiveMoney(nodeDetails){
    window.parent && parent.handleClickGiveMoney && parent.handleClickGiveMoney(nodeDetails);
  }

  renderDetails() {
    const { details, nodeControlStatus, nodeMatches = makeMap(), selectedNodeId } = this.props;
    const showControls = details.controls && details.controls.length > 0;
    const nodeColor = getNodeColorDark(details.rank, details.label, details.pseudo);
    const {error, pending} = nodeControlStatus ? nodeControlStatus.toJS() : {};
    const tools = this.renderTools();
    const styles = {
      controls: {
        backgroundColor: brightenColor(nodeColor)
      },
      header: {
        backgroundColor: nodeColor
      }
    };

    const nodeInfo = this.props.nodes.get(this.props.label).toJS();
    const nodeDetails = details;
    //服务列表
    const portList = nodeDetails.port_list||{};
    //此属性只有云节点有
    const nodeList = getNodeList(nodeDetails);
    //依赖列表
    const relationList =  nodeDetails.relation_list||{};
    const show = showDetailContent(nodeDetails);
    const container_memory = nodeDetails.container_memory;

    
    // 实例平均占用内存
    const podMemory = getPodMemory(nodeDetails);
    return (
      <div className={'node-details'}>
        {tools}
        <div className="node-details-header" style={{backgroundColor: getStatusColor(nodeDetails.cur_status)}}>
          <div className="node-details-header-wrapper">
            
            <h2 className="node-details-header-label" title={nodeInfo.label}>
              {
                nodeDetails.id == 'The Internet' ? 
                   <span className="node-details-text truncate"><MatchedText text={nodeInfo.label} match={nodeMatches.get('label')} /> </span>
                   :
                   <a href="javascript:;" onClick={this.handleClickService.bind(this, nodeDetails)}>
                    <span className="node-details-text truncate"><MatchedText text={nodeInfo.label} match={nodeMatches.get('label')} /> </span>
                    <span style={{verticalAlign: 'middle'}} className="icon-angle-right"></span>
                  </a>
              }
              
            </h2>
            
            {
              nodeDetails.id== 'The Internet' ? null : 
                <div className="node-details-header-relatives">
                  <table style={{width: '100%'}}>
                    <tr>
                      <td style={{width: '33%', textAlign: 'left'}}>{nodeDetails.status_cn||'未知'}</td>
                      <td style={{width: '33%', textAlign: 'center'}}>内存 {nodeDetails.total_memory}</td>
                      <td style={{width: '33%', textAlign: 'right'}}>实例数 {getPodNum(nodeDetails)}</td>
                    </tr>
                  </table>
                </div>
            }
          </div>
        </div>

        <div className="node-details-content" style={{display:show?'block':'none'}}>

        {
          nodeList.length>0 && (<div className="node-details-content-section">
            <table style={{width: '100%', tableLayout: 'fixed'}}>
              <thead>
                <tr>
                  <th style={{textAlign: 'left'}}>服务</th>
                  <th style={{width: '80px', textAlign: 'right'}}>端口</th>
                </tr>
              </thead>
            {
              nodeList.map((node, index) => {
                let portMap = node.port_map||{};
                return Object.keys(portMap).map((key, index) => {
                    let portItem = portMap[key];
                    return (
                      <tbody>
                      {
                        portItem.outer_url && (
                          <tr>
                            <td style={{textAlign: 'left', textDecoration: 'underline', cursor: 'pointer'}}><a style={{color: '#3c3c5a'}} href={portItem.protocol+'://'+portItem.outer_url} target="_blank">{portItem.outer_url.split(':')[0]}</a></td>
                            <td style={{textAlign: 'right'}}>{portItem.outer_url.split(':')[1]}</td>
                          </tr>
                        )
                      }
                      {
                        (portItem.domain_list || []).map((domain, index) => {
                         return (
                          <tr>
                            <td style={{textAlign: 'left', textDecoration: 'underline', cursor: 'pointer'}}><a style={{color: '#3c3c5a'}} href={domain} target="_blank">{domain}</a></td>
                            <td style={{textAlign: 'right'}}>80</td>
                          </tr>
                         );
                        })
                      }
                      {
                        (portItem.is_inner_service) && (
                        <tr>
                          <td style={{textAlign: 'left'}}>{node.service_cname}</td>
                          <td style={{textAlign: 'right'}}>{portItem.mapping_port}</td>
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
           Object.keys(portList).length>0 && (<div className="node-details-content-section">
            <table style={{width: '100%', tableLayout: 'fixed'}}>
              <thead>
                <tr>
                  <th style={{textAlign: 'left'}}>服务</th>
                  <th style={{width: '80px', textAlign: 'right'}}>端口</th>
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
                            <td style={{textAlign: 'left'}}><a style={{color: '#3c3c5a'}} href="javascript:;" target="_blank">{portItem.outer_url.split(':')[0]}</a></td>
                            :
                            <td style={{textAlign: 'left', textDecoration: 'underline', cursor: 'pointer'}}><a style={{color: '#3c3c5a'}} href={portItem.protocol+'://'+portItem.outer_url} target="_blank">{portItem.outer_url.split(':')[0]}</a></td>
                          }
                          
                          <td style={{textAlign: 'right'}}>{portItem.outer_url.split(':')[1]}</td>
                        </tr>
                      )
                    }
                    {
                      (portItem.domain_list || []).map((domain, index) => {
                       return (
                        <tr>
                          <td style={{textAlign: 'left', textDecoration: 'underline', cursor: 'pointer'}}><a style={{color: '#3c3c5a'}} href={domain} target="_blank">{domain}</a></td>
                          <td style={{textAlign: 'right'}}>80</td>
                        </tr>
                       );
                      })
                    }
                    {
                      (portItem.is_inner_service) && (
                      <tr>
                        <td style={{textAlign: 'left'}}>{nodeDetails.service_cname}</td>
                        <td style={{textAlign: 'right'}}>{portItem.mapping_port}</td>
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
            Object.keys(relationList).length>0 && (<div className="node-details-content-section">
              <table style={{width: '100%', tableLayout: 'fixed'}}>
                <thead>
                  <tr>
                    <th style={{textAlign: 'left'}}>依赖服务</th>
                    <th style={{width: '80px', textAlign: 'right'}}>端口</th>
                  </tr>
                </thead>
                <tbody>
                  {
                    Object.keys(relationList).map((key, index) => {
                      let relationListItem = relationList[key]||[];
                      return relationListItem.map((item, index) => {
                        return (
                          <tr>
                            <td onClick={(ev)=>{this.handleRelativeClick(ev, item.service_alias, undefined, item.service_cname, item.service_alias )}} style={{textAlign: 'left', textDecoration: 'underline', cursor: 'pointer'}}>{item.service_cname}</td>
                            <td style={{textAlign: 'right'}}>{item.mapping_port}</td>
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
            ((nodeDetails.pod_list || []).length>0) && (
                <div className="node-details-content-section">
                  <table style={{width: '100%', tableLayout: 'fixed'}}>
                    <thead>
                      <tr>
                        <th style={{textAlign: 'left'}}>实例</th>
                        <th style={{width: '80px', textAlign: 'right'}}>使用内存</th>
                      </tr>
                    </thead>
                    <tbody>
                      {
                        (nodeDetails.pod_list || []).map((value, index) => {
                          return (
                            <tr>
                              <td style={{textAlign: 'left'}}>{value.PodName}</td>
                              <td style={{textAlign: 'right'}}>{container_memory}M</td>
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
            <table style={{width: '100%', tableLayout: 'fixed'}}>
              <tbody>
                <tr>
                  <td style={{textAlign: 'left'}}></td>
                  
                </tr>
              </tbody>
            </table>
          </div>

        </div>
      </div>
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
  };
}

export default connect(
  mapStateToProps,
  { clickCloseDetails, clickShowTopologyForNode }
)(NodeDetails);
