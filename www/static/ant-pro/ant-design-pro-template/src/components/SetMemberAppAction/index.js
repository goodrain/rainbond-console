import React, { PureComponent } from 'react';
import { connect } from 'dva';
import { Button, Icon, Modal, Form, Checkbox, Select } from 'antd';
import RolePermsSelect from '../RolePermsSelect';
import globalUtil from '../../utils/global';
const FormItem = Form.Item;
const CheckboxGroup = Checkbox.Group;

@connect(({ teamControl }) => ({
  teamControl
}))
@Form.create()
class ConfirmModal extends PureComponent{
   constructor(arg){
     super(arg);
     this.state = {
        actions: []
     }
   }
   componentDidMount(){
     this.loadMembers();
   }
   handleSubmit= () => {
       this.props.form.validateFields((err, values) => {
        if (!err) {
          this.props.onOk && this.props.onOk(values);
          
        }
      });
   }
   loadMembers = () => {
    const { dispatch } = this.props;
    const team_name = globalUtil.getCurrTeamName();
    const region_name = globalUtil.getCurrRegionName();
    dispatch({
      type: 'teamControl/fetchMember',
      payload: {
         team_name: team_name,
         region_name: region_name
      }
    })
   }
   render(){
      const { getFieldDecorator } = this.props.form;
      const { onOk, onCancel, actions, title}= this.props;

      const formItemLayout = {
        labelCol: {
          xs: { span: 24 },
          sm: { span: 6 }
        },
        wrapperCol: {
          xs: { span: 24 },
          sm: { span: 14 }
        }
      };
      const tailFormItemLayout = {
        wrapperCol: {
          xs: {
            span: 24,
            offset: 0
          },
          sm: {
            span: 14,
            offset: 6
          },
        },
      };

      const options = actions || [];
      const members = this.props.members || [];
      return (
          <Modal
            title={"设置成员应用权限"}
            visible={true}
            width={800}
            onOk={this.handleSubmit}
            onCancel={onCancel}
          >

             <Form onSubmit={this.handleSubmit}>
              <FormItem
                {...formItemLayout}
                label="选择成员"
                hasFeedback
              >
                {getFieldDecorator('user_ids', {
                    rules: [{
                      required: true,
                      message: '请选择团队成员',
                    }],
                  })(
                    <Select mode="multiple">
                       {
                        members.map((member) => {
                           return <Select.Option value={member.user_id}>{member.user_name}</Select.Option>
                        })
                       }
                    </Select>
                )}
                
              </FormItem>

              <FormItem
                {...formItemLayout}
                label="选择权限"
              >
                {getFieldDecorator('perm_ids', {
                    initialValue:[],
                    rules: [{
                      required: true,
                      message: '请选择权限',
                    }],
                  })(
                    <RolePermsSelect showGroupName={false} hides={['团队相关']} datas={options} />
                )}
                
              </FormItem>
              </Form>

             
          </Modal>
      )
   }
}

export default ConfirmModal