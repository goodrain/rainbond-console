import React, {PureComponent} from 'react';
export default class Index extends PureComponent {
    constructor(props){
        super(props);
        this.state = {
            minWidth: ''
        }
    }
    componentDidMount(){
        this.listener();
        this.addListener();
    }
    componentWillMount(){
        this.removeListener();
    }
    listener = () => {
        const lg = this.props.lg || '';
        const md = this.props.md || '';
        const sm = this.props.sm || '';
        const smMathch = window.matchMedia("(min-width: 350px)");
        const mdMathch = window.matchMedia("(min-width: 800px)");
        if(smMathch.matches){
            this.setState({minWidth: sm})
            return;
        }

        if(mdMathch.matches){
            this.setState({minWidth: md})
            return;
        }
        this.setState({minWidth: lg})
    }
    addListener(){
        window.addEventListener('resize', this.listener, false)
    }
    removeListener(){
        window.removeEventListener('resize', this.listener, false)
    }
    render(){
        const minWidth = this.state.minWidth;
        return(
            <div style={{width: '100%', overflowX: 'auto'}}>
              <div style={{minWidth: minWidth}}>{this.props.children}</div>
            </div>
        )
    }
}