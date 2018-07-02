import React, {PureComponent, Fragment} from 'react';
import Mask from '../comm/mask';
import {Button} from 'antd';
import Task from '../comm/task';
import styles from '../style.less';
export default class Task0 extends Task {
    constructor(props){
        super(props);
    }
    componentDidMount(){
        
    }
    render(){
        return (
            <Fragment>
                <Mask />
                <div
                 className={styles.group0task0}
                 style={{zIndex: 30000,
                    marginTop: -200,
                    marginLeft: -350,
                    borderRadius: 10,
                    textAlign: 'center',
                    padding: '30px 0',
                    background: '#fff', width:700, height: 400, position:'fixed', top: '50%', left: '50%'}}>
                    <div className={styles.top}>
                        <h3  className={styles.title}>快速开始</h3>
                        <p className={styles.desc}>我们准备了一份简单的任务指引， 以便您快速上手Rainbond</p>
                    </div>
                    <div className={styles.middle}>
                        <div className={styles.groupsStep}>
                            1.创建应用
                        </div>
                        <div className={styles.groupsStep}>
                            2.管理应用
                        </div>
                    </div>
                    <div className={styles.bottom}>
                        <Button type="primary" style={{marginRight: 16}}>马上开始</Button>
                        <Button><a href="">查看文档</a></Button>
                    </div>
                </div>
            </Fragment>
        )
    }
}