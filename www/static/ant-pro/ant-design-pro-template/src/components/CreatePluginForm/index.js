import React, { PureComponent } from 'react';
import { connect } from 'dva';
import {Row, Col, Card, Button, Icon, Form, Radio, Select, Input } from 'antd';
import globalUtil from '../../utils/global';
const RadioButton = Radio.Button;
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

@connect(({ list, loading }) => ({

}))
@Form.create()
export default class Index extends PureComponent {
  componentDidMount = () => {
      this.props.getCom && this.props.getCom
  }
  handleSubmit = (e) => {
    e && e.preventDefault();
    const form = this.props.form;
    form.validateFields({ force: true }, (err, fieldsValue) => {
          if (err) return;
          this.props.onSubmit && this.props.onSubmit(fieldsValue)
      });
  }
  checkCmd = (rule, value, callback) => {
     const { getFieldValue } = this.props.form;
     const build_source = getFieldValue('build_source')
     if(build_source === 'image'){
         if(!value){
             callback("请输入镜像地址（名称:tag）如nginx:1.11")
         }else{
             callback();
         }
     }else{
         callback();
     }   
  }
  checkCode = (rule, value, callback) => {
     const { getFieldValue } = this.props.form;
     const build_source = getFieldValue('build_source')
     if(build_source === 'dockerfile'){
         if(!value){
             callback("请输入源码Git地址（必须包含Dockerfile文件)");
             return;
         }
     }
     callback();
  }
  checkCodeVersion = (rule, value, callback) => {
     const { getFieldValue } = this.props.form;
     const build_source = getFieldValue('build_source')
     if(build_source === 'dockerfile'){
         if(!value){
             callback("请输入代码版本");
             return;
         }
     }
     callback();
  }
  render() {
    const { getFieldDecorator, getFieldValue } = this.props.form;
    const data = this.props.data || {};

    var type = getFieldValue('build_source');
    const defaultType = 'image'
    if(!type){
        type = data.build_source || defaultType;
    }
    
    const isEdit = this.props.isEdit === void 0 ? false : this.props.isEdit;
    const allDisabled = this.props.allDisabled === void 0 ? false : this.props.allDisabled

    return (
       <Form  layout="horizontal" hideRequiredMark onSubmit={this.handleSubmit}>
          <Form.Item
            {...formItemLayout}
            label="插件名称"
          >
            {getFieldDecorator('plugin_alias', {
              initialValue: data.plugin_alias || '',
              rules: [{ required: true, message: '要创建的插件还没有名字' }],
            })(
              <Input disabled={allDisabled} placeholder="请为创建的插件起个名字吧" />
            )}
          </Form.Item>
          <Form.Item
            {...formItemLayout}
            label="安装来源"
          >
            {getFieldDecorator('build_source', {
              initialValue: data.build_source || defaultType,
              rules: [{ required: true, message: '请选择插件安装来源' }],
            })(
              <RadioGroup disabled={allDisabled || isEdit}>
                <Radio value="image">镜像</Radio>
                <Radio value="dockerfile">Dockerfile</Radio>
              </RadioGroup>
            )}
           </Form.Item>
            <Form.Item
            {...formItemLayout}
            label="插件类别"
          >
            {getFieldDecorator('category', {
              initialValue: data.category || 'net-plugin:up',
              rules: [{ required: true, message: '请选择插件安装来源' }],
            })(
              <Select  disabled={allDisabled || isEdit} placeholder="请选择类别">
                <Option value="net-plugin:up">入口网络</Option>
                <Option value="net-plugin:down">出口网络</Option>
                <Option value="analyst-plugin:perf">性能分析</Option>
                <Option value="init-plugin">初始化类型</Option>
                <Option value="general-plugin">一般类型</Option>
              </Select>
            )}
          </Form.Item>
          <Form.Item
            style={{display: type === 'image' ? '' : 'none'}}
            {...formItemLayout}
            label="镜像地址"
          >
            {getFieldDecorator('image', {
              initialValue: data.image || '',
              rules: [{ validator: this.checkCmd }],
            })(
              <Input  disabled={allDisabled || isEdit} placeholder="请输入镜像地址（名称:tag）如nginx:1.11" />
            )}
          </Form.Item>
          <Form.Item
            style={{display: type === 'dockerfile' ? '' : 'none'}}
            {...formItemLayout}
            label="源码地址"
          >
            {getFieldDecorator('code_repo', {
              initialValue: data.code_repo || '',
              rules: [{ validator: this.checkCode }],
            })(
              <Input  disabled={allDisabled || isEdit} placeholder="请输入源码Git地址（必须包含Dockerfile文件）" />
            )}
          </Form.Item>
          <Form.Item
            style={{display: type === 'dockerfile' ? '' : 'none'}}
            {...formItemLayout}
            label="代码版本"
          >
            {getFieldDecorator('code_version', {
              initialValue: data.code_version || 'master',
              rules: [{ validator: this.checkCodeVersion }],
            })(
              <Input disabled={allDisabled} placeholder="请输入代码版本" />
            )}
          </Form.Item>
          <Form.Item
            style={{display: (type === 'image' && isEdit) ? '' : 'none'}}
            {...formItemLayout}
            label="镜像版本"
          >
            {getFieldDecorator('image_tag', {
              initialValue: data.image_tag || ((data.image||'').split(':')[1] ||'') || '',
            })(
              <Input disabled={allDisabled} placeholder="镜像版本" />
            )}
          </Form.Item>
          
          <Form.Item
            {...formItemLayout}
            label="最小内存"
          >
            {getFieldDecorator('min_memory', {
              initialValue: data.min_memory || '64',
              rules: [{ required: true, message: '请选择最小内存' }]
            })(
              <Select disabled={allDisabled}>
                <Option value="64">64M</Option>
                <Option value="128">128M</Option>
                <Option value="256">256M</Option>
              </Select>
            )}
          </Form.Item>
          <Form.Item
            style={{display: (type === 'image') ? 'none' : ''}}
            {...formItemLayout}
            label="启动命令"
          >
            {getFieldDecorator('build_cmd', {
              initialValue: data.build_cmd || '',
              rules: [{ required: false, message: '请输入插件的启动命令' }],
            })(
              <Input disabled={allDisabled} placeholder="请输入插件的启动命令" />
            )}
          </Form.Item>
          <Form.Item
            style={{display: isEdit ? '' : 'none'}}
            {...formItemLayout}
            label="更新说明"
          >
            {getFieldDecorator('update_info', {
              initialValue: data.update_info || data.desc || '',
              rules: [{ required: false, message: '请输入更新说明' }],
            })(
              <Input disabled={allDisabled} placeholder="请输入更新说明" />
            )}
          </Form.Item>
          <Form.Item
            style={{display: !isEdit ? '' : 'none'}}
            {...formItemLayout}
            label="一句话说明"
          >
            {getFieldDecorator('desc', {
              initialValue: data.desc || '',
              rules: [{ required: true, message: '请输入一句话说明' }],
            })(
              <Input disabled={allDisabled} placeholder="请输入一句话说明" />
            )}
          </Form.Item>
          {
            !allDisabled ?
            <Row>
              <Col span="5"></Col>
              <Col span="19">
                <Button onClick={this.handleSubmit} type="primary">{this.props.submitText || '创建插件'}</Button>
              </Col>
            </Row>
            : null
          }
          
         
       </Form>
    );
  }
}
