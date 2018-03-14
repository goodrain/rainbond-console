import React from 'react';
import {connect} from 'dva';

class Index extends React.PureComponent {
    constructor(props) {
        super(props);
        this.state = {
            inited: false
        }
    }
    componentDidMount() {
        this
            .props
            .dispatch({
                type: 'global/fetchRainbondInfo',
                callback: () => {
                    this.setState({inited: true})
                }
            });
    }
    render() {
        const {rainbondInfo} = this.props;

        if (!rainbondInfo) {
            return null;
        }
        return (this.props.children);
    }
}

export default connect(({global}) => {
    return {rainbondInfo: global.rainbondInfo}
})(Index);