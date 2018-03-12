import React, { PureComponent } from 'react';
import { Button, Icon, Modal, Form, Checkbox, Select, Input } from 'antd';
import { getAllRegion } from '../../services/api';
import globalUtil from '../../utils/global';


const FormItem = Form.Item;
const Option = Select.Option;

@Form.create()
class CreateTeam extends PureComponent{
   constructor(arg){
     super(arg);
     this.state = {
        actions: [],
        regions:[]
     }
   }
   componentDidMount(){
     this.getUnRelationedApp();
   }
   getUnRelationedApp = () => {
       getAllRegion().then((data) => {
          if(data){
              this.setState({regions: data.list || []})
          }
      })
   }
   handleSubmit= () => {
       this.props.form.validateFields((err, values) => {
        console.log(values)
        if (!err) {
          this.props.onOk && this.props.onOk(values);
        }
      });
   }
   render(){
      const { getFieldDecorator } = this.props.form;
      const { onOk, onCancel, actions}= this.props;

      const formItemLayout = {
        labelCol: {
          xs: { span: 24 },
          sm: { span: 6 },
        },
        wrapperCol: {
          xs: { span: 24 },
          sm: { span: 14 },
        },
      };
      const tailFormItemLayout = {
        wrapperCol: {
          xs: {
            span: 24,
            offset: 0,
          },
          sm: {
            span: 14,
            offset: 6,
          },
        },
      };

      const options = actions || [];

      return (
          <Modal
            title="新建团队"
            visible={true}
            onOk={this.handleSubmit}
            onCancel={onCancel}
          >

             <Form onSubmit={this.handleSubmit}>
              <FormItem
                {...formItemLayout}
                label="团队名称"
                hasFeedback
              >
                {getFieldDecorator('team_name', {
                    rules: [{
                      required: true,
                      message: '请输入团队名称',
                    }],
                  })(
                    <Input placeholder="请输入团队名称" />
                )}
                
              </FormItem>

              <FormItem
                {...formItemLayout}
                label="数据中心"
                hasFeedback
              >
                {getFieldDecorator('useable_regions', {
                    rules: [{
                      required: true,
                      message: '请选择数据中心',
                    }],
                  })(
                    <Select
                      mode="multiple"
                      style={{ width: '100%' }}
                      placeholder="选择数据中心"
                    >
                      {(this.state.regions || []).map((item) => {
                          return <Option key={item.region_name}>{item.region_alias}</Option>
                      })}
                    </Select>
                )}
                
              </FormItem>
              </Form>

             
          </Modal>
      )
   }
}

export default CreateTeam