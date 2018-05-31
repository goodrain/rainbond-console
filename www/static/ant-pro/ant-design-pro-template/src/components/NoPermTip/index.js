import React, {PureComponent, Fragment} from 'react';
import { Icon } from 'antd';

import NoPerm403 from '../../routes/Exception/403'

class Index extends PureComponent {
    render(){
        return (
            <div style={{textAlign: 'center', padding: '50px 0'}}>
                <Icon style={{fontSize: 50, marginBottom: 32}} type="warning" />
                <h1 style={{fontSize: 50, color: 'rgba(0, 0, 0, 0.65)', marginBottom: 8}}>无权限访问</h1>
            </div>
        )
    }
}

export default NoPerm403;
