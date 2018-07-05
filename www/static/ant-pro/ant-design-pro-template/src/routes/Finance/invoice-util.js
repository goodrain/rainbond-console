const statusMap = {
    'Not' : '未处理',
    'Post': '已邮寄',
    'Cancel': '已取消'
}
const typeMap = {
    'special' : '专票',
    'normal': '普票'
}
const util = {
    getStatusCN: (status) => {
        return statusMap[status] || '-'
    },
    getTypeCN: (type) => {
        return typeMap[type] || '-'
    }
}
export default util