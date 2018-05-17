import React, {PureComponent, Fragment} from 'react';
import styles from '../style.less';
import Base from './base';


export default class Task extends Base {
    constructor(props){
        super(props);
        
    }
    componentDidMount(){
        document.body.style.overflow = "hidden"
    }
    componentWillUnmount(){
        document.body.style.overflow = ""
    }
}