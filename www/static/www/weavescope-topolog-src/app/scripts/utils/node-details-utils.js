import { NODE_DETAILS_TABLE_COLUMN_WIDTHS } from '../constants/styles';

//判断一个port是否可以显示
function isPortActive(port) {
    var domain = port.domain_list || [];
    if(domain.length || port.is_inner_service || port.is_outer_service){
      return true;
    }
    return false;
}

//过滤节点下不可用的port
function filterNodePort(node) {
   var portMap = node.port_map||{};
   var portKeys = Object.keys(portMap);
   for(var i=0;i<portKeys.length;i++){
      if(!isPortActive(portMap[portKeys[i]])){
          delete portMap[portKeys[i]];
      }
   }
}

function getInternerPort(nodeDetails) {
    var nodeList = nodeDetails.result_list||[];
    var res = [];
    for (var i=0;i<nodeList.length;i++) {
        var node = nodeList[i];
        filterNodePort(node);
        var portMap = node.port_map;
        var portKeys = Object.keys(portMap);
        // 判断此节点下是否有可用的port
        if(portKeys.length){
           res.push(node);
        }
    }
    return res;
}


export function getNodeList(nodeDetails={}) {
  return getInternerPort(nodeDetails);
}

export function showDetailContent(nodeDetails){
  return (nodeDetails.id == 'The Internet' || nodeDetails.cur_status === 'running' || nodeDetails.cur_status === 'closed') ? true : false;
}

// 节点状态对应的中文描述
export function statusCN(nodeDetails) {
  var map = {
     'running' : '运行中',
     'closed'  : '已关闭',
     'undeploy' : '未部署',
     'starting' : '开启中',
     'startting' : '开启中',
     'checking' : '检测中',
     'stoping' : '关闭中',
     'stopping' : '关闭中'

  }
  return map[nodeDetails.cur_status]  || '未知状态';
}

// 获取节点的内存占用
export function getContainerMemory(nodeDetails) {
  //不是运行中的状态内存强制显示为0
  if(nodeDetails.cur_status !== 'running'){
     return '0M';
  }
  return (nodeDetails.container_memory || 0)+'M';
}

// 获取节点的实例数量
export function getPodNum(nodeDetails) {
  return (nodeDetails.pod_list || []).length;
}

// 获取节点的实例的平均内存
export function getPodMemory(nodeDetails) {
  const memory = nodeDetails.container_memory||0;
  const totalPod = (nodeDetails.pod_list || []).length;
  return totalPod ? (memory / totalPod).toFixed(0) : memory;
}

export function isGenericTable(table) {
  return (table.type || (table.get && table.get('type'))) === 'multicolumn-table';
}

export function isPropertyList(table) {
  return (table.type || (table.get && table.get('type'))) === 'property-list';
}

export function isNumber(data) {
  return data && data.dataType && data.dataType === 'number';
}

export function isIP(data) {
  return data && data.dataType && data.dataType === 'ip';
}

export function genericTableEntryKey(row, column) {
  const columnId = column.id || column.get('id');
  const rowId = row.id || row.get('id');
  return `${rowId}_${columnId}`;
}

export function defaultSortDesc(header) {
  return header && isNumber(header);
}

export function getTableColumnsStyles(headers) {
  return headers.map(header => ({
    // More beauty hacking, ports and counts can only get
    // so big, free up WS for other longer fields like IPs!
    width: NODE_DETAILS_TABLE_COLUMN_WIDTHS[header.id],
    textAlign: isNumber(header) ? 'right' : 'left'
  }));
}
