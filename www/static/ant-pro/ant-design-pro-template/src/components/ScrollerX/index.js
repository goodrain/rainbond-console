import React, {PureComponent} from 'react';
export default class Index extends PureComponent {
    render(){
        const minWidth = this.props.minWidth || 500
        return(
            <div style={{width: '100%', overflowX: 'auto'}}>
              <div style={{minWidth: minWidth}}>{this.props.children}</div>
            </div>
        )
    }
}