import react, {PureComponent, Fragment} from 'react'
import {connect} from 'dva';
import {Modal, Steps, Form, Input, Select, Button} from 'antd'
import styles from './index.less'
import userStyles from '../../layouts/UserLayout.less'
const Step = Steps.Step;
const Option = Select.Option;

@connect()
@Form.create()
export default class Index extends PureComponent {
    constructor(props){
        super(props);
        this.state = {
            teamName: '',
            selectedRegion:'',
            regions:[],
            current:0
        }
    }
    componentDidMount = () => {
        this.getAllRegion()
    }
    getAllRegion = () => {
        this.props.dispatch({
            type: 'global/getAllRegion',
            callback: (data) => {
                this.setState({regions: data.list})
            }
        })
    }
    handleNext = () => {
        const form = this.props.form;
        form.validateFields(['team_alias'], (error) => {
            if(!error){
                this.setState({current: 1})
            }
        })
    }
    handlePre = () => {
        this.setState({current: 0})
    }
    handleSubmit = () => {
        const form = this.props.form;
        form.validateFields((error, values) => {
            
            if(!error){
                this.props.dispatch({
                    type:'global/InitTeam',
                    payload: values,
                    callback: () => {
                        this.props.onOk && this.props.onOk();
                    }
                })
            }
        })
    }
    handleRegionChange = (value) => {
        this.setState({selectedRegion: value})
    }
    showRegionTip = () => {
        var region = this.state.regions.filter((region) => {
             return region.region_name === this.state.selectedRegion
        })[0]

        if(region && region.scope !== 'private'){
            return true;
        }
        return false;
    }
    render(){
        const form = this.props.form;
        const {getFieldDecorator} = form;
        return (
            <div className={userStyles.container} style={{position: 'relative', zIndex:33}}>
            <div className={userStyles.content}>
              <div className={userStyles.top}>
                <div className={userStyles.header}>
                    <h1
                      style={{
                      display: 'inline-block',
                      verticalAlign: 'middle',
                      marginBottom: 0
                    }}>{"欢迎使用好雨Rainbond"}</h1>
                    <div className={userStyles.desc}>简单2步, 开启云端之旅</div>
                </div>
                <div className={styles.wrap}>
                    <div className={styles.body}>
                    <Steps current={this.state.current}>
                        <Step title="创建您的团队" description="" />
                        <Step title="开通数据中心" description="" />
                    </Steps>
                    <Form.Item  style={{display: this.state.current === 0 ? 'block' : 'none'}} className={styles.formWrap}>
                        {getFieldDecorator('team_alias', {
                            rules:[{
                                required: true, message: '请输入团队名称'
                            }]
                        })(
                            <Input placeholder="请为您的团队起个名称吧" />
                        )}
                    </Form.Item>
                    <Form.Item style={{display: this.state.current === 1 ? 'block' : 'none'}} className={styles.formWrap}>
                        {getFieldDecorator('region_name', {
                            initialValue:'',
                            rules:[{
                                required: true, message: '请为团队选择一个数据中心'
                            }]
                        })(
                            <Select onChange={this.handleRegionChange} style={{width: '100%'}}>
                                <Option value="">请为团队选择一个数据中心</Option>
                                {
                                    this.state.regions.map((region) => {
                                        return <Option value={region.region_name}>{region.region_alias}</Option>
                                    })
                                }
                            </Select>
                        )}
                       {this.showRegionTip() && <p className={userStyles.desc}>4G内存，1G 高速分布式存储， <span style={{color:'#1890ff'}}>免费试用7天</span></p>} 
                    </Form.Item>
                    </div>
                    <div className={styles.footer}>
                        {
                            this.state.current === 0 ? 
                            <Fragment>
                                <Button onClick={this.handleNext} type="primary">下一步</Button>
                            </Fragment>
                            : null
                        }
                        {
                            this.state.current === 1 ? 
                            <Fragment>
                                <Button onClick={this.handlePre} style={{marginRight: 8}}>上一步</Button>
                                <Button onClick={this.handleSubmit} type="primary">开启云端之旅</Button>
                            </Fragment>
                            : null
                        }
                    </div>
                </div>
              </div>
            </div>
          </div>
        )
    }
}