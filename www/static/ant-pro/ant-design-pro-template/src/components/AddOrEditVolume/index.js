import React, { PureComponent, Fragment } from 'react';
import { connect } from 'dva';
import { Link, Switch, Route } from 'dva/router';
import { Row, Col, Card, Form, Button, Icon, Menu, Input, Alert,  Dropdown, Table, Modal, Radio, Tooltip, notification} from 'antd';
const FormItem = Form.Item;
const RadioButton = Radio.Button;
const RadioGroup = Radio.Group;


@Form.create()
export default class AddVolumes extends PureComponent {
  handleSubmit = (e) => {
    e.preventDefault();
    this.props.form.validateFields((err, values) => {
      if (!err) {
        this.props.onSubmit && this.props.onSubmit(values);
      }
    });
  }
  handleCancel = () => {
      this.props.onCancel && this.props.onCancel();
  }
  render(){
     const { getFieldDecorator } = this.props.form;
     const { data } = this.props;
      const formItemLayout = {
      labelCol: {
        xs: { span: 24 },
        sm: { span: 6 },
      },
      wrapperCol: {
        xs: { span: 24 },
        sm: { span: 16 },
      },
    };
     return (
      <Modal
        title="添加持久化"
        onOk={this.handleSubmit}
        onCancel = {this.handleCancel}
        visible={true}
      >
        <Form onSubmit={this.handleSubmit}>
          <FormItem
          {...formItemLayout}
          label="名称"
          >
            {getFieldDecorator('volume_name', {
              initialValue: data.volume_name || '',
              rules: [{ required: true, message: '请输入持久化名称' }],
            })(
              <Input  placeholder="请输入持久化名称" />
            )}
          </FormItem>
          <FormItem
          {...formItemLayout}
          label="目录"
          >
            {getFieldDecorator('volume_path', {
              initialValue: data.volume_path || '',
              rules: [{ required: true, message: '请输入持久化目录' }],
            })(
              <Input  placeholder="请输入持久化目录" />
            )}
          </FormItem>
          <FormItem
          {...formItemLayout}
          label="类型"
          >

            {getFieldDecorator('volume_type',{
              initialValue: data.volume_type || '',
              rules: [{ required: true, message: '请选择持久化类型' }],
            })(
              <RadioGroup>
                <Radio value="share-file"><Tooltip title="分布式文件存储，可租户内共享挂载，适用于所有类型应用">共享存储（文件）</Tooltip></Radio>
                <Radio value="memoryfs"><Tooltip title="基于内存的存储设备，容量由内存量限制。应用重启数据即丢失，适用于高速暂存数据">内存文件存储</Tooltip></Radio>
                <Radio value="local"><Tooltip title="本地高速块存储设备，适用于有状态数据库服务">本地存储</Tooltip></Radio>
              </RadioGroup>
            )}
          
          </FormItem>
        </Form>
      </Modal>
     )
  }
}