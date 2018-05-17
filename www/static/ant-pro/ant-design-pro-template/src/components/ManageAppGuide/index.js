import React, {PureComponent, Fragment} from 'react';
import { Icon, Button } from 'antd';
import styles from './index.less';

export default class Index extends PureComponent {
    constructor(props){
        super(props);
        this.state = {
            status: 'open'
        }
    }
    handleClose =() =>{
        this.setState({status: 'close'})
    }
    handleOpen =() =>{
        this.setState({status: 'open'})
    }
    render(){
        return null;
        return (
            <Fragment>
                <div style={{position:'fixed', top: 0, right: 0, bottom:0, left:0, zIndex: 99999, background: 'rgba(0,0,0, 0.6)', display: this.state.status === 'open'? 'block' : 'none'}}></div>
                <div className={styles.appGuide +' '+ (this.state.status === 'open'? styles.statusOpen : styles.statusClose)}>

                    <span onClick={this.handleOpen} className={styles.siderBar}>
                        操<br />作<br />帮<br />助
                    </span>
                    <div className={styles.outer}>
                    <div className={styles.inner}>
                        
                        <h1 className={styles.title} style={{textAlign: 'center'}}>Rainbond应用管理教程</h1>
                        <div className={styles.bg}>
                        <dl className={styles.category}>
                            <dt>
                                <h3>
                                基础操作
                                </h3>
                                
                            </dt>
                            <dd>
                                <a className={styles.item}><Icon type="right-circle" />应用访问设置</a>
                                <a className={styles.item}><Icon type="right-circle" />性能分析监控</a>
                                <a className={styles.item}><Icon type="right-circle" />负载均衡设置</a>
                                <a className={styles.item}><Icon type="right-circle" />访问权限设置</a>
                            </dd>
                        </dl>
                        <dl className={styles.category}>
                            <dt>
                                <h3>
                                高级操作
                                </h3>
                                
                            </dt>
                            <dd>
                                <a className={styles.item}><Icon type="right-circle" />应用访问设置</a>
                                <a className={styles.item}><Icon type="right-circle" />性能分析监控</a>
                                <a className={styles.item}><Icon type="right-circle" />负载均衡设置</a>
                                <a className={styles.item}><Icon type="right-circle" />访问权限设置</a>
                            </dd>
                        </dl> 
                        </div>
                        <div className={styles.btns}>
                            <Button onClick={this.handleClose}>关闭</Button>
                        </div>
                    </div>
                    </div>
                </div>
            </Fragment>
        )
    }
}
