import React, {Fragment} from 'react';
import globalUtil from '../utils/global';
import {Layout, Icon, message, notification, Modal, Button} from 'antd';

//提示充值或购买资源
export default class PayTip extends React.PureComponent {
    handleCancel = () => {
        this.props.dispatch({
            type: 'global/hidePayTip'
        })
    }
    handleClick = () => {
        window.open('https://www.goodrain.com/spa/#/personalCenter/my/recharge')
        this.handleCancel();
    }
    getRegionId = () => {
        var regionName = globalUtil.getCurrRegionName();
        let regionId = '';
        if(regionName == 'ali-hz') {
        regionId = 2;
        }
        if(regionName == 'ali-sh'){
        regionId = 1;
        }
        return regionId;
    }
    handleBuySource = () => {
        const regionId = this.getRegionId();
        if(regionId){
            window.open(`https://www.goodrain.com/spa/#/resBuy/${regionId}`)
        }else{
            notification.warning({message: '当前数据中心不可购买'})
        }
        this.handleCancel();
    }
    componentDidMount(){
    }
    render(){
        const regionId = this.getRegionId();
        return <Modal
            visible={true}
            title="提示"
            onCancel={this.handleCancel}
            footer={[regionId ? <Button type="primary" size="sm"><Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/finance}`}>购买资源</Link></Button> : null,
            <Button onClick={this.handleClick} size="sm">账户充值</Button>]}
        >
             <h4 style={{textAlign: 'center'}}>资源及企业账户余额不足</h4>
        </Modal>;
    }
}
