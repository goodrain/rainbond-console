import React, {
    PureComponent,
    Fragment
} from 'react';
import {
    Button,
    Icon,
    Card,
    Modal
} from 'antd';
import {
    connect
} from 'dva';
import Result from '../../components/Result';
import {
    routerRedux
} from 'dva/router';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import {
    getCreateComposeCheckInfo,
    getCreateComposeCheckResult,
    getComposeCheckuuid
} from '../../services/createApp';
import globalUtil from '../../utils/global';
import CodeCustomForm from '../../components/CodeCustomForm';
import LogProcress from '../../components/LogProcress';
import userUtil from '../../utils/user';
import regionUtil from '../../utils/region';
import ConfirmModal from '../../components/ConfirmModal';




class ShowKeyModal extends PureComponent {
    constructor(props) {
        super(props);
        this.state = {

        }
    }
    componentDidMount() {

    }
    render() {
        const {
            onCancel
        } = this.props;
        return (
            <Modal
        title="配置授权Key"
        visible={true}
        onCancel={onCancel}
        footer={[<Button onClick={onCancel}>已授权</Button>]}
      >
        <p><Icon type="info-circle-o" /> 请拷贝如下Key到您的私有Git仓库进行授权，云帮平台方可访问您的私有Git仓库</p>
        <p style={{border: '1px dotted #dcdcdc', padding: '20px'}}>
          sdfsdfsdfsdf
        </p>
      </Modal>
        )
    }
}


class EditCreateCode extends PureComponent {
    handleOk = () => {
        var Com = this.ref.getWrappedInstance();
        var form = Com.getForm();
        form.validateFields((err, fieldsValue) => {
            if (err) return;
            this.props.onSubmit && this.props.onSubmit(fieldsValue)
        });
    }
    handleCancel = () => {
        this.props.onCancel && this.props.onCancel();
    }
    saveRef = (ref) => {
        this.ref = ref;
    }
    render() {
        return <Modal 
          title="基本信息修改"
          width={600}
          visible={true}
          onOk={this.handleOk}
          onCancel={this.handleCancel}

        >
        <CodeCustomForm showCreateGroup={false} showSubmitBtn={false} ref={this.saveRef} onSubmit={this.props.onSubmit} />
       </Modal>
    }
}


@connect(({
    user,
    appControl
}) => ({
    currUser: user.currentUser,
}))
export default class CreateCheck extends PureComponent {
    constructor(props) {
        super(props);
        this.state = {
            //failure、checking、success
            status: '',
            check_uuid: '',
            group_id: '',
            compose_id: '',
            errorInfo: [],
            serviceInfo: [],
            showEdit: false,
            showDelete: false
        }
        this.mount = false;
        this.socketUrl = '';
        var teamName = globalUtil.getCurrTeamName();
        var regionName = globalUtil.getCurrRegionName();
        var region = userUtil.hasTeamAndRegion(this.props.currUser, teamName, regionName);
        if (region) {
            this.socketUrl = regionUtil.getEventWebSocketUrl(region);
        }

    }

    componentDidMount(loopStatus) {
        const team_name = globalUtil.getCurrTeamName();
        this.getCheckuuid();
        this.mount = true;
        this.bindEvent();
    }
    getCheckuuid = () => {
        const appAlias = this.getAppAlias();
        const team_name = globalUtil.getCurrTeamName();
        const params = this.getParams();
        getComposeCheckuuid({
            team_name: team_name,
            ...params
        }).then((data) => {
            if (data) {

                if (!data.bean.check_uuid) {
                    this.startCheck();
                } else {
                    this.state.check_uuid = data.bean.check_uuid;
                    this.loopStatus();
                }
            }
        })
    }
    startCheck = (loopStatus) => {
        const appAlias = this.getAppAlias();
        const team_name = globalUtil.getCurrTeamName();
        const params = this.getParams();
        getCreateComposeCheckInfo({
            team_name: team_name,
            app_alias: appAlias,
            ...params
        }, (res) => {
            if (res.status === 404) {
                this.props.dispatch(routerRedux.replace('/exception/404'));
            }
        }).then((data) => {
            if (data) {
                this.state.check_uuid = data.bean.check_uuid;
                this.setState({
                    eventId: data.bean.check_event_id,
                    appDetail: data.bean
                })
                if (loopStatus !== false) {
                    this.loopStatus();
                }
            }
        })
    }
    getAppAlias() {
        return this.props.match.params.appAlias;
    }
    loopStatus = () => {
        if (!this.mount) return;
        const params = this.getParams();
        const team_name = globalUtil.getCurrTeamName();
        getCreateComposeCheckResult({
            team_name: team_name,
            check_uuid: this.state.check_uuid,
            ...params
        }).then((data) => {
            if (data && this.mount) {
                var status = data.bean.check_status;
                var error_infos = data.bean.error_infos || [];
                var serviceInfo = data.bean.service_info || [];
                this.setState({
                    status: status,
                    errorInfo: error_infos,
                    serviceInfo: serviceInfo
                })
            }
        }).finally(() => {
            if (this.mount && this.state.status === 'checking') {
                setTimeout(() => {
                    this.loopStatus();
                }, 5000)

            }
        })
    }
    componentWillUnmount() {
        this.mount = false;
        this.unbindEvent();
    }
    getParams() {
        return {
            group_id: this.props.match.params.groupId,
            compose_id: this.props.match.params.composeId

        }
    }
    handleCreate = () => {
        const appAlias = this.getAppAlias();
    }
    renderError = () => {
        const errorInfo = this.state.errorInfo;
        const extra = (
            <div>
            {
              errorInfo.map((item)=>{
                 return <div style={{ marginBottom: 16 }}>
                    <Icon style={{ color: '#f5222d', marginRight: 8 }} type="close-circle-o" />
                    <span dangerouslySetInnerHTML={{__html:'<span>'+(item.error_info||'')+' '+(item.solve_advice||'')+'</span>'}}></span>
                  </div>
              })
            }
          </div>
        );
        const actions = [<Button onClick={this.showDelete} type="default">放弃创建</Button>,
            <Button onClick={this.recheck} type="primary">重新检测</Button>
        ];

        return <Result
              type="error"
              title="应用检测未通过"
              description="请核对并修改以下信息后，再重新检测。"
              extra={extra}
              actions={actions}
              style={{ marginTop: 48, marginBottom: 16 }}
            />
    }
    handleSetting = () => {
        const params = this.getParams();
        this.props.dispatch(routerRedux.push(`/create/create-compose-setting/${params.group_id}/${params.compose_id}`));
    }
    handleBuild = () => {

        const appDetail = this.state.appDetail;
        const params = this.getParams();
        this.props.dispatch({
            type: 'groupControl/buildCompose',
            payload: {
                team_name: globalUtil.getCurrTeamName(),
                ...params
            },
            callback: () => {
                this.props.dispatch(routerRedux.replace("/groups/" + params.group_id))
            }
        })
    }
    renderSuccessInfo = (item) => {

        if (item.value) {
            if (typeof item.value === 'string') {
                return <div style={{paddingLeft: 32}}><span  style={{ verticalAlign: 'top',display: 'inline-block', fontWeight: 'bold' }}>{item.key}：</span>{item.value}</div>
            } else {
                return <div style={{paddingLeft: 32}}>
               <span  style={{ verticalAlign: 'top',display: 'inline-block', fontWeight: 'bold' }}>{item.key}：</span>
               <div style={{display: 'inline-block'}}>
               {
                 (item.value || []).map((item)=>{
                    return <p style={{marginBottom: 0}}>{item}</p>
                 })
               }
               </div>
               </div>
            }
        }

    }
    renderSuccess = () => {
        const serviceInfo = this.state.serviceInfo || [];
        const extra = (
            <div>
            {
              serviceInfo.map((item)=>{
                 return <div style={{ marginBottom: 16}}>
                      <p>应用名称：{item.service_cname}</p>
                     {
                         (item.service_info || []).map((item) => {

                              return <div style={{marginBottom: 16}}>
                                        {
                                           this.renderSuccessInfo(item)
                                        }
                            
                                     </div>
                         })
                     }
                    </div>
              })
            }
          </div>
        );
        const actions = [<Button onClick={this.handleBuild} type="primary">构建应用</Button>,
            <Button type="default" onClick={this.handleSetting}>高级设置</Button>,
            <Button  onClick={this.showDelete} type="default">放弃创建</Button>
        ];
        return <Result
              type="success"
              title="应用检测通过"
              description="请核对已下信息后开始构建。如信息有误，请点高级设置进行修改"
              extra={extra}
              actions={actions}
              style={{ marginTop: 48, marginBottom: 16 }}
            />
    }
    renderChecking = () => {
        const actions = <Button onClick={this.showDelete} type="default">放弃创建</Button>;

        const extra = (
            <div>
            {
              this.state.eventId && <LogProcress socketUrl={this.socketUrl} eventId={this.state.eventId} /> 
            }
          </div>
        );
        return <Result
              type="ing"
              title="应用检测中..."
              extra={extra}
              description="此过程可能比较耗时，请耐心等待"
              actions={actions}
              style={{ marginTop: 48, marginBottom: 16 }}
            />
    }
    recheck = () => {
        this.setState({
            status: 'checking'
        }, () => {
            this.startCheck();
        })
    }
    handleClick = (e) => {
        var parent = e.target;

        while (parent) {
            if (parent === document.body) {
                return;
            }
            var actionType = parent.getAttribute('action_type');
            if (actionType === 'modify_url' || actionType === 'modify_userpass') {
                this.setState({
                    showEdit: actionType
                })
                return;
            }

            if (actionType === 'get_publickey') {
                this.setState({
                    showKey: true
                })
                return;
            }
            parent = parent.parentNode
        }
    }
    handleCancelEdit = () => {
        this.setState({
            showEdit: false
        })
    }
    handleCancelShowKey = () => {
        this.setState({
            showKey: false
        })
    }
    bindEvent = () => {
        document.addEventListener('click', this.handleClick, false);
    }
    unbindEvent = () => {
        document.removeEventListener('click', this.handleClick);
    }
    handleDelete = () => {
        const params = this.getParams();
        this.props.dispatch({
            type: 'groupControl/deleteCompose',
            payload: {
                team_name: globalUtil.getCurrTeamName(),
                ...params
            },
            callback: () => {
                this.props.dispatch(routerRedux.replace("/index"))
            }
        })
    }
    showDelete = () => {
        this.setState({
            showDelete: true
        })
    }
    render() {
        const status = this.state.status;
        return <PageHeaderLayout>
          
          <Card bordered={false}>
            <div style={{minHeight: 400}}>
            {(status === 'checking') ? this.renderChecking() : null}
            {status === 'success' ? this.renderSuccess() : null}
            {status === 'failure' ? this.renderError() : null}
            </div>
          </Card>
          {this.state.showEdit ? <EditCreateCode onCancel={this.handleCancelEdit} /> : null}
          {this.state.showDelete && <ConfirmModal onOk={this.handleDelete} title="放弃创建" subDesc="此操作不可恢复" desc="确定要放弃创建此应用吗？" onCancel={()=>{this.setState({showDelete: false})}} />}
        </PageHeaderLayout>
    }
}
