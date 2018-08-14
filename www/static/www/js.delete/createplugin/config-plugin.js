/*****************


    util start

*****************/



//是否是昨天
function isToday(str) {
    var d = new Date(str);
    var todaysDate = new Date();
    if (d.setHours(0, 0, 0, 0) == todaysDate.setHours(0, 0, 0, 0)) {
        return true;
    } else {
        return false;
    }
}


//是否昨天
function isYestday(date){
    var d = new Date(date);
    var date = (new Date());    //当前时间
    var today = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime(); //今天凌晨
    var yestday = new Date(today - 24*3600*1000).getTime();
    return d.getTime() < today && yestday <= d.getTime();
}
//是否是前天
function isBeforeYestday(date){
    var d = new Date(date);
    var date = (new Date());    //当前时间
    var today = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime(); //今天凌晨
    var yestday = new Date(today - 24*3600*1000).getTime();
    var beforeYestday = new Date(today - 48*3600*1000).getTime();
    return d.getTime() < yestday && beforeYestday <= d.getTime();
}


function getShowData(date){
    if(isToday(date)){
        return '今天';
    }else if(isYestday(date)){
        return '昨天';
    }else if(isBeforeYestday(date)){
        return '前天';
    }
    return date;
}


function Queue(){
    this.datas = [];
}
Queue.prototype = {
    constructor:Queue,
    push:function(data){
        if(data !== void 0){
            this.datas.push(data);
        }
    },
    shift:function(){
        return this.datas.shift();
    },
    getCount:function(){
        return this.datas.length;
    },
    empty:function(){
        return this.datas.length === 0;
    }
}


function TimerQueue(option) {
    option = option || {};
    this.queue = new Queue();
    this.timer = null;
    this.isStarted = false;
    this.interval = option.interval || 300;
    this.onExecute = option.onExecute || util.noop;
}
TimerQueue.prototype = {
    add: function (data) {
        this.queue.push(data)
        if (!this.isStarted) {
            this.start();
        }
    },
    start: function () {
        var self = this;
        this.timer = setInterval(function () {
            if (!self.queue.empty()) {
                self.execute();
            } else {
                self.stop();
            }
        }, this.interval)
    },
    stop: function () {
        this.isStarted = false;
        clearInterval(this.timer);
    },
    execute: function () {
        this.onExecute(this.queue.shift());
    }
}



function LogSocket(option){
    option = option || {};
    this.url = option.url;
    this.eventId = option.eventId;
    this.onOpen = option.onOpen || noop;
    this.onMessage = option.onMessage || noop;
    this.onError = option.onError || noop;
    this.onClose = option.onClose || noop;
    this.onError = option.onError || noop;
    this.onSuccess = option.onSuccess || noop;
    this.onComplete = option.onComplete || noop;
    this.onFail = option.onFail || noop;
    this.webSocket = new WebSocket(this.url);
    this.webSocket.onopen = this._onOpen.bind(this);
    this.webSocket.onmessage = this._onMessage.bind(this);
    this.webSocket.onclose = this._onClose.bind(this);
    this.webSocket.onerror = this._onError.bind(this);
    this.timerQueue = new TimerQueue({
        onExecute:this.onMessage
    })
}

LogSocket.prototype = {
    constructor: LogSocket,
    getSocket: function() {
        return this.webSocket;
    },
    close: function(){
        this.webSocket.close();
    },
    _onOpen: function(evt) {
        this.webSocket.send("event_id=" + this.eventId);
        this.onOpen();
    },
    _onMessage: function(evt) {

        //代表连接成功， 不做任何处理
        if(evt.data === 'ok'){

        }else{
            var data = JSON.parse(evt.data);
            this.timerQueue.add(data);
            //判断是否最后一步
            if (data.step == "callback" || data.step == "last") {
               
                if(data.status === 'success'){
                    this.timerQueue.add({success: true});
                    this.onSuccess();
                }else{
                    this.timerQueue.add({fail: true});
                    this.onFail();
                }
                this.onComplete(data);
                this.webSocket.close();
                this.webSocket = null;
            }
        }

    },
    _onClose: function(evt) {
        this.onClose();
    },
    _onError: function() {
        this.onError();
    }
}

function beautifulJSON(jsonString){
    return jsonString.replace(/\"([^"]+)\":/g, "<span style='color:#92278f'>\"$1\"</span>:").replace(/\: (\"?([^:|^\n|^\[|^{|^]|^}])*\"?\n)/g, ": <span style='color:#3ab54a'>$1</span>")
}


/*****************


    util end

*****************/






/*****************


    api start

*****************/


/*
    获取插件版本构建历史
*/
function getBuildHistory(tenantName, plugin_id, page, page_size){
    return http({
        url:"/ajax/"+tenantName+"/plugin/"+plugin_id+"/build-history",
        type: 'get',
        data:{
            page: page || 1,
            page_size: page_size || 10
        }
    })
}





/*
    获取某条构建历史的日志
    level "debug | error | info"
*/
function getBuildlog(tenantName, plugin_id, build_version, level){
    return http({
        url:"/ajax/"+tenantName+"/plugin/"+plugin_id+"/version/"+build_version+"/event-log",
        type: 'get',
        data:{
            level: level || 'info'
        }
    })
}


/*
    构建版本
*/
function buildVersion(tenantName, plugin_id, build_version, info){
    return http({
        url:"/ajax/"+tenantName+"/plugin/"+plugin_id+"/version/"+build_version+'/manage',
        type:'post',
        data:JSON.stringify({
            update_info: info
        })
    })
}


/*
     删除版本
*/
function deleteVersion(tenantName, plugin_id, build_version, info){
    return http({
        url:"/ajax/"+tenantName+"/plugin/"+plugin_id+"/version/"+build_version+'/manage',
        type:'delete'
    })
}


/*
    查看某个版本的状态
*/
function getVersionStatus(tenantName, plugin_id, build_version){
    return http({
        url:"/ajax/"+tenantName+"/plugin/"+plugin_id+"/version/"+build_version+'/status',
        type:'get',
        showLoading: false,
        multiple: true

    })
}

/*
    查看某个版本的配置信息
*/
function getVersionConfig(tenantName, plugin_id, build_version){
    return http({
        url:"/ajax/"+tenantName+"/plugin/"+plugin_id+"/version/"+build_version+'/config',
        type:'get'
    })
}

/*
    添加配置
*/

function addConfig(tenant_name, plugin_id, version, data){
    return http({
        url: '/ajax/'+tenant_name+'/plugin/'+plugin_id+'/version/'+version+'/config',
        type: 'post',
        data: JSON.stringify(data)
    })
}

/*
    删除配置
*/

function deleteConfig(tenant_name, plugin_id, version, config_group_id){
    return http({
        url: '/ajax/'+tenant_name+'/plugin/'+plugin_id+'/version/'+version+'/config',
        type: 'delete',
        data:{
            ID: config_group_id
        }
    })
}

/*
    修改配置
*/

function editConfig(tenant_name, plugin_id, version, data){
    return http({
        url: '/ajax/'+tenant_name+'/plugin/'+plugin_id+'/version/'+version+'/config',
        type: 'put',
        data:JSON.stringify(data)
    })
}


/*
    获取配置json字符串
*/
function getConfigJson(tenant_name, plugin_id, version){
    return http({
        url: '/ajax/'+tenant_name+'/plugin/'+plugin_id+'/version/'+version+'/config/preview',
        type: 'get'
    })
}



/*****************

    api end

*****************/


/*****************

    art-template util start

*****************/


/*
    模板过滤器
*/
template.defaults.imports.typecn = function(val){
    if(val === 'string'){
        return '字符串'
    }else if(val === 'radio'){
        return '单选'
    }else if(val === 'checkbox'){
        return '多选'
    }else{
        return '';
    }
};



/*
    模板过滤器
*/
var statusMap = {
    'building' : {
        text: '构建中'
    },
    'build_fail': {
        text: '构建失败'
    },
    'build_success': {
        text: '构建成功'
    },
    'unbuild': {
        text: '未构建'
    },
    'time_out': {
        text: '构建超时'
    }
}

template.defaults.imports.buildstatuscn = function(val){
    var map = statusMap[val];
    return map ? map.text : '未知'
};


template.defaults.imports.grouptypecn = function(val){
    if(val === 'downstream_port'){
        return '下游服务端口'
    }else if(val === 'upstream_port'){
        return '端口'
    }else if(val === 'un_define'){
        return '默认'
    }else{
        return '';
    }
};

template.defaults.imports.injectiontypecn = function(val){
    if(val === 'auto'){
        return '主动发现'
    }else if(val === 'env'){
        return '环境变量'
    }else{
        return '';
    }
};

/*****************

    art-template util end

*****************/









/*********** widget ***************/

//好看版本日志
gWidget.define('viewVersionLog', {
    extend: 'dialog',
    _defaultOption:{
        title: '构建日志',
        width: '600px',
        height: '400px',
        eventId: '',
        tenantName: '',
        plugin_id: '',
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'viewVersionLog'){
            this._create();
            this.bind();
        }
    },
    _create:function(option){
        this.callParent();
        var self = this;
        
        

        getVersionStatus(
            this.option.tenantName,
            this.option.plugin_id,
            this.option.version
        ).done(function(data) {
            var status = data.bean.status;
            var eventId = data.bean.event_id;
        
            if(status === 'building' && eventId){
                self.appendContent('<div class="version-log" style="max-height:260px;overflow:auto;"></div>');
                var msgHtml = self.renderBuildLog([{message: '开始构建，等待日志信息推送...'}]);
                self.element.find('.version-log').prepend(msgHtml);
                self.loadBuildLog(
                    self.option.version,
                    'info'
                ).done(function(){
                    
                    self.socket =  new LogSocket({
                        url: $("#web_socket_url").val(),
                        eventId: eventId,
                        onMessage: function(data){
                            var msgHtml = self.renderBuildLog([data]);
                            self.element.find('.version-log').prepend(msgHtml);
                        },
                        onClose: function() {
                            
                        },
                        onSuccess: function(data) {
                            
                        },
                        onFail: function(data) {
                            
                        },
                        onComplete: function(data){
                            self.scoket = null;
                        }
                    })
                }) 
            }else{
                self.appendContent('<ul class="nav nav-tabs">'+
                  '<li data-log="info" role="presentation" class="active"><a href="javascript:;">Info日志</a></li>'+
                  '<li data-log="debug" role="presentation"><a href="javascript:;">Debug日志</a></li>'+
                  '<li data-log="error" role="presentation"><a href="javascript:;">Error日志</a></li>'+
                '</ul><div class="version-log" style="max-height:200px;overflow:auto;"></div>');
                self.loadBuildLog(
                    self.option.version,
                    'info'
                )
            }
            

            
        })
        
    },
    //加载某条构建历史的log
    loadBuildLog: function(version, action){
        var self = this;
        return getBuildlog(
            this.option.tenantName,
            this.option.plugin_id,
            version,
            action
        ).done(function(data){
            var html = self.renderBuildLog(data.list || [])
            self.element.find('.version-log').prepend(html);
        })
    },
    //选择某条日志详情
    renderBuildLog: function(datas){
        var html = [];
        for(var i=0;i<datas.length;i++){
            var data = datas[i];


            if(data.success === true){
                html.unshift('<div class="text-success" style="font-size:18px">构建成功，结束</div>');
            }else if(data.fail === true){
                html.unshift('<div class="text-danger" style="font-size:18px">构建失败，结束</div>');
            }else{
                try{
                    var arr = data.time.split('.')[0];
                    var time1 = arr.split('T')[0];
                    var time2 = arr.split('T')[1].split('Z')[0];
                    var time3 = time2.split('+')[0];
                    html.unshift("<div class='clearfix'><span class='log_time'>" + time3 + "</span><span class='log_msg'> " + data.message + "</span></div>");
                }catch(e){
                    html.unshift("<div class='clearfix'><span class='log_msg'> " + data.message + "</span></div>");
                }
            }
            
        }

        return html.join('');
        
    },
    bind:function(){
        this.callParent();
        var self = this;
        this.element.delegate('.nav-tabs li', 'click', function(e){
            var build_version = self.option.version;
            var action = $(this).attr('data-log');
            if(build_version){
                self.element.find('.nav-tabs li').removeClass('active');
                $(this).addClass('active');
                self.loadBuildLog(build_version, action);
            }else{
                Msg.warning("该条数据异常，暂时无法查看详情")
            }
        })
    }
})

/*********** widget ***************/







/*****************

    main start

*****************/

//生成日志条目dom字符串
function createLogTmp(data){
    var html = '';
    try{
        var arr = data.time.split('.')[0];
        var time1 = arr.split('T')[0];
        var time2 = arr.split('T')[1].split('Z')[0];
        var time3 = time2.split('+')[0];
        html = "<p class='clearfix'><span class='log_time'>" + time3 + "</span><span class='log_msg'> " + data.message + "</span></p>";
    }catch(e){
        console.log(e);
    }
    
    return html;
}

function noop(){}
var Msg = gWidget.Message;
gWidget.define('AddConfigItemDialog', {
    extend: 'dialog',
    _defaultOption: {
        id:'AddConfigItemDialog',
        onSuccess: noop,
        onFail: noop,
        onCancel: noop,
        autoDestroy: true,
        width: '830px',
        height:'500px',
        title: '新增配置组'
    },
    _init:function(option){
        var self = this;
        this.callParent(option);
        if(this.ClassName == 'AddConfigItemDialog'){
            this._create();
            this.bind();
        }
    },
    _create: function(){
        this.callParent();
        this.setContent($("#add-config-tpl").html());
        var element = this.getElement();
        
        var data = this.option.data;
        element.find('[name=config_name]').val(data.config_name||'');
        element.find('[value='+data.service_meta_type+']').prop('checked', true);
        element.find('[value='+data.injection+']').prop('checked', true);
        this.onTypeChange();

        if(data.options){
            for(var i=0;i<data.options.length;i++){
                controller.renderConfigItem(this.getElement(), data.options[i]);
            }
        }else{
            controller.renderConfigItem(this.getElement());
        }
        element.find('[name=attr_type]').trigger('change');
        
    },

    getData: function(){
        var element = this.getElement();
        var data = this.option.data;
        data.config_name = $.trim(element.find('[name=config_name]').val());
        data.service_meta_type = element.find('[name=service_meta_type]:checked').val();
        data.injection = element.find('[name=injection]:checked').val();
        data.options = [];

        element.find('.config-item').each(function(index, dom){
            var $dom = $(dom);
            var val = {
                attr_name: $.trim($dom.find('[name=attr_name]').val()),
                attr_type: $.trim($dom.find('[name=attr_type]').val()),
                attr_alt_value: $.trim($dom.find('[name=attr_alt_value]').val()),
                attr_default_value: $.trim($dom.find('[name=attr_default_value]').val()),
                is_change: $.trim($dom.find('[name=is_change]').val()),
                attr_info: $.trim($dom.find('[name=attr_info]').val())
            }
            data.options.push(val);
        })

        return data;
    },
    checkData: function(){
        var data = this.getData();
        if(!data.config_name){
            Msg.warning("请填写配置组名称");
            return false;
        }

        if(!data.options.length){
            Msg.warning("请至少填写一个配置项");
            return false;
        }

        for(var i=0;i<data.options.length;i++){
            var option = data.options[i];
            if(!option.attr_name){
                 Msg.warning("属性名称不能为空");
                return false;
            }

            if(!/^[a-zA-Z]+$/.test(option.attr_name)){
                 Msg.warning("属性名只能为大小写英文");
                return false;
            }
        }


        return true;
    },
    submit: function(){
        if(this.checkData()){

            this.option.onSuccess && this.option.onSuccess(this.getData());
        }
    },
    onTypeChange: function(){
        var element = this.getElement();
        var ctype = element.find('[name=service_meta_type]:checked').val();
        if(ctype == 'un_define'){
            element.find('.env-radio').show();
        }else{
            element.find('.env-radio').hide();
            element.find('[value=auto]')[0].checked = true;
        }
    },
    bind: function(){
        var self = this;
        this.callParent();
        var element = this.getElement();
        //监听事件
        element.delegate('[name=service_meta_type]', 'change', function(){
            self.onTypeChange();
        })

        element.delegate('.add-item', 'click', function(){
           controller.renderConfigItem(element)
        })

        element.delegate('.remove-item', 'click', function(){
           $(this).parents('.config-item').remove();
        })

        element.delegate('.btn-success', 'click', function(){
            self.submit()
        })

        element.delegate('[name=attr_type]', 'change', function(e){
            var val = $(this).val();
            if(val === 'string'){
                $(this).parents('.config-item').find('.attr_value_group').hide()
            }else{
                $(this).parents('.config-item').find('.attr_value_group').show()
            }
        })
    }
})

var controller = {
    init: function(){
        //存放当前版本信息
        this.data = {};
        this.config_group = [];
        this.build_list = [];
        this.page = 1;
        this.page_size = 100;
        this.tenantName = $('#tenantName').val();
        this.pluginId = $('#plugin_id').val();
        this.getPluginInfo();
        this.getBuildHistory();
        this.bind();
    },
    //判断该插件是否是从云市安装过来的
    isMarketPlugin: function(){
        return this.data.origin !== 'source_code';
    },
    addConfig: function(data){
        var self = this;
        var tenantName = $('#tenantName').val();
        var id = $('#plugin_id').val();
        addConfig(
            tenantName,
            id,
            this.data.build_version,
            data
        ).done(function(data){
            Msg.success("添加成功");
            self.getVersionConfig();
        })
    },
    deleteConfig: function(config){
        var self = this;
        var tenantName = $('#tenantName').val();
        var id = $('#plugin_id').val();
        deleteConfig(
            tenantName,
            id,
            this.data.build_version,
            config.ID
        ).done(function(data){
            Msg.success("删除成功");
            self.getVersionConfig();
        })
    },
    editConfig: function(config){
        var self = this;
        var tenantName = $('#tenantName').val();
        var id = $('#plugin_id').val();
        editConfig(
            tenantName,
            id,
            this.data.build_version,
            config
        ).done(function(data){
            Msg.success("修改成功");
            self.getVersionConfig();
        })
    },
    viewConfigJson: function(){
        var tenantName = $('#tenantName').val();
        var id = $('#plugin_id').val();
        var version = this.data.build_version;

        getConfigJson(
            tenantName,
            id,
            version
        ).done(function(data){
            if(data.bean){
                var dialog = gWidget.create('dialog', {
                    title: '预览配置数据',
                    width: '600px',
                    height: '500px',
                    btns:[{
                        text: '关闭',
                        classes: 'btn btn-default btn-cancel'
                    }]
                })
                dialog.setContent('<div style="white-space:pre">'+beautifulJSON(JSON.stringify(data.bean || [], null, 4))+'</div>')
            }else{
                Msg.warning("请先添加配置")
            }
        })
    },
    bind: function(){
        var self = this;
        //新增配置项ß
        $('.add-config').click(function(e){
            var dialog = gWidget.create('AddConfigItemDialog', {
                data:{},
                onSuccess: function(data){
                    self.addConfig(data);
                    dialog.destroy();
                }
            })
        })

        //保存配置
        $('#savePlugin').click(function(e){
            self.savePlugin();
        })

        //构建事件
        $('#buildPuild').click(function(e){
            self.buildPuild();
        })


        $('body').delegate('.del-config-group', 'click', function(e){
            var index = $(this).parents('tr').index();
            var config  = self.config_group[index];
            if(config){
                self.deleteConfig(config)
            }
                
        })

        $('body').delegate('.build-version', 'click', function(e){
            var version = $(this).parents('tr').attr('data-version-id');
            var info = $(this).parents('tr').find('[name=versioin_info]').val();
            if(version){
                self.buildVersion(version, info)
            }
        })


        $('body').delegate('.remove-version', 'click', function(e){
            var version = $(this).parents('tr').attr('data-version-id');
            if(version){
                self.deleteVersion(version)
            }
        })

        $('body').delegate('.view-version-log', 'click', function(e){
            var version = $(this).parents('tr').attr('data-version-id');
            if(version){
                self.viewVersionLog(version);
            }
        })

        $('body').delegate('.edit-config-group', 'click', function(e){
             var index = $(this).parents('tr').index();
             var data = self.config_group[index];
             if(data){
                var dialog = gWidget.create('AddConfigItemDialog', {
                    data: $.extend(true,{}, data),
                    onSuccess: function(data){
                        self.editConfig(data)
                        dialog.destroy();
                    }
                })
             }
        })

        //查看日志详情
        $('body').delegate('.ajax_log_new', 'click', function(e){
            var $li = $(this).parents('li');
            var eventId = $li.attr('data-event-id');
            var build_version = $li.attr('data-build-version');
            if(build_version){
                $li.removeClass('closed').addClass('open');
                if($li.attr('data-status') != 'building'){
                    $li.find('.log-tab-btn').eq(0).click();
                }
            }else{
                Msg.warning("该条数据异常，暂时无法查看详情")
            }
        })

        $('body').delegate('.hide_log', 'click', function(e){
            $(this).parents('li').removeClass('open').addClass('closed');
        })

        $('body').delegate('.view-config-json', 'click', function(e){
            self.viewConfigJson();
        })

        

        //加载更多构建历史
        $('body').delegate('.load_more_new', 'click', function(e){
            self.getBuildHistory();
        })
    },
    viewVersionLog: function(version){
        var tenantName = $('#tenantName').val();
        var id = $('#plugin_id').val();
        var dialog = gWidget.create('viewVersionLog',{
            tenantName: tenantName,
            plugin_id: id,
            version: version,
            btns:[{
                text: '关闭',
                classes: 'btn btn-default btn-cancel'
            }]
        })
    },
    loopVersionStatus: function(version){
        var tenantName = $('#tenantName').val();
        var id = $('#plugin_id').val();
        getVersionStatus(
            tenantName,
            id,
            version
        ).done((data) => {
            var status = data.bean.status;
            var map = statusMap[status];
            $('tr[data-version-id='+version+']').find('.version_status').html(map ? map.text : '未知');
            if(status !== 'unbuild'){
                $('tr[data-version-id='+version+']').find('.view-version-log').show();
            }
            if(status !== 'build_success'){
                setTimeout(() => {
                    this.loopVersionStatus(version);
                }, 2000)
            }
        })
    },
    buildVersion: function(version, info){
        var self = this;
        var tenantName = $('#tenantName').val();
        var id = $('#plugin_id').val();
        buildVersion(
            tenantName,
            id,
            version,
            info
        ).done(function(data){
            Msg.success("操作成功");
            self.viewVersionLog(version);
            self.loopVersionStatus(version);
            

        })
    },
    deleteVersion: function(version){
        var self = this;
        var tenantName = $('#tenantName').val();
        var id = $('#plugin_id').val();
        return deleteVersion(
            tenantName,
            id,
            version
        ).done(function(data){
            Msg.success("操作成功");
            self.reloadBuildHistory();
        })
    },
    
    getData:function(){
        var data ={}
        if(this.data.build_source === 'dockerfile'){
             data = {
                plugin_alias: $('#plugin_alias').val(),
                min_memory: $('#min_memory').val(),
                update_info: $('#desc').val(),
                build_cmd: $('#build_cmd').val(),
                code_version: $('#code_version').val()
            }
        }else{
            data = {
                plugin_alias: $('#plugin_alias').val(),
                min_memory: $('#min_memory').val(),
                update_info: $('#desc').val(),
                build_cmd: $('#build_cmd').val(),
                image_tag: $('#image_tag').val()
            }
        }
       
        return data;
    },
    checkData: function(){
        var data = this.getData();


        
         if(this.data.build_source === 'dockerfile'){
             if(!data.code_version){
                Msg.warning("请填写代码版本")
                return false;
             }
        }else{
            if(!data.image_tag){
                Msg.warning("请填写镜像版本")
                return false;
             }
        }

        if(!data.plugin_alias){
            Msg.warning("请填写插件名称");
            return;
        }

        return true;
    },
    //创建新版本
    buildPuild: function(){
        var self = this;
        var tenantName = $('#tenantName').val();
        var id = $('#plugin_id').val();
        http({
            url: '/ajax/'+tenantName+'/plugin/'+id+'/new-version',
            type: 'post'
        }).done(function(data){
            self.reloadBuildHistory();
            self.getPluginInfo();
        })
    },
    //保存插件
    savePlugin: function(){
        var data = this.getData();
        if(this.checkData()){
            var tenantName = $('#tenantName').val();
            var id = $('#plugin_id').val();
            http({
                url: '/ajax/'+tenantName+'/plugin/'+id+'/version/'+this.data.build_version+'/update',
                type: 'put',
                data: JSON.stringify(data)
            }).done(function(data){
                Msg.success("保存成功");
                $("#build_version").val(data.bean.build_version);
            })
        }
    },
    //渲染配置组
    renderConfigGroup: function(){
        var config_group = this.config_group || [];
        $('.added-config-item-wrap .config-item-wrap').html('');
        for(var i=0;i<config_group.length;i++){
            $('.added-config-item-wrap .config-item-wrap').append(
                template.render(document.getElementById('config-group-tpl').innerHTML, {config: config_group[i], isMarketPlugin: this.isMarketPlugin()})
            )
        } 
    },
    //获取插件当前配置信息
    getPluginInfo: function(){
        var self  = this;
        var tenantName = $('#tenantName').val();
        var id = $('#plugin_id').val();
        http({
            url:'/ajax/'+tenantName+'/plugin/'+id+'/base-info',
            type: 'get'
        }).done(function(data){
            self.data = data.bean || {};
            self.getVersionConfig();
            self.render();
        })
    },
    getVersionConfig: function(){
        var self = this;
        var tenantName = $('#tenantName').val();
        var id = $('#plugin_id').val();
        getVersionConfig(
            tenantName,
            id,
            this.data.build_version
        ).done(function(data){
            self.config_group = data.bean.config_group || [];
            self.renderConfigGroup();
        })
    },
    reloadBuildHistory: function(){
        this.page = 1;
        this.build_list = [];
        $('.version-history-table tbody').html('');
        this.getBuildHistory();
    },
    //获取构建历史
    getBuildHistory: function(){
        var self = this;
        var tenantName = $('#tenantName').val();
        var id = $('#plugin_id').val();
        getBuildHistory(
            tenantName,
            id,
            this.page,
            this.page_size
        ).done(function(data){
            self.build_list = self.build_list.concat(data.list || []);
            self.renderBuildHistory(data.list);
            self.page = data.next_page;

            if(data.list && data.list.length){
                var one = data.list[0];

                if(one.build_status === 'building'){
                    self.loopVersionStatus(one.build_version);
                }
            }
            
            //没有下一页了
            if(!data.list || !data.list.length){
                $('.load_more_wrap').hide();
            }

            if(data.list && data.list.length){
                $('.build-history-empty').remove();
            }
        })
    },
    //判断是否在构建中
    isBuilding: function(){
        if(this.build_list.length){
            var first = this.build_list[0];
            if(first.build_status === 'building'){
                return true;
            }
        }
        return false;
    },
    //渲染构建历史
    renderBuildHistory: function(data){

        var html = template.render(document.getElementById('build_history_list_item_tpl').innerHTML, {list: data || [], isMarketPlugin: this.isMarketPlugin()})
        $('.version-history-table tbody').prepend(html)
    },
    render: function(){
        var data = this.data;
        $('#plugin_alias').val(data.plugin_alias);
        $('#desc').val(data.update_info);
        $('#min_memory').val(data.min_memory);
        $("#build_cmd").val(data.build_cmd || '');
        $('.build_version').html(data.build_version);
        if(data.image_tag){
            $("#image_tag").val(data.image_tag)
        }

        if(data.code_versioin){
            $("#code_versioin").val(data.code_versioin)
        }
        
    },
    //渲染配置项
    renderConfigItem: function(element, data){
        var length = element.find('.config-item').length;
        data = data || {};
        element.find('.config-item-wrap').append(
            "<div class='config-item form-inline' style='margin-bottom:10px'>"+
                "<div class='form-group' style='margin-left:1px;margin-right:1px'>"+
                    "<span class='control-label sr-only'>属性名</span>"+
                    "<input  style='width:80px' placeholder='属性名' value='"+(data.attr_name||'')+"' class='form-control' type='text' name='attr_name' />"+
                "</div>"+
                "<div class='form-group' style='margin-left:1px;margin-right:1px'>"+
                    "<span class='control-label sr-only'>属性类型</span>"+
                     '<select   data-toggle="tooltip" data-placement="top" title="属性类型"  class="form-control fn-tips" name="attr_type">'+
                        '<option '+ (data.attr_type =='string' ? 'selected' : '') +' value="string">字符串</option>'+
                        '<option '+ (data.attr_type =='radio' ? 'selected' : '') +' value="radio">单选</option>'+
                        '<option '+ (data.attr_type =='checkbox' ? 'selected' : '') +' value="checkbox">多选</option>'+
                    '</select>'+
                "</div>"+
                "<div class='form-group attr_value_group' style='margin-left:1px;margin-right:1px;display:"+((data.attr_type === 'string' || !data.attr_type) ? 'none' : '')+"'>"+
                    "<span class='control-label sr-only'>可选值</span>"+
                        "<input value='"+(data.attr_alt_value || '')+"'  data-toggle='tooltip' data-placement='top' title='单选或多选的可选值， 多个用逗号分割，如：value1, value2' style='width:130px' class='form-control fn-tips' type='text' name='attr_alt_value' placeholder='可选值' />"+
                "</div>"+
                "<div class='form-group' style='margin-left:1px;margin-right:1px'>"+
                    "<span class='control-label sr-only'>默认值</span>"+
                    "<input  value='"+(data.attr_default_value || '')+"'  style='width:80px'   placeholder='默认值' class='form-control' type='text' name='attr_default_value' />"+
                "</div>"+
                "<div class='form-group' style='margin-left:1px;margin-right:1px'>"+
                    "<span class='control-label sr-only'>是否可修改</span>"+
                     '<select class="form-control" name="is_change">'+
                        '<option '+ (data.is_change === true ? 'selected' : '') +' value="true">可修改</option>'+
                        '<option '+ (data.is_change === false ? 'selected' : '') +'  value="false">不可修改</option>'+
                    '</select>'+
                "</div>"+
                "<div class='form-group attr_info' style='margin-left:1px;margin-right:1px;'>"+
                    "<span class='control-label sr-only'>配置项说明</span>"+
                        "<input value='"+(data.attr_info || '')+"'  data-toggle='tooltip' data-placement='top' style='width:130px' class='form-control' type='text' name='attr_info' placeholder='简短说明' />"+
                "</div>"+
                "<div class='form-group add-item-wrap' style='margin-left:1px;display:"+(length === 0 ? 'inline-block': 'none')+"'>"+
                    "<a href='javascript:;' class='glyphicon glyphicon-plus add-item'></span>"+
                "</div>"+
                "<div class='form-group remove-item-wrap' style='margin-left:1px;display:"+(length >= 1 ? 'inline-block': 'none')+"'>"+
                    "<a href='javascript:;' class='glyphicon glyphicon-minus remove-item'></span>"+
                "</div>"+
                "<div class='form-group delete-item-wrap' style='margin-left:1px;'>"+
                    "<a href='javascript:;' class='glyphicon glyphicon-remove delete-item'></span>"+
                "</div>"+
            "</div>"
        )
        $('.fn-tips').tooltip();
    }
}


$(function(){
    controller.init();
})

/*****************

    main end

*****************/


