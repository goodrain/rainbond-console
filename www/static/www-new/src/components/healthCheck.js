import widget from '../ui/widget';
import http from '../utils/http';
import http2 from '../utils/http2';
import { getHealthCheckInfo } from '../comms/app-apiCenter';

const Msg = widget.Message;



var healthCheckUtil = {
    getStatusCN: function(is_used){
        if(is_used === true){
            return '已启用'
        }

        if(is_used === false){
           return '已禁用'
        }

        return '未设置'
    }
}


/*
获取当前应用的健康监测信息
  
*/
widget.define('HealthCheckInfo', {
  _defaultOption:{
      tpl:'<div style="overflow:hidden;">'+
            '<form class="form-horizontal">'+
              '<div class="form-group">'+
                '<label for="inputEmail3" class="col-sm-4 control-label">状态:</label>'+
                '<div class="col-sm-8">'+
                  '<p class="form-control-static js-status">已生效</p>'+
                '</div>'+
              '</div>'+
              // '<div class="form-group">'+
              //   '<label for="inputPassword3" class="col-sm-4 control-label">探针模式:</label>'+
              //   '<div class="col-sm-8">'+
              //     '<p class="form-control-static js-model"></p>'+
              //   '</div>'+
              // '</div>'+
              '<div class="form-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label">检测端口:</label>'+
               '<div class="col-sm-8">'+
                  '<p class="form-control-static js-port"></p>'+
                '</div>'+
              '</div>'+
              '<div class="form-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label">探针使用协议:</label>'+
                '<div class="col-sm-8">'+
                  '<p class="form-control-static js-protocol">tcp</p>'+
                '</div>'+
              '</div>'+
              '<div class="form-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label">http请求头:</label>'+
                '<div class="col-sm-8">'+
                  '<p class="form-control-static js-headers"></p>'+
                '</div>'+
              '</div>'+
              '<div class="form-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label">路径:</label>'+
                '<div class="col-sm-8">'+
                  '<p class="form-control-static js-path"></p>'+
                '</div>'+
              '</div>'+
              // '<div class="form-group">'+
              //   '<label for="inputPassword3" class="col-sm-4 control-label">cmd命令</label>'+
              //   '<div class="col-sm-8">'+
              //     '<p class="form-control-static js-cmd"></p>'+
              //   '</div>'+
              // '</div>'+
              '<div class="form-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label">初始化等候时间:</label>'+
                '<div class="col-sm-8">'+
                  '<p class="form-control-static"><span class="js-wait">3000</span> 秒</p>'+
                '</div>'+
              '</div>'+
              '<div class="form-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label">检测间隔时间:</label>'+
                '<div class="col-sm-8">'+
                  '<p class="form-control-static"><span class="js-interval"></span> 秒</p>'+
                '</div>'+
              '</div>'+
               '<div class="form-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label">检测超时时间:</label>'+
                '<div class="col-sm-8">'+
                  '<p class="form-control-static"><span class="js-timeout">3000</span> 秒</p>'+
                '</div>'+
              '</div>'+
              '<div class="form-group js-failTimes-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label">连续错误次数:</label>'+
                '<div class="col-sm-8">'+
                  '<p class="form-control-static"><span class="js-failTimes"></span></p>'+
                '</div>'+
              '</div>'+
              '<div class="form-group js-successTimes-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label">连续成功次数:</label>'+
                '<div class="col-sm-8">'+
                  '<p class="form-control-static"><span class="js-successTimes"></span></p>'+
                '</div>'+
              '</div>'+
            '</form>'+
        '</div>',
      data: {
         is_used: '',
         mode: '',
         port: '',
         //协议
         scheme:'',
         http_header: '',
         path: '',
         cmd: '',
         //初始化等候时间
         initial_delay_second: '',
         //间隔时间
         period_second: '',
         //超时时间
         timeout_second: '',
         //运行时检测错误次数
         failure_threshold:3,
         //启动时检测成功次数
         success_threshold:3
      }
  },
  _init:function(option) {
     this.callParent(option);
     this._create();
  },
  _create:function(option) {
      this.callParent(option);
      this.$status = this.element.find('.js-status');
      this.$model = this.element.find('.js-model');
      this.$port = this.element.find('.js-port');
      this.$protocol = this.element.find('.js-protocol');
      this.$headers = this.element.find('.js-headers');
      this.$path = this.element.find('.js-path');
      this.$wait = this.element.find('.js-wait');
      this.$interval = this.element.find('.js-interval');
      this.$timeout = this.element.find('.js-timeout');
      this.$cmd = this.element.find('.js-cmd');
      this.$failtTimes = this.element.find('.js-failTimes');
      this.$successTimes = this.element.find('.js-successTimes');
      this.$failtTimesGroup = this.element.find('.js-failTimes-group');
      this.$successTimesGroup = this.element.find('.js-successTimes-group');
      this.setValue(this.option.data);

  },
  setValue:function(data) {
    

     this.data = $.extend(true, {}, this.data||{}, data || {});
     this.$status.html(healthCheckUtil.getStatusCN(this.data.is_used));
     this.$model.html(this.data.mode);
     this.$port.html(this.data.port);
     this.$protocol.html(this.data.scheme);
     this.$headers.html(this.data.http_header.replace(/=/g, ':'));
     this.$path.html(this.data.path);
     this.$wait.html(this.data.initial_delay_second);
     this.$interval.html(this.data.period_second);
     this.$timeout.html(this.data.timeout_second);
     this.$failtTimes.html(this.data.failure_threshold);
     this.$successTimes.html(this.data.success_threshold);
     this.$cmd.html(this.data.cmd);

     if(this.data.scheme === 'tcp'){
         this.$headers.parents('.form-group').hide();
         this.$path.parents('.form-group').hide();
     }

     //启动时
     if(this.data.mode === 'readiness'){
         this.$failtTimesGroup.hide();
         this.$successTimesGroup.show();
     //运行时
     }else if(this.data.mode === 'liveness'){
         this.$failtTimesGroup.show();
         this.$successTimesGroup.hide();
     }
  }
})


widget.define('HealthCheckForm', {
  _defaultOption:{
      tpl:'<div class="edit" style="overflow:hidden;">'+
            '<form class="form-horizontal">'+
              '<div class="form-group">'+
                '<label for="inputEmail3" class="col-sm-4 control-label">状态:</label>'+
                '<div class="col-sm-8">'+
                  '<p class="form-control-static js-status"></p>'+
                '</div>'+
              '</div>'+
              // '<div class="form-group">'+
              //   '<label for="inputPassword3" class="col-sm-4 control-label">探针模式:</label>'+
              //   '<div class="col-sm-8">'+
              //     '<p class="form-control-static js-model">readiness</p>'+
              //   '</div>'+
              // '</div>'+
              '<div class="form-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label"><span class="text-danger">*</span>检测端口:</label>'+
                '<div class="col-sm-8">'+
                   '<select class="form-control js-port" style="width:150px">'+
                   '</select>'+
                '</div>'+
              '</div>'+
              '<div class="form-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label"><span class="text-danger">*</span>探针使用协议:</label>'+
                '<div class="col-sm-8">'+
                  '<label class="radio-inline fm-radio">'+
                    '<input class="js-protocol" type="radio" name="scheme" value="tcp">'+
                    '<span class="radio-bg"></span>'+
                    'tcp'+
                  '</label>'+
                  '<label class="radio-inline fm-radio">'+
                    '<input class="js-protocol" type="radio" name="scheme" value="http">'+
                    '<span class="radio-bg"></span>'+
                    'http'+
                  '</label>'+
                  // '<label class="radio-inline fm-radio">'+
                  //   '<input class="js-protocol" type="radio" name="scheme" value="cmd">'+
                  //   '<span class="radio-bg"></span>'+
                  //   'cmd'+
                  // '</label>'+
                '</div>'+
              '</div>'+
              '<div class="form-group  js-headers-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label">http请求头:</label>'+
                '<div class="col-sm-8 js-header-wrap">'+
                  '<div class="form-inline js-header-row">'+
                      '<input type="text" style="width:90px" name="name" class="form-control" placeholder="name">'+
                      '<span style="margin:0 10px">:</span>'+
                      '<input type="text" name="value" style="width:200px" class="form-control" placeholder="value">'+
                      '<button style="margin-left:10px" type="button" class="btn btn-sm btn-default js-plusHeader">'+
                      '<span class="glyphicon glyphicon-plus" aria-hidden="true"></span>'+
                    '</button>'+
                  '</div>'+
                '</div>'+
              '</div>'+
              '<div class="form-group js-path-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label"><span class="text-danger">*</span>路径:</label>'+
                '<div class="col-sm-8">'+
                  '<input type="text" class="js-path form-control" name="path" style="width:260px"  placeholder="响应码2xx、3xx为正常" />'+
                '</div>'+
              '</div>'+
              '<div class="form-group js-cmd-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label"><span class="text-danger">*</span>cmd命令:</label>'+
                '<div class="col-sm-8">'+
                  '<input type="text" class="js-cmd form-control" name="path" style="width:260px"  placeholder="请填写cmd命令" />'+
                '</div>'+
              '</div>'+
              '<div class="form-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label"><span class="text-danger">*</span>初始化等候时间:</label>'+
                '<div class="col-sm-8">'+
                   '<div class="form-inline">'+
                      '<input type="text" class="js-wait form-control" name="path" style="width:260px"  placeholder="" /> '+
                      '秒'+
                  '</div>'+
                '</div>'+
              '</div>'+
              '<div class="form-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label"><span class="text-danger">*</span>检测间隔时间:</label>'+
                '<div class="col-sm-8">'+
                   '<div class="form-inline">'+
                      '<input type="text" class="js-interval form-control" name="path" style="width:260px"   placeholder="" /> '+
                      '秒'+
                  '</div>'+
                '</div>'+
              '</div>'+
               '<div class="form-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label"><span class="text-danger">*</span>检测超时时间:</label>'+
                '<div class="col-sm-8">'+
                  '<div class="form-inline">'+
                      '<input type="text" class="js-timeout form-control" name="path" style="width:260px"  placeholder="" /> '+
                      '秒'+
                  '</div>'+
                '</div>'+
              '</div>'+
              '<div class="form-group js-failTimes-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label"><span class="text-danger">*</span>连续错误次数:</label>'+
                '<div class="col-sm-8">'+
                  '<div class="form-inline">'+
                      '<input style="width:260px"  type="text" class="js-failTimes form-control" name="failTimes" /> '+
                      '<i style="color: #28cb75;font-size:18px;" class="fa fa-info-circle" title="以指定的时间间隔连续以指定次数进行健康检测，若检测有失败则系统重新启动应用"></i>'+
                  '</div>'+
                '</div>'+
              '</div>'+
              '<div class="form-group js-successTimes-group">'+
                '<label for="inputPassword3" class="col-sm-4 control-label"><span class="text-danger">*</span>连续成功次数:</label>'+
                '<div class="col-sm-8">'+
                  '<div class="form-inline">'+
                      '<input type="text" style="width:260px" class="js-successTimes form-control" name="successTimes" /> '+
                      '<i style="color: #28cb75;font-size:18px;" class="fa fa-info-circle" title="以指定的时间间隔连续以指定次数进行健康检测，若检测均成功则系统启动应用"></i>'+
                  '</div>'+
                '</div>'+
              '</div>'+
            '</form>'+
        '</div>',
      headerRowTpl: '<div class="form-inline js-header-row">'+
                      '<input type="text" style="width:90px" name="name" class="form-control" placeholder="name">'+
                      '<span style="margin:0 10px">:</span>'+
                      '<input type="text" name="value" style="width:200px" class="form-control" placeholder="value">'+
                      '<button style="margin-left:10px" type="button" class="btn btn-sm btn-default js-minusHeader">'+
                      '<span class="glyphicon glyphicon-minus" aria-hidden="true"></span>'+
                    '</button>'+
                  '</div>',
      //要选择的端口列表
      ports:'',
      data: {
         is_used: '',
         mode: '',
         port: '',
         //协议
         scheme:'',
         http_header: '',
         path: '',
         cmd: '',
         //初始化等候时间
         initial_delay_second: 2,
         //间隔时间
         period_second: 3,
         //超时时间
         timeout_second: 20,
         //运行时检测错误次数
         failure_threshold:3,
         //启动时检测成功次数
         success_threshold:1
      }
  },
  _init:function(option) {
     this.callParent(option);
     


     this._create();
     this.bind();
  },
  _create:function(option) {
      this.callParent(option);
      this.$status = this.element.find('.js-status');
      this.$model = this.element.find('.js-model');
      this.$port = this.element.find('.js-port');
      this.$protocol = this.element.find('.js-protocol');
      this.$headers = this.element.find('.js-headers');
      this.$path = this.element.find('.js-path');
      this.$wait = this.element.find('.js-wait');
      this.$interval = this.element.find('.js-interval');
      this.$timeout = this.element.find('.js-timeout');
      this.$cmd = this.element.find('.js-cmd');
      this.$headersWrap = this.element.find('.js-header-wrap');
      this.$headerGroup = this.element.find('.js-headers-group');
      this.$pathGroup = this.element.find('.js-path-group');
      this.$cmdGroup = this.element.find('.js-cmd-group');
      this.$failTimes = this.element.find('.js-failTimes');
      this.$successTimes = this.element.find('.js-successTimes');
      this.$failtTimesGroup = this.element.find('.js-failTimes-group');
      this.$successTimesGroup = this.element.find('.js-successTimes-group');



      //运行时
      if(this.option.mode === 'liveness'){
         this.option.data.initial_delay_second = 20;
      }
      this.setValue(this.option.data);

      //渲染端口
      this.renderPort(this.option.ports);
  },
  setProtocolValue: function(value){
    this.data.scheme = value;
    this.$protocol.each(function(){
         if($(this).val() === value){
             $(this)[0].checked = true;
         }
    })
    this.onProtocolChange();
  },
  onProtocolChange: function() {
     var protocol = this.data.scheme;
      if(protocol === 'tcp'){
          this.$cmdGroup.hide();
          this.$pathGroup.hide();
          this.$headerGroup.hide();
      }else if(protocol === 'http'){
          this.$cmdGroup.hide();
          this.$pathGroup.show();
          this.$headerGroup.show();
      }else if(protocol === 'cmd') {
          this.$cmdGroup.show();
          this.$pathGroup.hide();
          this.$headerGroup.hide();
      }
  },
  getPortType: function(port){
    for(var i=0;i<this.option.ports.length;i++){
       if(this.option.ports[i].container_port == port){
          return this.option.ports[i].protocol
       }
    }
  },
  onPortChange: function(port){
      var type = this.getPortType(port);
      if(type == 'http'){
           this.element.find('[value=http]').parent().show();
      }else{
          this.element.find('[value=http]').parent().hide();
          this.setProtocolValue('tcp');
      }
  },
  setValue:function(data) {
     this.data = $.extend(true, {}, this.data||{}, data || {});
     this.$status.html(healthCheckUtil.getStatusCN(this.data.is_used));
     this.$model.html(this.data.mode);
     this.$port.val(this.data.port);
     this.setProtocolValue(this.data.scheme);
     this.setHeaderValue(this.data.http_header);
     this.$path.val(this.data.path);
     this.$wait.val(this.data.initial_delay_second);
     this.$interval.val(this.data.period_second);
     this.$timeout.val(this.data.timeout_second);
     this.$cmd.val(this.data.cmd);
     this.$failTimes.val(this.data.failure_threshold);
     this.$successTimes.val(this.data.success_threshold);

     //启动时
     if(this.data.mode === 'readiness'){
         this.$failtTimesGroup.hide();
         this.$successTimesGroup.show();
     //运行时
     }else if(this.data.mode === 'liveness'){
         this.$failtTimesGroup.show();
         this.$successTimesGroup.hide();
     }
     this.onPortChange(this.data.port);
  },
  setHeaderValue:function(headers){
     var $headerRows = this.element.find('.js-header-row');
     headers = headers||'';
     headers = headers.split(',');
     if(headers.length){
        var headersFirst = headers.shift();
        $headerRows.eq(0).find('[name=name]').val(headersFirst.split('=')[0]);
        $headerRows.eq(0).find('[name=value]').val(headersFirst.split('=')[1]);

     }
     for(var i=0,len=headers.length;i<len;i++){
        var head = headers[i].split('=');
        this.addHeaderRow(head[0], head[1]);
     }
  },
  check:function(){
      var data = this.getValue();
      var scheme = data.scheme;
      var Message = gWidget.Message;
      if(scheme === 'tcp') {

      }else if(scheme === 'http'){
        if(!$.trim(data.path)){
            Message.warning('请填写路径');
            return false;
        }
      }

      if(!data.initial_delay_second){
          Message.warning('请填写初始化等候时间');
          return false;
      }

      if(!/^[1-9]+\d*$/.test(data.initial_delay_second)){
          Message.warning('初始化等候时间格式不正确，只能为正整数');
          return false;
      }

      if(!data.period_second){
          Message.warning('请填写检测间隔时间');
          return false;
      }

      if(!/^[1-9]+\d*$/.test(data.period_second)){
          Message.warning('检测间隔时间格式不正确，只能为正整数');
          return false;
      }

      if(!data.timeout_second){
          Message.warning('请填写检测超时时间');
          return false;
      }

      if(!/^[1-9]+\d*$/.test(data.timeout_second)){
          Message.warning('检测超时时间格式不正确，只能为正整数');
          return false;
      }

      //启动时
     if(this.data.mode === 'readiness'){

        if(!data.success_threshold){
          Message.warning('请填写检测成功次数');
          return false;
        }

        if(!/^(1|2|3){1}$/.test(data.success_threshold)){
            Message.warning('检测成功次数只能为1到3的正整数');
            return false;
        }

         
     //运行时
     }else if(this.data.mode === 'liveness'){
          
       if(!data.failure_threshold){
          Message.warning('请填写检测错误次数');
          return false;
        }

        if(!/^(1|2|3){1}$/.test(data.failure_threshold)){
            Message.warning('检测错误次数只能为1到3的正整数');
            return false;
        }

     }

     return true;
  },
  //获取cmd的值
  getCmdValue: function() {
     return this.$cmd.val();
  },
  //获取初始化等候时间的值
  getInitialValue: function() {
     return this.$wait.val();
  },  
  //获取间隔时间的值
  getIntervalValue: function() {
     return this.$interval.val();
  },  
  //获取超时时间的值
  getTimeoutValue: function() {
     return this.$timeout.val();
  },
  //获取端口的值
  getPortValue:function() {
     return this.$port.val();
  },
  //获取路径的值
  getPathValue:function() {
     return this.$path.val();
  },
  //获取协议的值
  getSchemeValue:function() {
     return this.element.find('[name=scheme]:checked').val();
  },
  //获取请求头的值
  getHeaderValue:function() {
      var headers=[], $headerRows = this.element.find('.js-header-row');
      $headerRows.each(function() {
          var name = $.trim($(this).find('[name=name]').val());
          var value = $.trim($(this).find('[name=value]').val());
          if(name && value){
              headers.push(name+'='+value);
          }
      })
      return headers.join(',')
  },
  getFailTimes: function() {
    return this.$failTimes.val();
  },
  getSuccesTimes: function() {
    return this.$successTimes.val();
  },
  getValue:function(){
     var data = {};
     data.id = this.data.probe_id;
     data.mode = this.data.mode;
     data.scheme=this.getSchemeValue();

     if(data.scheme === 'http'){
        data.http_header = this.getHeaderValue();
        data.path = this.getPathValue();
     }

     data.port = this.getPortValue();
     data.initial_delay_second = this.getInitialValue();
     data.period_second = this.getIntervalValue();
     data.timeout_second= this.getTimeoutValue();
     //data.cmd = this.getCmdValue();
     if(data.mode === 'readiness'){
       data.success_threshold = this.getSuccesTimes();
     }else if(data.mode === 'liveness'){
       data.failure_threshold = this.getFailTimes();
     }
     return data;
  },
  addHeaderRow:function(name, value){
     var $row = $(this.option.headerRowTpl);
     if(name && value){
        $row.find('[name=name]').val(name);
        $row.find('[name=value]').val(value);
     }
     this.$headersWrap.append($row);
  },
  renderPort:function(ports = []){
     var html = [];
     for(var i=0,len=ports.length;i<len;i++){
        html.push('<option value="'+ports[i].container_port+'">'+ports[i].container_port+'</option>')
     }
     this.$port.html(html.join(''));
  },
  bind:function(){
    var self =this;
    this.element.delegate('.js-plusHeader', 'click', function(e){
       self.addHeaderRow();
    })

    this.element.delegate('.js-minusHeader', 'click', function(e){
       $(this).parents('.js-header-row').remove();
    })

    this.element.delegate('.js-protocol', 'change', function(e){
         var value = self.element.find('[name=scheme]:checked').val();
         self.setProtocolValue(value);
    })

    this.element.delegate('.js-port', 'change', function(e){
         var value = self.element.find('.js-port').val();
         self.onPortChange(value);
    })
  }
})



  widget.define('viewAndEditStartHealthCheck', {
    _defaultOption:{
        tpl:'<div></div>',
        width:'700px',
        height: '500px',
        viewTitle:'启动时监测',
        editTitle: '请设置对启动时检测的具体要求',
        serviceAlias:'',
        tenantName:'',
        port:'',
        mode:'',
        onAddSuccess:function(){

        },
        onEditSuccess:function(){

        },
        data:{

        }
    },
    _init:function(option){
      var self = this;
      this.callParent(option);
      //判断是否已经设置， 如果没有就要添加
      this.ok = false;
      getHealthCheckInfo(
        this.option.tenantName, 
        this.option.serviceAlias, 
        this.option.mode
        ).done(function(data){
          self._create();
          self.bind();
          self.ok = true;
          self.changeToView();
          self.healthCheckInfo.setValue(data.body.bean);
          self.healthCheckForm.setValue(data.body.bean);
      }).fail(function(data, ajaxInfo){
          if(data.code == 404) {
             self._create();
             self.bind();
             self.changeToAdd();
          }else{
            Msg.warning(data.msgcn || '操作异常');
          }
      })
      
    },
    _create:function(option){
      var self = this;
      this.callParent(option);
      //弹框
      this.dialog = gWidget.create('dialog', {
          id:'dialog-run',
          classes: 'healthCheck-dialog',
          title: this.option.viewTitle,
          width: this.option.width,
          height: this.option.height,
          event: {
            afterHide: function() {
              self.destroy();
            }
          },
          btns:[{
            text: '编辑',
            classes: 'btn btn-success btn-edit'
          },{
            text: '保存',
            classes: 'btn btn-success btn-save'
          },{
            text: '关闭',
            classes: 'btn btn-default btn-cancel'
          },{
            text: '返回',
            classes: 'btn btn-default btn-back'
          }]
      })


      //查看组件
      this.healthCheckInfo = gWidget.create('HealthCheckInfo', {});
      //编辑组件
      this.healthCheckForm = gWidget.create('HealthCheckForm', {
        ports: this.option.port,
        mode: this.option.mode
      });
      this.dialog.appendContent(this.healthCheckInfo.getElement());
      this.dialog.appendContent(this.healthCheckForm.getElement());
    },
    show:function() {
      this.dialog.show();
      
    },
    handleEdit:function() {
      var self = this;
      if(!this.healthCheckForm.check()){
        return;
      }

     var data = this.healthCheckForm.getValue();
     var url = '/ajax/'+this.option.tenantName+'/'+this.option.serviceAlias+'/probe/'+data.id;
     delete data.id;
     http2({
        url:url,
        type:'post',
        data:data
     }).done(function(data){
        if(data.code >= 200 && data.code < 300){
            self.option.onEditSuccess();
            self.destroy();
        }else{
            Msg.warning(data.msgcn || '操作异常');
        }
     })
    },
    handleAdd:function() {
      var self = this;
      if(!this.healthCheckForm.check()){
        return;
      }

      var data = this.healthCheckForm.getValue();
      var url = '/ajax/'+this.option.tenantName+'/'+this.option.serviceAlias+'/probe';

      http2({
          url:url,
          type:'post',
          data:data
      }).done(function(data){
        if(data.code >= 200 && data.code < 300){
          self.option.onAddSuccess(data);
          self.destroy();
        }else{
          Msg.warning(data.msgcn || '操作异常');
        }
      })
        
    },
    hide: function() {
      this.dialog.hide();
    },
    changeToView:function(){
      var element = this.dialog.getElement();
      element.find('.btn-save').hide();
      element.find('.btn-back').hide();
      element.find('.btn-edit').show();
      element.find('.btn-cancel').show();
      this.healthCheckInfo.show();
      this.healthCheckForm.hide();
      this.dialog.setTitle(this.option.viewTitle);
    },
    changeToAdd:function(){
       var element = this.dialog.getElement();
       element.find('.btn-cancel').show();
       element.find('.btn-edit').hide();
       element.find('.btn-save').show();
       element.find('.btn-back').hide();
       this.healthCheckInfo.hide();
       this.healthCheckForm.show();
       var port = this.option.port[0].container_port;
       this.healthCheckForm.setValue({mode: this.option.mode, port:this.option.port[0].container_port});
       this.dialog.setTitle(this.option.editTitle);
    },
    changeToEdit:function(){
       var element = this.dialog.getElement();
       element.find('.btn-cancel').hide();
       element.find('.btn-edit').hide();
       element.find('.btn-save').show();
       element.find('.btn-back').show();
       this.healthCheckInfo.hide();
       this.healthCheckForm.show();
       this.dialog.setTitle(this.option.editTitle);
    },
    destroy:function(){
       this.healthCheckInfo.destroy();
       this.healthCheckForm.destroy();
       this.dialog.destroy();
       this.dialog = this.healthCheckInfo = this.healthCheckForm = null;

    },
    bind:function(){
       var self = this;
       var element = this.dialog.getElement();
       element.delegate('.btn-edit', 'click', function(e){
          self.changeToEdit();
       })
       element.delegate('.btn-save', 'click', function(e){
          if(!self.ok){
             self.handleAdd();
          }else{
            self.handleEdit();
          }
       })

       element.delegate('.btn-back', 'click', function(e){
           self.changeToView();
       })
    }
 })