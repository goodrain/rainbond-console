/*
  添加或者修改插件配置
*/
import React, { PureComponent, Fragment } from 'react';
import { connect } from 'dva';
import { Link, Switch, Route } from 'dva/router';
import { Row, Col, Card, Form, Button, Icon, Menu, Input,  Dropdown, Table, Modal, Radio, Select, Tooltip} from 'antd';
import globalUtil from '../../utils/global';
const RadioGroup = Radio.Group;
const Option = Select.Option;


const formItemLayout = {
  labelCol: {
    span: 5,
  },
  wrapperCol: {
    span: 19,
  },
};

@Form.create()
@connect(({region}) => {
    return {
      protocols: region.protocols || []
    }
})
export default class Index extends PureComponent {
   constructor(props){
     super(props);
     this.state = {
       selectedRowKeys:[],
       apps:[]
     }
     this.envGroup = null;
   }
   componentDidMount(){
      
   }
   handleSubmit = () => {
      const form = this.props.form;
      form.validateFields((err, fieldsValue) => {
          if (err) return;
          this.props.onOk && this.props.onOk(fieldsValue)
      });
   }
   handleCancel = () => {
     this.props.onCancel && this.props.onCancel();
   }
   hanldeMetaTypeChange = (e) => {
     const { getFieldDecorator, setFieldsValue } = this.props.form;
     var value = e.target.value;
     if(value !== 'un_define'){
         setFieldsValue({'injection': 'auto'})
     }
   }
   checkInjection = (rule, value, callback) => {

       if(this.envGroup){
         if(this.envGroup.check()){
          callback();
         }else{
           callback('    ')
         }
       }
       
   }
   handleEvnGroupMount  = (com) => {
      this.envGroup = com;
   }
   render(){

      const title = this.props.title;
      
      const { getFieldDecorator, getFieldValue } = this.props.form;
      const data = this.props.data || {};
      const metaType = getFieldValue('service_meta_type') || 'un_define';
      
      return (
        <Modal
        title= {title|| '发票信息填写'}
        visible={true}
        onOk={this.handleSubmit}
        onCancel = {this.handleCancel}
        >
        <Form>
            <h3 style={{color: '#dedede', borderBottom: '1px solid #dedede', paddingBottom: 8, marginBottom: 16}}>发票基础信息</h3>
            <Form.Item
              {...formItemLayout}
              style={{marginBottom: 10}}
              label="申请人姓名"
            >
              {getFieldDecorator('user_name', {
                initialValue: data.user_name || '',
                rules: [{ required: true, message: '请输入申请人姓名' }],
              })(
                <Input placeholder="请输入申请人姓名" />
              )}
            </Form.Item>
            <Form.Item
              {...formItemLayout}
              style={{marginBottom: 10}}
              label="发票类型"
            >
              {getFieldDecorator('receipt_type', {
                initialValue: data.receipt_type || 'special',
                rules: [{ required: true, message: '发票类型' }],
              })(
                <RadioGroup>
                  <Radio  value="special">增值税专业发票</Radio>
                  <Radio value="normal">增值税普通发票</Radio>
                </RadioGroup>
              )}
            </Form.Item>
            <Form.Item
              style={{marginBottom: 10}}
              {...formItemLayout}
              label="发票抬头"
            >
              {getFieldDecorator('subject', {
                initialValue: data.subject || '',
                rules: [{ required: true, message: '请输入发票抬头' }],
                validateFirst: true
              })(
                <Input placeholder="请输入发票抬头" />
              )}
            </Form.Item>
            <Form.Item
              style={{marginBottom: 10}}
              {...formItemLayout}
              label="纳税人识别号"
            >
              {getFieldDecorator('taxes_id', {
                initialValue: data.taxes_id || '',
                rules: [{ required: true, message: '请输入纳税人识别号' }],
                validateFirst: true
              })(
                <Input placeholder="请输入纳税人识别号" />
              )}
            </Form.Item>
            <Form.Item
              style={{marginBottom: 10}}
              {...formItemLayout}
              label="开户行"
            >
              {getFieldDecorator('bank', {
                initialValue: data.bank || '',
                rules: [{ required: true, message: '请输入开户行' }],
                validateFirst: true
              })(
                <Input placeholder="请输入开户行" />
              )}
            </Form.Item>
            <Form.Item
              style={{marginBottom: 10}}
              {...formItemLayout}
              label="银行账号"
            >
              {getFieldDecorator('bank_account', {
                initialValue: data.bank_account || '',
                rules: [{ required: true, message: '请输入银行账号' }]
              })(
                <Input placeholder="请输入银行账号" />
              )}
            </Form.Item>
            <Form.Item
              style={{marginBottom: 10}}
              {...formItemLayout}
              label="开户人手机"
            >
              {getFieldDecorator('phone', {
                initialValue: data.phone || '',
                rules: [{ required: true, message: '请输入手机' }, {pattern: /^[0-9]{11}$/, message: '格式不正确, 请输入11位数字'}],
                validateFirst: true
              })(
                <Input type="number" maxLength="11" placeholder="请输入手机" />
              )}
            </Form.Item>

            <Form.Item
              style={{marginBottom: 10}}
              {...formItemLayout}
              label="开户行地址"
            >
              {getFieldDecorator('address', {
                initialValue: data.address || '',
                rules: [{ required: true, message: '请输入开户行地址' }],
                validateFirst: true
              })(
                <Input placeholder="请输入开户行地址" />
              )}
            </Form.Item>
            <Form.Item
              style={{marginBottom: 10}}
              {...formItemLayout}
              label="发票内容"
            >
              {getFieldDecorator('content', {
                initialValue: data.content || '服务费',
                rules: [{ required: true, message: '' }]
              })(
                <Select placeholder="">
                  <Select.Option value="服务费">服务费</Select.Option>
                  <Select.Option value="技术服务费">技术服务费</Select.Option>
                </Select>
              )}
            </Form.Item>
            <Form.Item
              style={{marginBottom: 10}}
              {...formItemLayout}
              label="发票金额"
            >
              <span>{data.receipt_money || 0}  元</span>
            </Form.Item>
            <h3 style={{color: '#dedede', borderBottom: '1px solid #dedede', paddingBottom: 8, marginBottom: 16}}>发票邮寄信息</h3>
            <Form.Item
              style={{marginBottom: 10}}
              {...formItemLayout}
              label="邮寄地址"
            >
              {getFieldDecorator('post_address', {
                initialValue: data.post_address || '',
                rules: [{ required: true, message: '请输入邮寄地址' }]
              })(
                <Input placeholder="请输入邮寄地址" />
              )}
            </Form.Item>
            <Form.Item
              style={{marginBottom: 10}}
              {...formItemLayout}
              label="收件人"
            >
              {getFieldDecorator('post_contact', {
                initialValue: data.post_contact || '',
                rules: [{ required: true, message: '请输入收件人' }]
              })(
                <Input placeholder="请输入收件人" />
              )}
            </Form.Item>
            <Form.Item
              style={{marginBottom: 10}}
              {...formItemLayout}
              label="联系人手机"
            >
              {getFieldDecorator('post_contact_phone', {
                initialValue: data.post_contact_phone || '',
                rules: [{ required: true, message: '请输入手机' }, {pattern: /^[0-9]{11}$/, message: '格式不正确, 请输入11位数字'}],
                validateFirst: true
              })(
                <Input type="number" maxLength="11" placeholder="请输入手机" />
              )}
            </Form.Item>
           
        </Form>
        </Modal>
      )
   }
}