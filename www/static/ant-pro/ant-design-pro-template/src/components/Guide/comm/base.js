import React, { PureComponent, Fragment } from 'react';
class Base extends PureComponent {
    getViewWH = () => {
        return {
            width: document.documentElement.clientWidth || document.body.clientWidth,
            height: document.documentElement.clientHeight || document.body.clientHeight 
        }
    }
    getTargetRect = () => {
        var target = document.querySelector(this.props.target);
        if(target){
            return target.getBoundingClientRect();
        }
        return null;
    }

}
export default Base;