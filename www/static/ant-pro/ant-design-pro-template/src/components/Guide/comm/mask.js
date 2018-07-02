import React, { PureComponent, Fragment } from 'react';
import styles from '../style.less';
import Base from './base';
class Mask extends Base {
    constructor(props){
        super(props);
        this.state = {
            show: false
        }
    }
    componentDidMount(){
        setTimeout(()=>{
            this.setState({show: true})
        })
        
    }
    getTopStyle = () => {
         var rect = this.getTargetRect();
         var wh = this.getViewWH();
         if(!rect){
             return {
                 left: 0,
                 top:0,
                 right: 0,
                 bottom:0
             }
         }else{
            return {
                left: 0,
                top:0,
                right: 0,
                height: rect.top
            }
         }
         
    }
    getRightStyle = () => {
        var rect = this.getTargetRect();
        var wh = this.getViewWH();
        if(!rect){
            return {
                width: 0,
                height: 0
            }
        }else{
            return {
                left: rect.right,
                top:rect.top,
                right: 0,
                bottom: 0
            }
        }
    }
    getBottomStyle = () => {
        var rect = this.getTargetRect();
        var wh = this.getViewWH();
        if(!rect){
            return {
                width: 0,
                height: 0
            }
        }else{
           return {
               left:rect.left,
               bottom:0,
               right:wh.width-rect.right,
               top: rect.bottom
           }
        }
    }
    getLeftStyle = () => {
        var rect = this.getTargetRect();
        var wh = this.getViewWH();
        if(!rect){
            return {
                width: 0,
                height: 0
            }
        }else{
           return {
               left:0,
               top:rect.top,
               width: rect.left,
               bottom:0
           }
        }
    }
    render(){
        if(!this.state.show) return null;
        return (
            <Fragment>
                <div style={this.getTopStyle()} className={styles.mask}></div>
                <div style={this.getRightStyle()} className={styles.mask}></div>
                <div style={this.getBottomStyle()} className={styles.mask}></div>
                <div style={this.getLeftStyle()} className={styles.mask}></div>
            </Fragment>
        )
    }
}
export default Mask;