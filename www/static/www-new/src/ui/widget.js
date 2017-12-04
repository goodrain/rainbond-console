require('./widget.css');

//guid生成器
function guid() {
    function S4() {
       return (((1+Math.random())*0x10000)|0).toString(16).substring(1);
    }
    return (S4()+S4()+"-"+S4()+"-"+S4()+"-"+S4()+"-"+S4()+S4()+S4());
}

function toggleNum(num){
    if(!window.toggleNum || Math.abs(window.toggleNum) !== Math.abs(num)){
        window.toggleNum = num;
    }else{
        window.toggleNum = -window.toggleNum;
    }
    return window.toggleNum;
}


var widgetCache = {};
function extend(sub, parent){
    var args = arguments, len = args.length;
    if(len == 0){
        return {};
    }else if(len == 1){
        return sub;
    }else if(len == 2){
        if(typeof parent === 'object'){
            for(var k in parent){
                if(sub[k] && $.isFunction(sub[k])){
                    var parentFn = parent[k];
                    var subFn = sub[k];
                    sub[k] = (function(parentFn, subFn){
                        return function() {
                            var oldParent = this.callParent;
                            this.callParent = parentFn;
                            var res = subFn.apply(this, arguments);
                            this.callParent = oldParent;
                            return res;
                        }
                    })(parentFn, subFn)              
                }else{
                    if(k === '_defaultOption'){

                        var copy = $.extend(true,{},parent[k]);
              
                        sub[k] = merge(copy || {}, sub[k] || {});
                    }else{
                       sub[k] = parent[k];
                    }
                }
            }
        }
    }
    return sub;
}

function merge(object, config){
    var args = arguments, len = args.length;
    if(len == 0){
        return {};
    }else if(len == 1){
        return object;
    }else if(len == 2){
        if(typeof config === 'object'){

            for(var k in config){
                object[k] = config[k];
            }
        }
    }
    return object;
}

function each(array, fn, context){
    var i=0,len=array.length;
    for(;i<len;i++){
        fn.call(context, array[i]);
    }
}

function strToElement(str){
    var fragment = document.createDocumentFragment();
    fragment.innerHTML = str;
    return fragment.firstChild;
}


function Event (){
    
}
Event.prototype = {
    on : function(name, handle, context){
        this.events || (this.events = {});
        this.events[name] || (this.events[name] = []);
        var obj = {
            handle : handle,
            context : context
        }
        this.events[name].push(obj);
    },
    off:function(name, handle, context){
        var handles = this.events[name], item;
        if(!handles || !handles.length) return;

        if(arguments.length ==0){
            this.events = {};
            return;
        }

        if(arguments.length == 1){
            this.events[name] = [];
            return;
        }

        for(var i=0;i<handles.length;i++){
            item = handles[i];
            if(item === item.handle){
                handles.splice(i, 1);
                i--;
            }
        }
    },
    once:function(name, handle, context){
        var self = this;
        var onceHandle = function(){
            var result = handle.call(context, arguments);
            self.off(name, onceHandle);
            return result;
        }
        this.on(name, onceHandle, context);
    },
    fire:function(name, data){
        
        var handles = this.events[name], handle, context,i=0,len, result;
        if(handles){
            for(len=handles.length;i<len;i++){
                handle = handles[i].handle;
                context = handles[i].context;
                
                result = handle.apply(context, [].slice.call(arguments, 1));
            }
        }
        return result;
    }
}
var uuid = 1;
var baseZindex = 1000;
function noop(){};
function Base(){};
Base.prototype = {
    _init      : function(option = {}){
        this.option = $.extend(true, {}, this.option || {}, this._defaultOption || {}, option)
        var event = this.option.event;
        this.setEvent(event);
    },
    _create : function(){
        var self = this;
        this.option.tpl && (this.element = $(this.option.tpl));
        if(this.option.id){
            this.element.attr('id', this.option.id);
        }
        var cssText = '';
        if(this.option.maxHeight){
            cssText += 'max-height:'+this.option.maxHeight+';';
        }
        if(this.option.height){
            cssText += 'height:'+this.option.height+';';
        }
        if(this.option.width){
            cssText += 'width:'+this.option.width+';';
        }
        if(this.option.maxWidth){
            cssText += 'max-width:'+this.option.maxWidth+';';
        }
        if(this.option.zIndex){
            cssText += 'z-index:'+this.option.zIndex+';';       
        }
        if(this.option.style){
            cssText += this.option.style;  
        }

        this.element[0].style.cssText += cssText;  
        var classes = this.option.classes;
        if(classes){
            this.element.addClass(classes);
        }
        
        if(this.option.domEvents){
            for(var key in this.option.domEvents){
                
                var selector = key.split(' ')[0];
                var type = key.split(' ')[1];
                
                (function(selector, type, fn){
                    self.element.delegate(selector, type ,  function(e){
                        fn(e, self)
                    })
                })(selector, type, this.option.domEvents[key]);
                
            }
        }
    },
    parseTpl : function(tplStr){
        return strToElement(tplStr);
    },
    getElement : function(){
        return this.element;
    },
    setEvent : function(event){
        if(event && $.isPlainObject(event)){
            for(var k in event){
                this.on(k, event[k]);
            }
        }
    },
    setPos  : function(pos){
        pos = pos || {};
        var position = this.element.css('position');
        if(position == 'absolute' || position == 'relative' || position == 'fixed'){
            pos.left && this.element.css('left', pos.left);
            pos.top && this.element.css('top', pos.top);
        }else{
            pos.left && this.element.css('margin-left', pos.left);
            pos.top  && this.element.css('margin-top', pos.top);
        }
    },
    setSize : function(size){
        size = size || {};
        size.width  && this.element.css('width', size.width);
        size.height && this.element.css('height', size.height);
        size.maxWidth && this.element.css('max-width', size.maxWidth);
        size.maxHeight && this.element.css('max-height', size.maxHeight);
        this.resize();
    },
    getRect : function(){
        var rect = {},ele = $(this.element);
        var position = ele.position();
        rect.left = position.left;
        rect.right = position.right;
        rect.width = ele.outerWidth();
        rect.height = ele.outerHeight();
        return rect;
    },
    show : function(){
        if(this.fire('beforeShow') !== false){
            this.element.show();
            this.fire('afterShow');
        } 
    },
    hide : function(){
        if(this.fire('beforeHide') !== false){
            this.element.hide();
            this.fire('afterHide');
        }
    },
    unbind : noop,
    bind : noop,
    destroy : function(){
        if(this.fire('beforeDestroy') !== false){
            this.events = this.event = [];
            this.unbind();
            this.element.off();
            this.off();
            this.element.remove();
        }
        this.element.undelegate();
    },
    resize : function(){
        
    },
    getUUID : function(){
        return ++uuid;
    }
}

function Classes(name, data){
    data = data || {};
    data.extend = data.extend || 'Base';
    data.mixins = data.mixins || ['Event']
    function Contrl(option, name){
        this.events = {};
        this.ClassName = name;
        this._init(option);
    }
    var prototype = Contrl.prototype;
    extend(prototype, data);
    Classes.process(Contrl, data);
    Classes.addCache(name, Contrl);
    return Contrl;
}
Classes.addCache = function(name, com){
    widgetCache[name] = com;
},
Classes.getCache = function(name){
    return widgetCache[name];
}
Classes.process = function(Class, data){
    var k, handle, cfg;
    for(k in this.registerCache){
        handle = this.registerCache[k];
        cfg = data[k];
        delete data[k];
        handle(cfg, Class);
    }
}
Classes.registerCache = {};
Classes.register = function(proto, handle){
    this.registerCache[proto] = handle;
}

Classes.register('mixins', function(mixins, Class){
    var k,i=0, len = mixins.length;
    for(;i<len;i++){
        var mixinsClass = Classes.getCache(mixins[i]);
        var pro = mixinsClass ? mixinsClass.prototype : {};
        merge(Class.prototype, pro);
    }
})

Classes.register('extend', function(val, Class){
    var mixClass = Classes.getCache(val);
    if(mixClass){
        var subClass = Class.prototype;
        var parentClass = mixClass.prototype;
        extend(subClass, parentClass);
    }
})

Classes.addCache('Base', Base);
Classes.addCache('Event', Event);

var widget = {
    define : function(name, data){
        return Classes(name, data);
    },
    create : function(name, option){
        var classes = Classes.getCache(name);   
        return new classes(option, name);     
    }
}



//拖拽组件,与其他组件组合使用
widget.define('drag', {
    _defaultOption : {
        handle : '',
        target : '',
        position : 'absolute',
        context  : 'body',
        parent : null,
        lockX : false,
        lockY : false
    },
    _init:function(option){
        this.callParent(option);
        this.touchSupper = 'touchstart' in document;
        this.startEvent = this.touchSupper ? 'touchstart' : 'mousedown';
        this.moveEvent  = this.touchSupper ? 'touchMove'  : 'mousemove';
        this.endEvent   = this.touchSupper ? 'touchend'   : 'mouseup';
        this.lockX      = this.option.lockX;
        this.lockY      = this.option.lockY;
        
        this._create();
        this.bind();
    },
    _create:function(){
        
        this.handle = this.option.handle instanceof jQuery ? this.option.handle: $(this.option.context+' '+this.option.handle);
        if(this.option.target){
            this.target = this.option.target instanceof jQuery ? this.option.target:$(this.option.context+' '+this.option.target);
        }else{
            this.target =  this.handle;
        }
        this.element = this.target;
        //this.element.css('position', this.option.position);
    },
    bind:function(){
        var self = this;
        
        this.handle.bind(this.startEvent, function(e){
            self.dragStart(e);
        });
    },
    unbind:function(){
        this.handle.unbind();
    },
    dragStart : function(e){
        e.preventDefault();
        var self = this;
       
        this.x = e.clientX;
        this.y = e.clientY;
        this.offsetX = this.element[0].offsetLeft;
        this.offsetY = this.element[0].offsetTop;

        if(!this.proxyMove){
            this.proxyMove = function(e){
                self.drag(e);
            }
        }
        if(!this.proxyEnd){
            this.proxyEnd = function(e){
                self.dragEnd(e);
            }
        }
        if(this.fire('onStart') === false) return;
        $(document).bind(this.moveEvent, this.proxyMove);
        $(document).bind(this.endEvent, this.proxyEnd);
    },
    drag : function(e){
        var currX = e.clientX;
        var currY = e.clientY;
        e.preventDefault();
        var disX = currX - this.x;
        var disY = currY - this.y;
        if(this.fire('onDrag', {disX : disX, disY : disY}) === false) return;
        
        if(this.option.parent){

                !this.lockY && this.element.css({'top' : this.offsetY+disY})

                !this.lockX && this.element.css({'left' : this.offsetX+disX})
             
            
        }else{
             var cw = $(document).width();
             var ch = $(document).height();

             if((this.offsetY+disY) > 0 && (this.element.outerHeight()+this.offsetY+disY) < ch){
                 !this.lockY && this.element.css({'top' : this.offsetY+disY})
             }
             if(this.offsetX+disX > 0 && (this.element.outerWidth()+this.offsetX+disX) < cw){
                 !this.lockX && this.element.css({'left' : this.offsetX+disX})
             }
        }
       
    },
    dragEnd : function(e){
        $(document).unbind(this.moveEvent, this.proxyMove);
        $(document).unbind(this.endEvent, this.proxyEnd);
        this.fire('onEnd');
    },
    setLockX : function(v){
        this.lockX = !!v;
    },
    setLockY : function(v){
        this.lockY = !!v;
    }
})


//按钮组件
widget.define('button', {
    _defaultOption : {
        tpl :'<button class="btn"></button>',
        tag:'button',
        iconTpl : '<i class="fa"></i>',
        style : 'cursor:pointer;',
        classes : 'btn-default',
        disabled    : false,
        text : '',//按钮文字
        icon      : '', //是否带icon图标
        iconPosition : 'left'   //如果有icon图标，则表示图标位置, 左/右
    },
    _init : function(option){
        this.callParent(option);
        if(this.ClassName == 'button'){
            if(this.tag == 'a'){
                this.option.tpl = '<a href="javascript:;" class="btn"></a>';
            }else{
                this.option.tpl = '<'+this.option.tag+' class="btn"></'+this.option.tag+'>';
            }
            this._create();
        }
        this.bind();
    },
    _create : function(){
        this.created = true;
        this.callParent();

        //设置文本
        this.element.html(this.option.text || 'button');

        //是否有icon
        var iconClass = this.option.icon;
        if(iconClass){
            this.icon = $(this.option.iconTpl);
            this.icon.addClass('fa-'+iconClass);
            var pos = this.option.iconPosition;
            if(pos == 'left'){
                this.element.prepend(this.icon);
            }else if(pos == 'right'){
                this.element.append(this.icon);
            }
        }
        if(this.option.disabled){
            this.element.addClass('btn-disabled');
        }
    },
    toggler:function(){
        if(!this.option.disabled){
            this.element.removeClass('btn-disabled');
        }else{
            this.element.addClass('btn-disabled');
        }
        this.option.disabled = !this.option.disabled;
    },
    isDisabled:function(){
        return this.option.disabled === false;
    },
    bind:function(){
        this.callParent();
        var event = this.option.event;
        if(event){
            this.element.bind( event.type ||'click',function(){
                event.handle.call(event.context || null);
            })
        }
    }
})


//遮罩层组件
widget.define('mask', {
    _defaultOption : {
        id : '',
        _class   : 'ui_mask',
        autoShow : true,
        tpl      : '<div></div>',
        style    : 'position:fixed;left:0;top:0;width:100%;height:100%;',
        footerStyle:'',
        bodyStyle:'',
        zIndex   : 9999,
        opacity  : '0.5',
        color    : '#000',
        renderTo : 'body'
    },
    _init : function(option){
        this.callParent(option);
        this._create();
        this.bind();
    },
    _create : function(){
        this.option.id = this.id = this.option.id || 'ui_mask_'+this.getUUID();
        this.callParent();
        
        this.element.css('background-color', this.option.color).css('opacity', this.option.opacity);


        if(this.option.autoShow){
            this.show();
        }

        if(this.ClassName == 'mask'){
            this.element.appendTo($(this.option.renderTo));
        }
        
    },
    bind : function(){
        var self = this;
        this.element.bind('click', function(){
            self.fire('onClick');
        })
    },
    destroy : function(){
        this.element.unbind();
        this.element.remove();
    }
})

widget.define('panel', {
    _defaultOption : {
        tpl:'<div class=" panel panel-default">'+
                '<div class="panel-heading">'+
                    '<span class="panel-title"></span>'+
                    '<div class="btns">'+
                        '<span class="fa fa-remove panel-hide" title="关闭"></span>'+
                        '<span class="btn-collaspe"></span>'+
                    '</div>'+
                '</div>'+
                '<div class="panel-cont">'+
                    '<div class="panel-body"></div>'+
                    '<div class="panel-footer">'+
                        
                    '</div>'+
                '</div>'+
              '</div>',
        state : 'expand',
        width:'100%',
        quickCollaspe:false,
        showFooter : false,
        expandable: false,
        closeable : true
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'panel'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        
        this.callParent();
        this.header = this.element.find('.panel-heading');
        
        
        if(this.option.expandable === false){
            this.header.find('.btn-collaspe').hide();
        }
        if(this.option.closeable === false){
            this.header.find('.panel-hide').hide();
        }

        this.cont = this.element.find('.panel-cont');

        //设置标题
        this.setTitle(this.option.title);
        
        this.body = this.element.find('.panel-body');
           this.body[0].style.cssText = this.option.bodyStyle || '';
        
        //设置内容
        if(this.option.content){
            
            this.setContent(this.option.content);
            
        }
        this.footer = this.element.find('.panel-footer');
        if(!this.option.showFooter){
            this.footer.hide();
        }else if(this.option.footerContent){
            this.footer.html(this.option.footerContent);
            
        }
        if(this.option.footerStyle){
            this.footer[0].style.cssText = this.option.footerStyle || '';
        }
        if(this.option.state == 'expand'){
            this.expand();
        }else{
            this.collaspe();
        }

        this.element.appendTo(this.option.renderTo);
        
    },
    setTitle : function(title){
        this.header.find('.panel-title').html(title).attr('title', title).attr('alt', title);
    },
    setContent : function(content){
        
        this.body.html(content);
    },
    appendContent:function(content){
        this.body.append(content);
    },
    bind:function(){
        var self = this;
        if(this.option.quickCollaspe === true){
            this.element.delegate('.panel-heading', 'click', function(e){
                e.stopPropagation();
                self.trigger();
            })
        }
        
        this.element.delegate('.fa-remove', 'click', function(e){
            e.stopPropagation();
            if(self.fire('onClose') !== false){
                self.hide();
            }
        })

    },
    expand:function(){
        this.option.state = 'expand';
        this.cont.show();
        this.header.find('.btn-collaspe').removeClass('state-expend').addClass('state-collaspe');
    },
    collaspe:function(){
         this.option.state = 'collapse';
         this.cont.hide();
         this.header.find('.btn-collaspe').removeClass('state-collaspe').addClass('state-expend');
    },
    trigger:function(){
        if(this.option.state == 'expand'){
           this.collaspe();
        }else{
            this.expand();
        }
    }
})


//弹出对话框框组件
var stack = [];
widget.define('dialog', {
    _defaultOption : {
        tpl:  '<div class="modal fade"><div class="modal-dialog" role="document">'+
            '<div class="modal-content">'+
              '<div class="modal-header">'+
                '<button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>'+
                '<h4 class="modal-title">Modal title</h4>'+
              '</div>'+
              '<div class="modal-body" style="max-height:400px;overflow-y:auto">'+
              '</div>'+
              '<div class="modal-footer">'+
            
              '</div>'+
            '</div>'+
          '</div></div>',
        resizeTpl   : '<span class="resize-btn" title="resize"></span>',
        closeBtnTpl : '',
        id          : '',
        classes     : '',
        modal       : true,
        width       : '600px',
        height      : '400px',
        maxWidth    : '1000px',
        maxHeight   :'1000px',
        minHeight   :'400px',
        autoDestroy : true,//是否隐藏时自动销毁
        minWidth    :'auto',
        autoShow    : true,
        autoCenter  : true, //是否默认屏幕居中显示
        footerStyle :'text-align:right;',
        bodyStyle   : 'overflow:auto;',
        zIndex      : 10000, 
        status      : '',
        pos         : 'center center',
        position    : 'absolute',
        resize      : false,
        renderTo    : 'body',
        drag        : true,
        enter       : true,//是否开启回车事件
        showFooter  : true,
        quickHide   : false,
        title       : '标题',
        full        : false,//是否全屏
        bindEvent:{
        },
        
        btns       : [
            {
                text : '确定',
                classes : 'btn-success'
            },
            {
                text : '取消',
                classes : 'btn-default btn-cancel'
            }
        ]
    },
    _init : function(option){
        this.callParent(option);
        this.id = this.option.id || 'ui_dialog_'+this.getUUID();
        if(this.ClassName == 'dialog'){
            this.randomId = Math.random();
            this._create();
            this.bind();
        }
    },
    _create : function(){
        var self = this;
        this.callParent();
        this.element.appendTo(this.option.renderTo);
        this.header = this.element.find('.modal-header');
        this.body = this.element.find('.modal-body');
        this.footer = this.element.find('.modal-footer');

        //设置标题
        this.setTitle(this.option.title);

        if(this.option.btnText){
            if(!$.isArray(this.option.btnText)){
                this.option.btnText = [this.option.btnText]
            }
            
            for(var i=0;i<this.option.btnText.length;i++){
                this.option.btns[i].text = this.option.btnText[i];
            }
        }
        
        //如果全屏显示
        if(this.option.full){
            this.option.drag = false;
            this.option.maxWidth = this.option.width = (document.documentElement.clientWidth || document.body.clientWidth) +'px';
            this.option.maxHeight = this.option.height = (document.documentElement.clientHeight || document.body.clientHeight) +'px';
        }
        
        
        this.element.css('position', 'fixed').css('margin', 0).addClass('dialog');
        if(this.option.full){
            this.element.css({top:0,left:0})
        }
        
        //创建遮罩层
        if(this.option.modal){
            this.mask = widget.create('mask',{
                event : {
                    'onClick' : function(){
                        if(self.option.quickHide){

                            self.mask.hide();
                            self.hide();
                        }
                    }
                }
            })
        }
        //是否可以拖动
        if(this.option.drag){
            this.drag = widget.create('drag', {
                handle : '#'+this.element.attr('id')+' '+'.modal-title',
                target : '#'+this.element.attr('id')
            })
        }
        //是否可以拖动改变大小
        if(this.option.resize){
            var w = 0,height = 0, cw = 0, ch = 0, maxWidth = parseInt(this.option.maxWidth), maxHeight = parseInt(this.option.maxHeight), minHeight = parseInt(this.option.minHeight), minWidth = parseInt(this.option.minWidth);
            this.element.append($(this.option.resizeTpl));
            this.resizeBtn = widget.create('drag', {
                handle : '#'+this.element.attr('id')+' '+'.resize-btn',
                target : '#'+this.element.attr('id'),
                event : {
                    onStart : function(){
                        
                        w = self.element.width();
                        h = self.element.height();
                    },
                    onDrag : function(arg){
                        var currw = w+arg.disX;
                        var currh = h+arg.disY;
                        if(currw < minWidth){
                            currw = minWidth;
                        }else if(currw > maxWidth){
                            currw = maxWidth;
                        }

                        if(currh < minHeight){
                            currh = minHeight;
                        }else if(currh > maxHeight){
                            currh = maxHeight;
                        }
                        self.fire('onResize');
                        self.element.css({width:currw, height:currh});
                        self.setBodyHeight();
                        return false;
                    }
                }
            })
        }

        if(this.option.content) {
            this.appendContent(this.option.content);
        }
        this.setSize({width: this.option.width, height:this.option.height});
        this.footer.addClass('dialog-footer');
        //是否隐藏footer
        if(!this.option.showFooter){
            this.footer.hide();
        }else{
            this.btns = [];
            var btns = this.option.btns;
            for(var i=0;i<btns.length;i++){
                var btn = widget.create('button', btns[i]);
                this.btns.push(btn);
                btn.getElement().appendTo(this.footer);
            }
        }
        
        //阻止后退键
        $(window).bind('keydown.dialog'+this.randomId, function(e){
            if(this.status != 'show'){
                return;
            }
            if(e.keyCode == 8){
                e.preventDefault();
            }
        })
       
        this.element.delegate('input,textarea', 'keydown.dialog', function(e){
            e.stopPropagation();
        })

        if(this.option.autoShow){
            this.show();
        }
        if(this.option.autoCenter){
            this.center();
        }
    },
    setBodyHeight:function(){
        if(this.option.height == 'auto'){
            return;
        }
        var self = this;
        var headHeigth = self.header.outerHeight();
        var footerHeight = self.option.hideFooter ? 0 : self.footer.outerHeight();
        var allHeight = self.element.height();
        var bodyPaddingTop = parseInt(self.body.css('padding-top')) || 0;
        var bodyPaddingBottom = parseInt(self.body.css('padding-bottom')) || 0;
        var bodyHeight = allHeight - headHeigth - footerHeight - bodyPaddingTop - bodyPaddingBottom;
        self.body.height(bodyHeight);
    },
    setSize: function(size) {
        this.callParent(size.width, size.height);
        this.element.find('.modal-dialog').css({width: size.width, height: size.height})
    },
    appendContent:function(cont){
        this.callParent(cont);
        this.center();
    },
    center : function(){
        var w = $(document).width();
        var h = document.documentElement.clientHeight || document.body.clientHeight;
        var thisRect = this.getRect();
        if(this.option.full){
            this.setPos({left: 0, top: 0});
        }else{
            //this.element.css({bottom:'auto', left: '50%', top: '50%', transform: 'translate(-50%, -50%)'})
            this.setPos({left: (w - thisRect.width)/2, top: (h-thisRect.height)/2});
        }
    },
    show : function(){
        this.callParent();

        this.status = 'show';
        if($.inArray(this, stack)=== -1){
            stack.push(this);
        }
        var perDialog;
        for(var i=0;i<stack.length;i++){

            if(stack[i] === this){
                perDialog = stack[i-1];
            }
        }
        if(perDialog){
            perDialog.hide();
        }

        if(this.mask){
            this.mask.show();
        }

        this.element.addClass('in');

        this.element.show();
        //$('body').css('overflow','hidden');
        this.setBodyHeight();
    },
    hide : function(){
        
        if(this.fire('beforeHide') !== false){
            this.element.hide();
            
            var perDialog;
            for(var i=0;i<stack.length;i++){
                if(stack[i] === this){
                    perDialog = stack[i-1];
                }
            }
            var self = this;
            setTimeout(function(){
                if(perDialog !==self && stack[stack.length-1] === self){
                    perDialog && perDialog.show();
                    stack.pop();
                }
            },20);
            if(this.mask){
                this.mask.hide();
            }
            this.status = 'hide';
            if(this.option.autoDestroy){
                this.destroy();
            }
            this.element.removeClass('in');
            this.fire('afterHide');
            $('body').css('overflow','');
        }
    },
    setTitle : function(title){
        this.header.find('.modal-title').html(title).attr('title', title).attr('alt', title);
    },
    setContent : function(content){
        this.body.html(content);
    },
    appendContent:function(content){
        this.body.append(content);
    },
    expand:function(){
        this.callParent();
        this.element.height(this.oldHeight);
        this.resizeBtn && this.element.find('.resize_btn').show();
    },
    collaspe:function(){
        this.callParent();
        this.oldHeight = this.element.height();
        this.resizeBtn && this.element.find('.resize_btn').hide();
        this.element.height(this.header.outerHeight());
    },
    destroy:function(){
        if(this.fire('beforeHide') !== false){
            this.element.undelegate('input,textarea','keydown.dialog')
            $(window).unbind('keydown.dialog'+this.randomId);
            
            for(var i=0;i<stack.length;i++){
                if(stack[i] === this){
                    stack.splice(i,1);
                    break;
                }
            }
            

            if(this.mask){
                this.mask.destroy();
            }
            
        
            if(this.btns && this.btns.length){
                for(var i=0;i<this.btns.length;i++){
                    this.btns[i].destroy();
                    this.btns.splice(i,1);
                    i--;
                }
            }
            
            this.status = 'destroy';
            
            if(this.option.full){
                $(window).unbind('resize.dialog');
            }
            this.callParent();
        }
    },
    bind : function(){
        var self = this;
        this.callParent();
       
        if(this.option.full){
            
            $(window).bind('resize.dialog', function(){
                self.option.maxWidth = self.option.width = (document.documentElement.clientWidth || document.body.clientWidth) +'px';
                self.option.maxHeight = self.option.height = (document.documentElement.clientHeight || document.body.clientHeight) +'px';
                self.setSize({width:self.option.width, height:self.option.height, maxWidth:self.option.maxWidth, maxHeight:self.option.maxHeight})
                self.setBodyHeight();
            })
        }

        this.element.delegate('.btn-ok', 'click', function(e){
            self.fire('onOk')
        })
        
        this.element.delegate('.btn-cancel, .close', 'click', function(e){
            if(self.fire('onCancel') !== false){
                self.hide();
            }
        })
        
        if(this.option.enter){
            $(document).bind('keydown.dialog', function(e){
                if(e.keyCode == 13){
                    e.preventDefault()
                    self.fire('onEnter');
                }
            })
        }
        
        var bindEvent = this.option.bindEvent;
        if(bindEvent &&　((typeof bindEvent) == 'object')){
            for(var key in bindEvent){
                this.element.delegate(key, 'click', function(e){
                    bindEvent[key]();
                })
            }
        }
    },
    unbind:function(){
        this.callParent();
        $(document).unbind('keydown.dialog');
    }
})

var icontype ={
    "success": "glyphicon-ok-sign",
    "danger": "glyphicon-remove-sign",
    "info": "glyphicon-info-sign",
    "warning": "glyphicon-exclamation-sign"
}

widget.define('message', {
    _defaultOption : {
        top:20,
        zIndex: 30000,
        interval:3000,
        message: ''
    },
    _init:function(option){
        this.callParent(option);
        this._create();
        this.bind();
    },
    _create:function(){
        this.$element = $('<div style="display:none;position:fixed;z-index:'+this.option.zIndex+';top:50%;left:50%; transform: translateX(-50%),translateY(-50%)"></div>');
        $('body').append(this.$element);
    },
    show:function(type, message){
        clearTimeout(this.timer);
        var tmp = '<div class="alertbig alert-'+type+' alert-dismissible fade in" role="alert"><span class="glyphicon '+ icontype[type] +'"></span><button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">×</span></button>'+(message || '')+'</div>'
        this.$element.html(tmp);
        this.$element.show();
        var self = this;
        this.timer = setTimeout(function(){
            self.destroy();
        },3000)
    },
    hide:function(){
        clearTimeout(this.timer);
        this.$element.hide(500);
    },
    destroy:function(){
        this.$element.remove();
        this.$element = null;
    },
    bind:function(){
        var self = this;
        this.$element.find('.close').click(function(){
            self.destroy();
        })
    }
});


widget.define('alert', {
    extend:'dialog',
    _defaultOption : {
        resize : false,
        expandable : false,
        zIndex: 10000,
        showFooter : true,
        autoShow : true,
        drag:true,
        autoCenter : true,
        width:'350px',
        height:'200px',
        minHeight:'200px',
        modal : true,
        btns:[
            {
                text : '确定',
                classes : 'btn-success btn-enter'
            }
        ]
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'alert'){
            this._create();
            this.bind();
        }
    },

    _create:function(){
        this.callParent();
        this.element.addClass('widget-alert').find('.modal-footer').css('text-align','center');
        if(this.option.renderTo && this.ClassName == 'alert'){
            this.element.appendTo(this.option.renderTo);
        }
    },
    bind:function(){
        var self = this;
        this.callParent();
        this.$element.find('.btn-enter').click(function(){
            self.destroy();
        })

    }
})

widget.define('confirm', {
    extend:'dialog',
    _defaultOption : {
        resize : false,
        drag : false,
        title:'提示',
        closeable:false,
        expandable : false,
        showFooter : true,
        autoShow : true,
        autoCenter : true,
        height:'200px',
        icon:'warning',
        showIcon:true,
        width:'400px',
        maxWidth:'400px',
        minHeight:'150px',
        btns:[
            {
                text : '确定',
                classes : 'btn-success btn-ok'
            },
            {
                text : '取消',
                classes : 'btn-default btn-cancel'
            }
        ]
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'confirm'){
            this._create();
            this.bind();
        }
    },

    _create:function(){
        this.callParent();
        this.element.addClass('widget-confirm').find('.modal-footer').css('text-align','center');
        this.body.css("text-align", "center");
    },
    setContent:function(cont){
        this.callParent(cont);
        this.body.html('<div class="dialog-msg-box">'+
                '<div '+(this.option.icon&&this.option.showIcon ? '' : 'style="display:none;"')+' class="dialog-msg-icon icon-confirm-'+this.option.icon+'"></div>'+
                '<div class="dialog-msg"></div>'+
            '</div>');
        this.body.find('.dialog-msg').html(cont)

    },
    appendContent: function(cont) {
        this.setContent(cont);
    },
    bind:function(){
        var self = this;
        this.callParent();
    }
})

widget.define('loadingbar', {
    _defaultOption:{
        tpl:'<div class="loadingbar" style="background:#5ef298;height:3px;position:fixed;left:0;top:0;width:0;"></div>',
        renderTo : $('body'),
        zIndex: 99999,
        interval: 300
    },
    _init:function(option){
        this.total = 0;
        this.loaded = 0;
        this.timer = null;
        this.width=0;
        this.callParent(option);
        if(this.ClassName == 'loadingbar'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        this.callParent();
        if(this.option.renderTo && this.ClassName == 'loadingbar'){
            this.element.appendTo(this.option.renderTo);
        }
    },
    getCurrentWidth(){
        var totalWidth = 100, pWidth = 0;
        this.width += (totalWidth - this.width) * 0.4;
        if(this.loaded > 0){
           pWidth = (this.loaded / this.total) * 100;
        }
        this.width = Math.max(this.width, pWidth);
        return this.width;
    },
    start(){
        this.width = 0;
        this.element.stop().show();
        this.computedWidth();
        this.timer = setInterval(() => {
            this.computedWidth();
        }, this.option.interval);
    },
    computedWidth(){
        var width = this.getCurrentWidth();
        this.element.stop().animate({width:width + '%'});
    },
    addRequest(){
        this.total ++;
        if(!this.timer){
            this.start();
        }else{
            this.computedWidth();
        }
    },
    removeRequest(){
        this.loaded ++;
        if(this.total == this.loaded){
            this.completed();
        }else{
            this.computedWidth();
        }
    },
    completed(){
        var self = this;
        this.total = this.loaded = 0;
        this.element.animate({width:'100%'}, function(){
                setTimeout(function(){
                    self.element.width(0).hide();
                })
                
        });
        clearInterval(this.timer);
        this.timer = null;
    }
})




widget.define('loading', {
    _defaultOption:{
        tpl:'<div class="loadbg" style="display:none;">'+
            '<div class="loadbox">'+
                '<div class="loading-center-absolute">'+
                    '<div class="object" id="object_one"></div>'+
                    '<div class="object" id="object_two"></div>'+
                    '<div class="object" id="object_three"></div>'+
                '</div>'+
                '<div class="loadtext">加载中</div>'+
            '</div>'+
        '</div>',
        renderTo : $('body'),
        zIndex: 20000,
        defaultInfo: '努力加载中'
    },
    _init:function(option){
        this.total = 0;
        this.callParent(option);
        if(this.ClassName == 'loading'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        this.callParent();
        this.textElement = this.element.find('.loadtext');
        if(this.option.renderTo && this.ClassName == 'loading'){
            this.element.appendTo(this.option.renderTo);
        }
    },
    show:function(text){
        this.textElement.html(text || this.option.defaultInfo)
        this.callParent();
        this.total ++;
    },
    hide:function(){
        --this.total;
        if(this.total == 0){
            this.callParent();
        }
    }
})

const widgetLoading = widget.create('loading',{})

//步骤功能组件
widget.define('stepLayout', {
    _defaultOption : {
        width: 350,
        height : 400,
        bodyStyle : 'height:315px',
        renderTo : 'body',
        classes : '',
        steps : [{
            title : '步骤一',
            content : '内容内容11',
            btns : [{
                text : '下一步',
                classes : 'btn-default step-next'
            }]
        },
        {
            title : '步骤二',
            content : '内容内容22',
            btns : [{
                text : '上一步',
                classes : 'btn-default step-pre'
            },{
                text : '下一步',
                classes : 'btn-default step-next'
            }]
        }],
        tpl : '<div class="layout stepLayout">'+
              '<div class="stepLayout_header">'+
                 '<div class="inner"></div>'+
                 '<span class="line bg-primary"></span>'+
              '</div>'+
              '<div class="stepLayout_body"><div class="inner"></div></div>'+
              '<div class="stepLayout_footer"><div class="inner"></div></div>'+
          '</div>',
        titleTpl : '<span class="step_title"></span>',
        stepBodyTpl  : '<div class="step"></div>',
        btnTpl       : '<div class="step_btns"></div>'
    },
    
    _init:function(option){
        this.callParent(option);
        this.total = this.option.steps.length;
        this.currStep = this.option.currStep || 0;
        if(this.ClassName == 'stepLayout'){
            if(this.total == 0){
                alert('步骤总数为0');
            }else{
                this._create();
                this.bind();
            }
        }
    },
    _create : function(){
        this.callParent();
        var classes, steps, i=0,len, step;
        this.element = $(this.option.tpl);
        this.setSize({width:this.option.width, height:this.option.height});
        this.header = this.element.find('.stepLayout_header');
        this.body   = this.element.find('.stepLayout_body');
        this.footer = this.element.find('.stepLayout_footer');

        var bodyStyle = this.option.bodyStyle;
        if(bodyStyle){
            this.body[0].style.cssText = bodyStyle;
        }

        classes = this.option.classes;
        if(classes){
            this.element.addClass(classes);
        }
        this.setSize({width:this.option.width, height:this.option.height});
        this.steps = steps = this.option.steps;
        if(steps &&steps.length > 0){
            for(len=steps.length;i<len;i++){
                step = steps[i];
                this._createStepHtml(step, i);
            }
        }

        //渲染出来
        if(this.option.renderTo && this.ClassName == 'stepLayout'){
            this.element.appendTo($(this.option.renderTo));
        }
        var self = this;
        setTimeout(function(){
            self._initData();
            self.translate(this.currStep);
        },0)
    },
    //初始化尺寸等信息
    _initData : function(){
        this.oneTitleWidth  = this.header.width()/this.total;
         
        this.oneBodyWidth   = this.body.width();
        this.oneFooterWidth = this.footer.width();

        this.body.find('.step').css({width:this.oneBodyWidth, height:this.body.height()});
        this.footer.find('.step_btns').width(this.oneFooterWidth);
        this.header.find('.step_title').width(this.oneTitleWidth);
        this.header.find('.line').width(this.oneTitleWidth)
        this.body.find('.inner').width(this.oneBodyWidth*this.total);
        this.footer.find('.inner').width(this.oneFooterWidth*this.total);
    },
    
    getCurrData : function(){
        return this.steps[this.currStep];
    },
    getStepInfo : function(index){
        return this.steps[index];
    },
    next : function(){
        this.currStep = this.currStep + 1 < this.total ? this.currStep + 1 : this.currStep;
        this.translate(this.currStep);
    },
    front : function(){
        this.currStep = this.currStep - 1 < 0 ? 0 : this.currStep - 1;
        this.translate(this.currStep);
    },
    translate : function(index){
        var stepInfo  = this.getStepInfo(index);
        this.header.find('.line').animate({width: this.oneTitleWidth*(index+1)});
     
        this.body.find('.inner').animate({left: -this.oneBodyWidth*(index)});
        this.footer.find('.inner').animate({left: -this.oneFooterWidth * index});
    },
    _createStepHtml : function(step, index){
        this._createTitle(step, index);
        this._createBody(step, index);
        this._createBtns(step, index);
    },
    //创建title
    _createTitle : function(step,index){

        var tit = step.title;
        var $tit = $(this.option.titleTpl).html(tit);
        this.header.find('.inner').append($tit);
        $tit = null;
    },
    //创建内容实体
    _createBody : function(step, index){
        var $body = $(this.option.stepBodyTpl);
        $body.addClass('step-body-'+index);
        if(step.content){
            $body.html(step.content);
        }
        this.body.find('.inner').append($body);
        $body = null;
    },
    //创建步骤按钮区
    _createBtns : function(step, index){
        var $btnWrap = $(this.option.btnTpl), btns = step.btns, btn, i=0,len;
        if(step.style){
            $btnWrap[0].style.cssText = step.style;
        }
        $btnWrap.addClass('step-btn-'+index);
        if(btns && btns.length>0){
            for(len=btns.length;i<len;i++){
                btn = widget.create('button', btns[i]);
                $btnWrap.append(btn.getElement());
            } 
        }
        this.footer.find('.inner').append($btnWrap);
    },
    unbind : function(){
        this.element.unbind();
    },
    bind:function(){
        var self = this;
        this.element.delegate('.step-next', 'click', function(){
            if(self.fire('beforeNext', self.currStep) !== false){
                self.next();
                self.fire('after', self.currStep);
            }
            
        })

        this.element.delegate('.step-pre', 'click', function(){
            if(self.fire('beforeFront', self.currStep) !== false){
                self.front();
                self.fire('afterFront', self.currStep);
            }
        })
    }
})


//分页组件
widget.define('page',{
    _defaultOption:{
        tpl : '<div class="widget-page" style="text-align:center;"><ul class="pagination"></ul></div>',
        total : 0,
        index : 1,
        groups : 5,
        timeout:20000,
        pageSize:10,
        url:'',
        loading:false,
        initialize:false,
        onChange: noop,
        dataType:'json',
        type:'get',
        views:['first', 'prev', 'group', 'next', 'end', 'info']
        //views:['first', 'prev', 'group', 'next', 'end', 'info', 'jump']
    },
    _init:function(option){
        this.initialize = false;
        this.callParent(option);
        this.option.totalPage = this.option.total/this.option.pageSize;
        if(this.ClassName == 'page'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        this.callParent();
        this.render();
        if(this.option.renderTo && this.ClassName == 'page'){
            this.element.appendTo($(this.option.renderTo));
        }
    },
    setData:function(total, pageNumber, pageSize){
        this.option.total = total;
        this.option.index = pageNumber;
        this.option.pageSize = pageSize;
        this.option.totalPage = Math.ceil(total/pageSize);
        this.render();
    },
    go:function(page){
        if(this.option.loading){
            return;
        }
        
        if(this.option.totalPage==0) {
            return;
        };
         
        if(page > this.option.totalPage){
            return;
        }

        if(page < 1 && this.option.index == 1){
            return;
        }

        page = page < 1 ? 1 : page;
        page = page > this.option.totalPage ? this.option.totalPage : page;
        this.option.index = page;
        this.render();
        this.option.onChange(this.option.index)
    },
    render:function(){
        
        var html = [],name;
        for(var i=0;i<this.option.views.length;i++){
            name = this.option.views[i];
            html.push(this.templates(name));
        }
        this.element.find("ul").html(html.join(''));
    },
    templates:function(name, data){
        var self = this;
        var tmps = {
            'first' : function(){
                    return '<li><a href="javascript:;" class="btn btn-default laypage_first" data-page="1"  title="首页">首页</a></li>'
       
            },
            'prev' : function(){
                    var index = self.option.index - 1;
                    return '<li><a href="javascript:;" class="btn btn-default laypage_first" data-page="'+ (index < 1 ? 1 : index) +'">上页</a></li>'
            },
            'group':function(){
                var currGroup = self.getCurrGroups(),i=currGroup[0],html='';
                for(;i<=currGroup[1];i++){
                    if(i == self.option.index){
                        html += '<li class="active"><a class="page-curr-number">'+i+'</a><li>'
                    }else{
                        html += '<li><a class="page-number" href="javascript:;" data-page="'+i+'">'+i+'</a></li>'
                    }
                }
                return html;
            },
            'info':function(){
                return '<li><span class="laypage-info"> '+self.option.index+'/'+self.option.totalPage+' </span></li>';
            },
            'next':function(){
                    var index = self.option.index + 1;
                    return '<li><a href="javascript:;" class="btn btn-default laypage_last" data-page="'+ (index > self.option.totalPage ? self.option.totalPage : index) +'">下页</a></li>';
            },
            'end':function(){
                    return '<li><a href="javascript:;" class="btn btn-default laypage_last" title="末页"  data-page="'+ self.option.totalPage +'">末页</a></li>';
            },
            'jump':function(){
                return '<li class="page-jump" style="display:inline-block;">到第 <input type="text" class="pageNum"> 页 <button class="goPage">确定</button></li>'
            }
        }
        try{
            return tmps[name]();
        }catch(e){
            alert(name)
        }
        
    },
    getCurrGroups:function(){
        var index = this.option.index, self = this;
        var poor = this.option.groups%2 == 0 ? Math.floor(this.option.groups)/2 : Math.floor(this.option.groups-1)/2;
        var min=(this.option.index -poor);
        
        var one =  min <= 1 ? 1 : (min >= this.option.totalPage-this.option.groups+1 ? this.option.totalPage-this.option.groups+1 : min);
        
        var last = index > 1 ? (function(){
            var max = index + poor;
            if(max < self.option.groups){
                max = self.option.groups;
            }
            return max;
            
        }()) : this.option.groups;
        if(this.option.totalPage == 0){
            return [1,1];
        }
        return [one, last > self.option.totalPage ? self.option.totalPage : last];
    },
    bind:function(){
        var self = this;
        this.element.delegate('a', 'click', function(){
            var p = $(this).attr('data-page');
            if($(this).hasClass('page-curr-number')) return;
            if(self.option.index == p) {return};
            self.go(+p);
            
        })
        this.element.delegate('.goPage', 'click', function(){
            var p = $.trim(self.element.find('.pageNum').val());
            if(!/^[1-9]?[0-9]*$/.test(p)) {return;}
            if(self.option.index == p) {return};
            self.go(+p);
            
        })
    },
    unbind:function(){
        this.element.unbind();
    },
    destroy:function(){
        this.unbind();
        this.element.remove();
    }
})


//注册input附加组件
widget.defineInputPlugin = function(name, object){
    if(name && object){
        widget.define('plugin-'+name, object);
    }
}

widget.createInputPlugin = function(name, object){
    return widget.create('plugin-'+name, object);
}


widget.defineInputPlugin('date', {
    _defaultOption:{
        format:'yyyy-mm-dd',
        forceParse : false,
        autoclose:true,
        target:null,
        minView: "month",
        onChange:null
        
    },
    _init:function(option){
        this.callParent(option);
        this._create();
    },
    _create:function(){
        $(this.option.target).datetimepicker(this.option);
        if(this.option.onChange){
            $(this.option.target)
            .datetimepicker().on('changeDate', this.option.onChange)
        }
    },
    destroy:function(){
        $(this.option.target).datetimepicker('remove').unbind("changeDate");
    },
    setStartDate:function(date){
        $(this.option.target).datetimepicker('setStartDate', date);
    },
    setEndDate:function(date){
        $(this.option.target).datetimepicker('setEndDate', date);
    }
})


widget.define('baseField', {
    _defaultOption:{
        width:'',
        height:'',
        style:'',
        placeholder:'',
        clesses:'aaaaaa', //类名,
        id:'', //id名称
        value : '', //默认的属性值
        name:'', //name属性
        maxLength : '',//最大长度 
        editable : true,  //是否可以编辑
        onBlur   : false, //是否绑定onBlur事件验证
        onChange : true,
        attr:{}           //要绑定到input上的attribute属性
    },
    showErrorMsg:function(message){
          var msg = widget.create('message',{});
          msg.show('warning', message);
    },
    _init:function(option){
    
        this.callParent(option);
        
        this.type = this.option.type;
    },
    disable:function(){
        this.element.attr('disabled', 'disabled');
    },
    active:function(){
        this.element.removeAttr('disabled');
    },
    show:function(){
        this.element.parents('.widget-form-col').show();
    },
    hide:function(){
        this.element.parents('.widget-form-col').hide();
    },
    setValue:function(value){
        var self = this;
        this.element.val(value);
        self.fire('onChange', {element:self.element, value:self.getValue(), name:self.name});
    },
    _create:function(){
        this.callParent();
        if(this.option.name){
            (this.type !='checkbox' && this.type!=='radio') && this.element.attr('name', this.option.name);
            this.name = this.option.name;
        }
        
        if(this.option.value){
            this.setValue(this.option.value);
        }
        
        if(this.option.aliasName){
            this.element.attr('alias-name', this.option.aliasName);
        }
        
        
        if(this.option.disabled){
            this.element.attr('disabled', 'disabled');
        }else{
            
            if(this.option.readonly){
                if(['checkbox', 'radio', 'select'].join('').indexOf(this.type) ==-1){
                    this.element.attr('readonly','readonly');
                }else{
                    this.element.attr('disabled', 'disabled');
                }
            }
        }
        
        if(this.option.maxLength){
            this.element.attr('maxlength',this.option.maxLength);
        }
        
        if(this.option.classes){
            this.element.addClass(this.option.classes)
        }
        
        for(var k in this.option.attr){
            this.element.attr(k, this.option.attr[k])
        }
        
        
        //如果有配置input附加组件，则创建
        if(this.option.plugin !== undefined && this.option.plugin.name){
            try{
                var config = this.option.plugin.config || {};
                config.target = this.element;
                this.plugin = widget.createInputPlugin(this.option.plugin.name,config);
                
            }catch(e){
                window.console && console.log('int inputPlugins '+this.option.plugin.name+' error ')
            }
        }
        
    },
    bind:function(){
        var self = this;
        switch(this.type){
            case 'password' :
            case 'text':
            case 'textarea':
            
               if(this.option.onBlur){
                   this.element.bind('blur', function(){
                       self.fire('onBlur', self.element, self.getValue());
                       self.check();
                   })
               }
               
               
               
               if(this.option.onChange){
                   var timer = null;
                   
                   this.element.bind('change', function(){
                

                           if(self.check()){
                        
                               self.fire('onChange', {element:self.element, value:self.getValue(), name:self.name});
                           }
                           
                       
                   })
               }
               break;
            case 'radio':
            case 'checkbox':
                this.element.delegate('[name='+self.name+']','click', function(){
                    if(self.check()){
                        self.fire('onChange', {element:self.element, value:self.getValue(), name:self.name});
                    }
                })
                break;
            case 'select':
                if(this.option.onChange){
                   this.element.bind('change', function(){
                       if(self.check()){
                         self.fire('onChange', {element:self.element, value:self.getValue(), name:self.name});
                       }
                   })
               }
                break;
            case 'file':
               if(this.option.onChange){
                   
                   //图片预览
                   function ViewImg(fileObj, viewId){
                     var allowExtention = ".jpg,.bmp,.gif,.png"; //允许上传文件的后缀名document.getElementById("hfAllowPicSuffix").value;
                     var extention = fileObj.value.substring(fileObj.value.lastIndexOf(".") + 1).toLowerCase();
                     var browserVersion = window.navigator.userAgent.toUpperCase();
                     var wrap = document.getElementById(viewId);
                     if(!wrap) return;
                     var img = document.createElement('img');
                     img.style.cssText="width:100%;height:auto;";
                     if (allowExtention.indexOf(extention) > -1) {
                         if (fileObj.files) {//HTML5实现预览，兼容chrome、火狐7+等
                             if (window.FileReader) {
                                 var reader = new FileReader();
                                 reader.onload = function (e) {
                                     
                                     wrap.appendChild(img);
                                     img.setAttribute("src", e.target.result);
                                 }
                                 reader.readAsDataURL(fileObj.files[0]);
                             } else if (browserVersion.indexOf("SAFARI") > -1) {
                                 alert("不支持Safari6.0以下浏览器的图片预览!");
                             }
                         } else if (browserVersion.indexOf("MSIE") > -1) {
                             if (browserVersion.indexOf("MSIE 6") > -1) {//ie6
                                 wrap.appendChild(img);
                                 img.setAttribute("src", fileObj.value);
                             } else {//ie[7-9]
                                 fileObj.select();
                                 if (browserVersion.indexOf("MSIE 9") > -1||browserVersion.indexOf("MSIE 8") > -1){
                                    //不加上document.selection.createRange().text在ie9和ie8会拒绝访问
                                     fileObj.blur();
                                 }
                                 wrap.style.filter = "progid:DXImageTransform.Microsoft.AlphaImageLoader(sizingMethod='scale',src='" + document.selection.createRange().text + "')";
                             }
                         } else if (browserVersion.indexOf("FIREFOX") > -1) {//firefox
                             var firefoxVersion = parseFloat(browserVersion.toLowerCase().match(/firefox\/([\d.]+)/)[1]);
                             wrap.appendChild(img);
                             if (firefoxVersion < 7) {//firefox7以下版本
                                 img.setAttribute("src", fileObj.files[0].getAsDataURL());
                             } else {//firefox7.0+                    
                                 img.setAttribute("src", window.URL.createObjectURL(fileObj.files[0]));
                             }
                         } else {
                             wrap.appendChild(img);
                             img.setAttribute("src", fileObj.value);
                         }
                     } else {
                       
                     }
                   }
                   
                   this.element.bind('change', function(){
                       if(self.option.viewId){
                          ViewImg($(this)[0], self.option.viewId);
                       }
                       if(self.check()){
                         self.fire('onChange', {element:self.element, value:self.getValue(), name:self.name});
                       }
                   })
               }
        }

        if(this.focus){
            self.fire('onChange', {element:self.element, value:self.getValue(), name:self.name});
        }
    },
    check:function(){
        var val = $.trim(this.getValue());
        var name = this.getName();
        
        
        var required;
        if($.isFunction(this.option.required)){
            required = this.option.required();
        }else{
            required = this.option.required
        }
        
        if(!required && val == ''){
           return true;
        }
        
        if(required && val == ''){
            this.element.parents('.form-group').removeClass('has-success').addClass('has-error');
            this.element.focus();
            this.option.requiredError && this.showErrorMsg(this.option.requiredError);
            this.fire('error', 'required', this.option.requiredError,this);
            this.option.onError && this.option.onError(this);
            return false;
        }
        
        if(this.option.minLength && (val.length < this.option.minLength)){
            this.element.parents('.form-group').removeClass('has-success').addClass('has-error');
            this.element.focus();
            this.option.minLengthError&&this.showErrorMsg(this.option.minLengthError);
            this.fire('error','minLength', this.option.minLengthError, this);
            return false;
        }
        
        if(this.option.maxLength && (val.length > this.option.maxLength)){
            this.element.parents('.form-group').removeClass('has-success').addClass('has-error');
            this.element.focus();
            this.option.maxLengthError&&this.showErrorMsg(this.option.maxLengthError);
            this.fire('error','maxLength', this.option.maxLengthError, this);
            return false;
        }
       
        if(this.option.regx){
            this.regx = new RegExp(this.option.regx);
            
        }
        
        if(this.regx &&　!this.regx.test(val)){
            this.element.parents('.form-group').removeClass('has-success').addClass('has-error');
            this.element.focus();
            this.option.regxError && this.showErrorMsg(this.option.regxError);
            this.fire('error', 'regx',this.option.regxError, this);
            this.onError && this.onError(this);
            return false;
        }
        
        if(this.option.checkFn && $.isFunction(this.option.checkFn)){
            var hd = this.option.checkFn;
            var ret = hd(this);
            if(ret === false){
                this.element.focus();
                this.element.parents('.form-group').removeClass('has-success').addClass('has-error');
                this.fire('error', this);
                return false;
            }else if(ret === true){
                this.element.parents('.form-group').removeClass('has-error').addClass('has-success');
                this.fire('success', this);
                return true;
            }else if(typeof ret === 'string'){
                 this.element.focus();
                 this.element.parents('.form-group').removeClass('has-success').addClass('has-error');
                 this.fire('error', 'checkFn', ret);
                 return false;
            }
        }
        
        
        this.element.parents('.form-group').removeClass('has-error').addClass('has-success');
        this.fire('success', this.option.successMsg,  this);
        return true;
    },
    getValue:function(){
         var val = this.element.val();
         return val === null ? '' : val;
    },
    getName:function(){
         return this.element[0].tagName;
    },
    destroy:function(){
        this.plugin && this.plugin.destroy();
        this.plugin = null;
    }
    
})

//创建文本框组件
widget.define('textFeild', {
    extend:'baseField',
    _defaultOption:{
        tpl:'<input type="text" class="form-control" />',
        type:'text'
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'textFeild'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        this.callParent();
        if(this.option.placeholder){
            this.element.attr('placeholder', this.option.placeholder);
        }
    }
})

//隐藏域类型
widget.define('hiddenFeild', {
    extend:'baseField',
    _defaultOption:{
        tpl:'<input type="hidden" class="form-control" />',
        type:'hidden'
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'hiddenFeild'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        this.callParent();
    }
    
})

 //创建文本框组件
widget.define('positiveintegertextFeild', {
    extend:'baseField',
    _defaultOption:{
        tpl:'<input type="text" class="form-control" onkeyup="this.value=this.value.replace(/\\D/g,\'\')" onafterpaste="this.value=this.value.replace(/\\D/g,\'\')" />',
        type:'text'
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'positiveintegertextFeild'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        this.callParent();
        if(this.option.placeholder){
            this.element.attr('placeholder', this.option.placeholder);
        }
    }
})
//创建textarea框组件
widget.define('textareaFeild', {
    extend:'baseField',
    _defaultOption:{
        tpl:'<textarea class="form-control"></textarea>',
        rows:3
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'textareaFeild'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        this.callParent();
        var maxLength = this.option.maxLength;
        if(this.option.rows){
            this.element.attr('rows', this.option.rows);
        }
        if(this.option.placeholder){
            this.element.attr('placeholder', this.option.placeholder);
        }
    }
})

//创建file组件
widget.define('fileFeild', {
    extend:'baseField',
    _defaultOption:{
        tpl:'<input type="file" class="form-control" />',
        checked: false
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'fileFeild'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        this.callParent();
        var checked = this.option.checked;
    }
})

//创建文本框组件
widget.define('selectFeild', {
    extend:'baseField',
    _defaultOption:{
        tpl:'<select class="form-control"></select>',
        items:[], //option 选项,例子[{text:'1111', value:'1111', selected:true}]
        defaultValue:'-1'
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'selectFeild'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        this.callParent();
        var maxLength = this.option.maxLength;
        var items = this.option.items;

        
        if(this.option.placeholder){
            this.element.append('<option value="'+this.option.defaultValue+'">'+this.option.placeholder+'</option>')
        }
        if(items &&　items.length){
            for(var i=0;i<items.length;i++){
                if(typeof items[i] == 'object'){
                    var selected = false;
                    if(items[i].selected) {
                        selected = true;
                    }
                    if(items[i].value === this.option.value){
                        selected = true;
                    }

                    this.element.append('<option '+(selected ? 'selected = "selected"' : '')+' value="'+items[i].value+'">'+items[i].text+'</option>')
                }
            }
        }
    }
})

//普通文本组件
widget.define('infoFeild', {
    extend:'baseField',
    _defaultOption:{
        tpl:'<div class="form-control-static"></div>',
        defaultValue:'-1'
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'infoFeild'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        this.callParent();
        this.element.append(this.option.value || '')       

    }
})

//创建checkbox组件
widget.define('checkboxFeild', {
    extend:'baseField',
    _defaultOption:{
        tpl:'<span class="checkbox-group" style="display:inline-block;vertical-align:middle;"></span>',
        items:[], //选项,例子[{text:'1111', value:'1111', checked:true}]
        type:'checkbox'
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'checkboxFeild'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        this.callParent();
        var items = this.option.items;
        var readonly = this.option.readonly;
        
        if(items &&　items.length){
            for(var i=0;i<items.length;i++){
                if(typeof items[i] == 'object'){
                    this.element.append('<label class="checkbox-inline '+(items[i].classes || '')+'"><input '+(readonly===true ? 'disabled="disabled"' : '')+' type="checkbox" value="'+items[i].value+'" '+(items[i].checked ? 'checked="checked"':'')+ 'name="'+(this.name)+'">'+(items[i].text||'')+'</label>')
                }
            }
        }
    },
    disable:function(){
        this.element.find('input').attr('disabled', 'disabled');
    },
    active:function(){
        this.element.find('input').removeAttr('disabled');
    },
    check:function(){
        var self =this, res= false;
        
        if(this.option.checkFn && $.isFunction(this.option.checkFn)){
            var hd = this.option.checkFn;
            var ret = hd(this);
            
            if(ret === false){
                this.element.focus();
                this.element.parents('.form-group').removeClass('has-success').addClass('has-error');
                this.fire('error', this);
                return false;
            }else if(ret === true){
                this.element.parents('.form-group').removeClass('has-error').addClass('has-success');
                this.fire('success', this);
                return true;
            }
        }
        
        var required;
        if($.isFunction(this.option.required)){
            required = this.option.required();
        }else{
            required = this.option.required
        }

        
        if(required){
            this.element.find('[name='+this.name+']').each(function(item, i){
                if($(this)[0].checked){
                    res = true;
                }
            })
            if(res === false){
                this.element.parents('.form-group').removeClass('has-success').addClass('has-error');
                this.fire('error','required', this.option.requiredError, this);
                return res;
            }
            this.element.parents('.form-group').removeClass('has-error').addClass('has-success');
            self.fire('success', self);
            return res;
        }else{
            this.element.parents('.form-group').removeClass('has-error').addClass('has-success');
            self.fire('success', self);
            return true;
        }
    },
    getValue:function(){
        var value = [];
        this.element.find('input').each(function(){
            if($(this)[0].checked){
                value.push($(this).val());
            }
        })
        return value.join(',');
    },
    setValue:function(value){
        var self = this;
        if(typeof value === 'string'){
            value = value.split(',');
        }
        
        
        for(var i=0;i<value.length;i++){
            
            this.element.find('input').each(function(){
                if($(this).val() == value[i]){
                     $(this).attr('checked', 'checked');
                     self.fire('onChange', {element:self.element, value:self.getValue(), name:self.name});
                }
            })
        }
        
    }
})

 //创建radio组件
widget.define('radioFeild', {
    extend:'baseField',
    _defaultOption:{
        tpl:'<span class="radio-group" style="display:inline-block;vertical-align:middle;"></span>',
        items:[], //选项,例子[{text:'1111', value:'1111', checked:true}]
        type:'radio'
    },
    _init:function(option){
        this.callParent(option);
        if(this.ClassName == 'radioFeild'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        this.callParent();
        var items = this.option.items;
        var readonly = this.option.readonly;
        if(items &&　items.length){
            for(var i=0;i<items.length;i++){
                if(typeof items[i] == 'object'){
                    this.element.append('<label class="radio-inline '+(items[i].classes || '')+'"><input '+(readonly === true ? 'disabled="disabled"' : '')+' type="radio" '+((items[i].checked || (this.option.value !== undefined && this.option.value == items[i].value)) ? 'checked="checked"':'')+' value="'+items[i].value+'" name="'+(this.name)+'">'+(items[i].text||'')+'</label>')
                }
            }
        }
    },
    disable:function(){
        this.element.find('input').attr('disabled', 'disabled');
    },
    active:function(){
        this.element.find('input').removeAttr('disabled');
    },
    check:function(){
        var self = this, res= undefined;
        
        if(this.option.checkFn && $.isFunction(this.option.checkFn)){
            var hd = this.option.checkFn;
            var ret = hd(this);
            
            if(ret === false){
                this.element.focus();
                this.element.parents('.form-group').removeClass('has-success').addClass('has-error');
                this.fire('error', this);
                return false;
            }else if(ret === true){
                this.element.parents('.form-group').removeClass('has-error').addClass('has-success');
                this.fire('success', this);
                return true;
            }
        }
        
        var required;
        if($.isFunction(this.option.required)){
            required = this.option.required();
        }else{
            required = this.option.required
        }

        if(required){
            this.element.find('[name='+this.name+']').each(function(item, i){
                if($(this)[0].checked){
                    res = true;
                }
            })
            
            if(res === false||res===undefined){
                
                this.element.parents('.form-group').removeClass('has-success').addClass('has-error');
                this.fire('error','required', this.option.requiredError, this);
                return res;
            }
            this.element.parents('.form-group').removeClass('has-error').addClass('has-success');
            self.fire('success', self);
            return res;
        }else{
            this.element.parents('.form-group').removeClass('has-error').addClass('has-success');
            self.fire('success', self);
            return true;
        }
    },
    getValue:function(){
        var value = '';
        this.element.find('input').each(function(){
            if($(this)[0].checked){
                value = $(this).val();
                return false;
            }
        })
        return value;
    },
    setValue:function(value){
        var self = this;
        this.element.find('input').each(function(){
            if($(this).val() == value){
                 $(this).attr('checked', 'checked');
                 self.fire('onChange', {element:self.element, value:self.getValue(), name:self.name});
            }
        })
    }
})

//form表单
widget.define('form',{
    _defaultOption:{
        tpl:'<div class="widget-form"><form></form></div>',
        formType:'horizontal', //表单类型, ['horizontal', 'inline', vertical],
        method:'post',//表单提交类型
        url:'',//form提交的url地址
        name:'', //表单的name值
        size : 'sm',
        labelCol:3,
        editable:true,
        inputCol:8,
        rowNum: 1,//在水平表单的情况下，一行显示表单的数量
        target:'',//表单的提交目标
        enctype:'application/x-www-form-urlencoded',
        validation : true,//是否开启验证,
        plusabled : true, //是否开启组件功能,比如日历组件等等,
        items:[],
        renderTo: null,
        onChange:noop
    },
    _init:function(option){
        
        this.callParent(option);
        //是否有文件表单类型
        this.hasFile = false;
        this.inputs = [];
        if(this.ClassName == 'form'){
            this._create();
        }
    },
    _create:function(){
        this.callParent();
        this.form = this.element.find('form');
        if(this.option.formType == 'horizontal'){
            this.form.addClass('form-horizontal');
        }else if(this.formType == 'inline'){
            this.form.addClass('form-inline');
        }
        this.form.attr('enctype', this.option.enctype).attr('method', this.option.method);
        
        if(this.option.url){
            this.form.attr('action', this.option.url);
        }
        if(this.option.target){
            this.form.attr('target', this.option.target);
        }
        
        if(this.option.classes){
            this.element.removeClass(this.option.classes);
            this.form.addClass(this.option.classes);
        }
        
        var items = this.option.items;
        if(this.option.formType == 'horizontal'){
            var rowNum = parseInt(12/this.option.rowNum);
        
            var rowTotal = Math.ceil((items.length)/this.option.rowNum), row, item;
            
            
                
                for(var j=0;j<items.length;j++){
                    
                    if(items[j] && items[j].type == 'hidden'){
                        var ele = this._createInput(items[j]).getElement();
                        this.form.append(ele);
                        //this.form.append('<input type="hidden" name="'+items[j].name+'" value="'+(items[j].value||'')+'" />');
                        items.splice(j,1);
                        j--;
                    }
                }
            
            
            
            while(items.length){
                
                row = $('<div class="row"></div>');
                for(var i=0;i<this.option.rowNum;i++){
                    item = items[0];
                    items.splice(0,1);
                    if(item){
                        //是否单独一行
                        var oneRow = item.oneRow;
                        var col = $('<div class="widget-form-col col-'+this.option.size+'-'+(rowNum)+'"></div>');
                        var group = $('<div class="form-group"></div>');
                        
                        if(this.option.hideLabel !== true){
                            group.append('<span title="'+(item.label || '')+'" for="'+(item.name || '')+'" class="col-'+this.option.size+'-'+(item.labelCol || this.option.labelCol)+' control-label">'+(item.required ? '<span class="text-danger">*</span> ' : '')+(item.label || '')+'：</span>');
                        }
                        
                        var inputs = this._createInput(item);

                        this.inputs.push(inputs);
                        try{
                            inputs = inputs.getElement();
                        }catch(e){
                            
                        }
                        
                        var inputCol = 12;
                        if(this.option.hideLabel !== true){
                            inputCol = item.inputCol || this.option.inputCol;
                        }
                        
                        var inputWrap = $('<div class="input-wrap col-'+this.option.size+'-'+(inputCol)+'"></div>');
                        inputWrap.append(inputs);
                        
                        group.append(inputWrap);
                        
                        //是否有用户自定义的dom要添加进来
                        if(item.customDom){
                            if($.isFunction(item.customDom)){
                                item.customDom(group);
                            }else{
                                try{
                                    group.append(item.customDom);
                                }catch(e){
                                    window.console && console.log('form->customDom->Error');
                                }
                            }
                        }
                        
                        
                        col.append(group);
                        try{
                            row.append(col);
                        }catch(e){
                            window.console&&console.log(item)
                        }
                        
                        item.tipMsg && inputWrap.append('<span class="help-block">'+item.tipMsg+'</span>');
                        if(item.append && $.isFunction(item.append)){
                            item.append(row);
                        }
                        if( oneRow === true){
                            break;
                        }
                        
                    }
                    if( items[0] && (items[0].oneRow === true)){
                        break;
                    }
                }
                this.form.append(row);
            }
        }
        
        this.option.renderTo && this.element.appendTo(this.option.renderTo);
    },
    getInput:function(name){
        for(var i=0;i<this.inputs.length;i++){
            
            if(this.inputs[i].name == name){
                return this.inputs[i];
            }
        }
        return null;
    },
    getInputByIndex:function(index){
        return this.inputs[index];
    },
    _createInput:function(item){
        var type = item.type || 'text';
        item.editable = item.editable === undefined ? this.option.editable : item.editable;
        
        switch(type){
            case 'info':
                var input = widget.create(type+'Feild', item);
                return input;
                break;
            case 'text':
            case 'password':
            case 'file':
            case 'textarea':
            case 'select':
            case 'checkbox':
            case 'radio':
            case 'positiveintegertext':
                var input = widget.create(type+'Feild', item);
                return input;
                break;
            case 'hidden':
                var input = widget.create(type+'Feild', item);
                return input;
                break;
        }
    },
    disable:function(name){
        for(var i=0;i<this.inputs.length;i++){
            if(name){
                if(this.inputs[i].name === name){
                    this.inputs[i].disable();
                }
            }else{
                this.inputs[i].disable();
            }
        }
    },
    active:function(names){
        names = names ||[];
        names = names.join(',');
        for(var i=0;i<this.inputs.length;i++){
            if(names){
                if(names.indexOf(this.inputs[i].name)!= -1){
                    this.inputs[i].active();
                }
            }else{
                this.inputs[i].active();
            }
        }
    },
    hideInput:function(name){
        for(var i=0;i<this.inputs.length;i++){
            if(this.inputs[i].name === name){
                this.inputs[i].hide();
            }
        }
    },
    showInput:function(name){
        for(var i=0;i<this.inputs.length;i++){
            if(this.inputs[i].name === name){
                this.inputs[i].show();
            }
        }
    },
    //验证
    valid:function(){
        for(var i=0;i<this.inputs.length;i++){
            if(!this.inputs[i].check()){
                return false;
            }
        }
        return true;
    },
    submit:function(){
        if(this.valid()!==false && this.fire('beforeSubmit')!==false){
            this.form.submit();
        }
    },
    destroy:function(){
        
        try{
            for(var i=0;i<this.inputs.length;i++){
                
                this.inputs[i].destroy();
                
            }
        }catch(e){
            
        }
        this.callParent();
    },
    getValue:function(name){
        for(var i=0;i<this.inputs.length;i++){
            if(this.inputs[i].name === name){
                return this.inputs[i].getValue();
            }
        }
    },
    setValue:function(dataObj){
        
        for(var k in dataObj){
            
            for(var i=0;i<this.inputs.length;i++){
                if(this.inputs[i].name === k){
                    this.inputs[i].setValue(dataObj[k]);
                }
            }
        }
    },
    reset: function(){
        try{
            this.element.find('form')[0].reset();
        }catch(e){
            console(e)
        }
    },
    bind:function(){
        this.callParent();
        var self = this;
        this.element.find('form').on('submit', function(e){
            e.preventDefault();
            if(self.valid() && self.option.onSubmit){
                self.option.onSubmit();
            }
            return false;
        })
    }
})

//定位到指定元素的周围
widget.define('around', {
    _defaultOption:{
        tpl:'<div class="around"></div>',
        cssPosition:'absolute',
        autoHide: true,
        closeBtn : false, //是否显示关闭按钮
        renderType:'body', //生成到target元素的父级下，即同级，其它值则生成到body下
        target : null, //要出现周围的元素
        autoPos: true, //是否自动调整位置
        resetTarget : $(document), //自动调整位置时的参考目标，默认是document
        pos:'bottom',
        offset:0,
        autoHide:true
    },
    _init:function(option){
        this.callParent(option);
        if(!this.guid){
            this.guid = guid();
        }
        if(this.ClassName == 'around'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        this.callParent();
        var target = (this.option.target instanceof jQuery) ? this.option.target : $(this.option.target);
        var renderType = this.option.renderType;
        this.element.css('position', this.option.cssPosition);

        if(renderType == 'parent'){
            this.element.appendTo(target.parent());
        }else{
            this.element.appendTo($('body'));
        }

        this.setPos();
    },
    setPos:function(){
        var renderType = this.option.renderType, cpos={},pos;
        var resetTarget = this.option.resetTarget instanceof jQuery ? this.option.resetTarget : $(this.option.resetTarget);
        var target = (this.option.target instanceof jQuery) ? this.option.target : $(this.option.target);

        if(renderType === 'parent'  && resetTarget[0]!=$(document)[0]){

            cpos = target.position();
        }else{
            cpos = target.offset();
        }
        pos = this.option.pos;
        var w = this.element.width();
        var h = this.element.height();

        if(this.option.autoPos){
            var resetTarget = this.option.resetTarget instanceof jQuery ? this.option.resetTarget : $(this.option.resetTarget);
            var offset = resetTarget.offset();
            var tw = resetTarget.width();
            var th = resetTarget.height();
            var tst = resetTarget.scrollTop();
            var tsl = resetTarget.scrollLeft();
            var tt = offset == null ? 0 : offset.top;
            var tl = offset == null ? 0 : offset.left;

            if(pos == 'bottom'){
                var t = cpos.top+target.outerHeight()+this.option.offset;
                var l  = cpos.left;
                if( t+h > ((document.documentElement.clientHeight || document.body.clientHeight))+tst){
                    t = cpos.top-this.option.offset;
                }
                
            }else if(pos == 'right'){
                var t = cpos.top;
                var l = cpos.left+target.width()+this.option.offset;
                if(l+w > tw+tsl){
                    l = cpos.left-w-this.option.offset+tsl;
                }
            }else if(pos == 'top'){
                var t = cpos.top-h-this.option.offset;
                var l  = cpos.left;

                if(t<0){
                    t = cpos.top+target.height()+this.option.offset;
                }

            }else if(pos == 'left'){
                var t = cpos.top;
                var l = cpos.left-w-this.option.offset+tsl;
                if(l<0){
                    l = cpos.left+target.width()+this.option.offset;
                }
            }
        }
        
        this.element.css({left:l, top:t});
    },
    show:function(){
       this.callParent();
       this.setPos();
       
    },
    bind:function(){
        this.callParent();
        var self = this;
        if(this.option.autoHide){
            $(document).bind('mousedown.around'+this.guid, function(){
                self.hide();
            })
        }
    },
    unbind:function(){
        this.callParent();
        $(document).unbind('mousedown.around'+this.guid);
    }
})

//tab切换项
widget.define('tab', {
    _defaultOption:{
        tpl:'<div class="widget-tab"></div>',
        classes:'',
        btnClasses:'tab-btn',
        contentClasses:'tab-cont',
        index:0,
        width:'100%',
        id:'',
        items:[{
            title:'标签1',
            content:'' //或者是函数
            
        },{
            title:'标签2',
            content:'' //或者是函数
        }
        ]
    },
    _init:function(option){
        this.callParent(option);
        this.index = -1;
        this._create();
        this.bind();
    },
    _create:function(){
        this.callParent();
        var items = this.option.items, item;
        this.element.append('<div class="hd"></div>');
        this.element.append('<div class="bd"></div>');
        this.header = this.element.find('.hd');
        this.content = this.element.find('.bd');
        
        for(var i=0;i<items.length;i++){
            item = items[i];
            var content;
            if($.isFunction(item.content)){
                content = item.content();
            }else {
                content = item.content || '';
            }
            this.header.append('<span class="tab-btn '+this.option.btnClasses+'">'+item.title+'</span>');
            var $contentOuter = $('<div style="display:none;" class="tab-cont '+this.option.contentClasses+'"></div>');
            $contentOuter.append(content);
            this.content.append($contentOuter)
        }
        
        if(this.option.renderTo){
            this.element.appendTo((this.option.renderTo));
        }
        
        if(this.option.index >= 0){
            this.showIndex(this.option.index);
        }
    },
    add:function(item){
        this.option.items.push(item);
        var content;
        if($.isFunction(item.content)){
            content = item.content();
        }else {
            content = item.content || '';
        }
        this.header.append('<span class="'+this.option.btnClasses+'">'+item.title+'</span>');
        this.content.append('<div style="display:none;" class="'+this.option.contentClasses+'">'+content+'</div>')
    },
    showIndex:function(index){
        
        
        if(this.index !== index && this.index >= 0){
            this.fire('onHide',  this.option.items[this.index], this.index, this.content.find('.'+this.option.contentClasses).eq(this.index));
        }
        this.index = index;
        this.header.find('.tab-btn').removeClass('active').eq(index).addClass('active');
        this.content.find('.'+this.option.contentClasses).hide().eq(index).show();
        
        this.fire('onChange', this.option.items[index], index, this.content.find('.'+this.option.contentClasses).eq(index));
    },
    setContent:function(index, content){
        this.content.find('.'+this.option.contentClasses).eq(index).append(content);
    },
    bind:function(){
        var self = this;
        this.callParent && this.callParent();
        this.element.delegate('.tab-btn', 'click', function(e){
            var index = $(this).index();
            if(index === self.index) return;
            self.showIndex(index);
        })
    },
    getIndex:function(){
        return this.index||0;
    },
    destroy:function(){
        var index = this.index;
        this.fire('onDestroy', this.option.items[index], index, this.content.find('.'+this.option.contentClasses).eq(index));
        this.callParent();
    }
})

//手风琴
widget.define('accordion', {
    _defaultOption:{
        tpl:'<div class="accordion"></div>',
        multiple:false,//是否多选
        items:[], //配置数据
        animate:true,//折叠时是否启动动画
        showIcon : true,
        iconClasses:'',
        dIconClasses:'', //默认的icon类名
        iconPos:'left',
        quickHide : true //是否点击头部切换状态
    },
    _init:function(option){
        this.callParent(option);
        //对象缓存
        this.items = [];
        if(this.ClassName == 'accordion'){
            this._create();
            this.bind();
        }
    },
    _create:function(){
        this.callParent();

        if(this.option.animate){
            this.element.addClass('animate');
        }

        //创造主体
        var items = this.option.items;
        if($.isArray(items) && items.length>0){
            for(var i=0;i<items.length;i++){
                var state = items[i].state || 'collaspe';
                var group = $('<div data-index="'+i+'" class="accordion-item '+state+'"></div>');
                var head = $('<div data-index="'+i+'" class="accordion-item-head"></div>');
                var content = $('<div data-index="'+i+'" class="accordion-item-body " style="height:'+(state == 'collaspe' ? 0 : 'auto')+'"></div>')

                //头部a标签带链接
                if(items[i].url){
                    head.append('<a class="accordion-item-tit" href="'+items[i].url+'">'+items[i].title+'</a>')
                }else{
                    head.append('<span class="accordion-item-tit">'+items[i].title+'</span>');
                }

                if(this.option.showIcon){
                    var pos = items[i].iconPos || this.option.iconPos || 'left';
                    if(pos == 'right'){
                        head.prepend('<i class="icon icon-'+state+' pull-right"></i>')
                    }else{
                        head.prepend('<i class="icon icon-'+state+'"></i>')
                    }
                }

                var cont = items[i].content;
                if ($.isFunction(cont)){
                    content.append(cont(items[i]));
                }else{
                    cont && content.append(cont);
                }
                
                group.append(head);
                group.append(content);
                //自定义函数
                items[i].render && items[i].render(items[i], group, i);
                this.element.append(group);

            }
        }
        
    },
    expand:function(index){
        
        if(index !== undefined && typeof parseInt(index) == 'number'){
            var item = this.element.find('.accordion-item').eq(index);
            if(item.length && item.hasClass('collaspe')){
                item.find('i.icon').removeClass('icon-collaspe').addClass('icon-expand')
                item.removeClass('collaspe').addClass('expand');
                item.find('.accordion-item-body').css('height', 'auto');
            }
        }
    },
    expandAll:function(){
        var item = this.element.find('.accordion-item');
        if(item.length && item.hasClass('collaspe')){
            item.find('i.icon').removeClass('icon-collaspe').addClass('icon-expand')
            item.removeClass('collaspe').addClass('expand');
            item.find('.accordion-item-body').css('height', 'auto');
        }
    },
    collaspeAll:function(){
      
            var item = this.element.find('.accordion-item');
            if(item.length && item.hasClass('expand')){
                item.find('i.icon').removeClass('icon-expand').addClass('icon-collaspe')
                item.removeClass('expand').addClass('collaspe');
                item.find('.accordion-item-body').css('height', 0);
            }
        
    },
    collaspe:function(index){

        if(index !== undefined && typeof parseInt(index) == 'number'){
            var item = this.element.find('.accordion-item').eq(index);
            if(item.length && item.hasClass('expand')){
                item.find('i.icon').removeClass('icon-expand').addClass('icon-collaspe')
                item.removeClass('expand').addClass('collaspe');
                item.find('.accordion-item-body').css('height', 0);
            }
        }
    },
    bind:function(){
        this.callParent();
        var self = this;
        this.element.delegate('.accordion-item-head','click', function(e){

            if($(this).parent().hasClass('expand')){
                self.collaspe($(this).attr('data-index'));
            }else if($(this).parent().hasClass('collaspe')){
                if(!self.option.multiple){
                    self.collaspeAll();
                }

                self.expand($(this).attr('data-index'));
            }
        })
    }
})
   
    
    /*
    工具函数 start
 */
var tool = {}, uuid = 1;
tool.strToEle = function(str, parentTag){
    if(!parentTag){
        var fragment = document.createElement('div');
    }else{
        var fragment = document.createElement(parentTag);
    }
    
    fragment.innerHTML = str;
    return fragment.firstChild;
}

//遍历搜索dom及其父级是否包含某个属性
tool.getAttr = function(attr, ele, stopEle){
    if (ele.tagName.toLowerCase() == 'html'){
        return null;
    }
    var v = ele.getAttribute(attr);
    if(!v && ele !== stopEle && stopEle){
        ele = ele.parentNode;
        if(ele){
            return  tool.getAttr(attr, ele, stopEle);
        }else {
            return null;
        }
        
    }else{
        return {
            value : v,
            element : ele
        };
    }
    return null;
}

tool.merge = function(t1, t2){
    if(t1 && t2){
        for(var k in t2){
            if(t1[k] === undefined){
                t1[k] = t2[k];
            }
        }
    }
}


//数据结构转换
tool.translateData = function(data, element){
    var res = {
            data : data,
            element : element || null,
            selected : false,
            translated : true,
            uuid       : tool.getUUID()
        }
    return res;
}

tool.eachData = function (data, fn, context){
   
    var i=0,d=data,len=d.length,result = null;
    for(;i<len;i++){
        result = fn.call(context, d[i], i);
        if(result === false){
            return false;
        }
        if(result){
            return result;
        }
    }
}
tool.getUUID = function(){
    return ++uuid;
}
tool.getFragment = function(){
    return document.createDocumentFragment();
}

tool.noop = function(){};
/*工具函数 end*/

//table 渲染控制器
var view = {
    //创建列表容器
    createTable :function(setting, parentDom){
        var table = $('<table class="table table-list"></table>');
        return table;
    },
    //创建列表头部容器
    createHeader   :function(setting, table){
        var header = $('<thead><tr></tr></thead>');
        table.append(header);
        return header;
    },
    //创建表格body
    createBody : function(setting, table){
        var tbody = $('<tbody></tbody>');
        table.append(tbody);
        return tbody;
    },
    //创建列表项
    createList :function(setting, node, index){
        var selected = node.selected;
        var tr = $('<tr class="'+setting.ListItemClass+' '+(selected ? setting.selectedClass : '')+'" node-type="item" uid="'+node.uuid+'"></tr>');
        this.createListItem(setting, node, tr, index);
        //body.append(tr);
        return tr;
    },
    //创建列表字段项
    createListItem : function(setting, node, tr, index){
        if(setting.selectable){
            this.createListSelectItem(setting, node, tr, index);
        }
        this.renderListItem(setting, node, tr);
    },
    renderListItem:function(setting, node, tr, index){
        var data = node.data;
        var columns = setting.columns;
        var td;
        var ellipsis = setting.ellipsis;
        var customData = null;
        
        
        
        if(setting.toCustomData){
            customData = setting.toCustomData(node.data);
        }
        for(var i=0;i<columns.length;i++){
            var name = columns[i].name;
            if(setting.render && setting.render[name]){
                try{
                    var v= setting.render[name](data[name], data, index, customData),r;
                }catch(e){
                    
                }
                
                if(v === '' || v === undefined || v ===null){
                    v = '-';
                }
                if(ellipsis){
                    r = '<div>'+v+'</div>';
                }
                td = $('<td name="'+ name +'">'+(r||v)+'</td>');
            }else{
                var v = data[columns[i].name];
                
                //去数据中的某个字段中找
                if(!v){
                    if(!setting.otherKey){
                        setting.otherKey = 'fileNomination';//'json';
                    }
                    
                    var otherVal = data[setting.otherKey]
                    try{
                        if(typeof otherVal === 'string'){
                            otherVal = JSON.parse(otherVal);
                        }
                        v = otherVal[columns[i].name]
                    }catch(e){
                        
                    }
                }
                
                if(v === '' || v === undefined || v ===null){
                    v = '-';
                }
                if(ellipsis){
                    v= '<div title="'+(v||'')+'">'+v+'</div>';
                }
                
                td = $('<td name="'+ name +'">'+v+'</td>');
            }
            tr.append(td);
        } 
        td = tr = node = setting = name = null;
    },
    
    //创建列表头部字段
    createHeaderItem : function(setting, header){
        var self = this,
            columns = setting.columns;

        //如果显示选中按钮
        if(setting.selectable){
            this.createAllSelectItem(setting, header);
        }

        tool.eachData(columns, function(d, i){
            self.randerHeaderColumn(setting, d, header);
        })
    },
    randerHeaderColumn:function(setting, data, header){
        var sortClass = (data.sortable && setting.sortField && ((setting.sortField == data.sortCode)  || (setting.sortField == data.name) ) && setting.sortMode) || ''
        var activeClass = (setting.sortField && ((setting.sortField == data.sortCode)  || (setting.sortField == data.name))) ? 'active' : '';
        var width = data.width;
        var th = $('<th '+(width ? 'width='+width : '')+' class="'+setting.headerColumClass+' '+sortClass+' '+activeClass+' '+(data.sortable ? 'sort' : '')+'" data-name="'+ data.name +'" data-sortCode ="'+( data.sortCode? data.sortCode :data.name) +'"  data-sort="'+data.sortVal+'" node-type="'+(data.sortable ? 'sort' : '')+'">'+data.text+'</th>');
        data.element = th;
        if(setting.dragResize){
            th.prepend('<span class="hd-resize-bar"></span>')
        }
        header.find('tr').append(th);
    },
    //创建全选字段项
    createAllSelectItem: function(setting, header){
        var tmp = $('<th width='+setting.selectWidth+' class="'+setting.allSelectItemClass+'"><input type="checkbox" node-type="allSelect" class="'+setting.allSelectInputClass+'" /></th>');
        header.find('tr').append(tmp);
    },
    //创建列表选中字段项
    createListSelectItem : function(setting, node, tr){
        var selected = node.selected;
        if(node.data.claimed){
            if(node.data.claimed == 'y' || node.data.claimed == 'n'){
                var td = $('<td class="'+setting.listSelectedClass+'"><input type="checkbox" node-type="selectInput" class="'+setting.listSelectedInputClass+'" '+(selected ? "checked=checked" : '')+' /></td>');
            }else{
                var td = $('<td class="'+setting.listSelectedClass+'"><input type="checkbox" node-type="selectInput" disabled="true" class="'+setting.listSelectedInputClass+'" '+(selected ? "checked=checked" : '')+' /></td>');  
            }
        }else{
            var td = $('<td class="'+setting.listSelectedClass+'"><input type="checkbox" node-type="selectInput" class="'+setting.listSelectedInputClass+'" '+(selected ? "checked=checked" : '')+' /></td>');
        }
        
        tr.append(td);
    },
    //创建固定表头
    createFixedHeader:function(setting, table){
        var zIndex = +setting.renderTo.css('z-index');
        var wrap = $('<div></div>').css({width:table.width(),position:'absolute',zIndex:zIndex, overflow:'hidden'});
        var tmpTable = $('<table></table>');
        tmpTable.attr('style', table.attr('style')).attr('class', table.attr('class'));
        var header = table.find('thead').clone();
        tmpTable.append(header);
        table.find('thead th').each(function(index, item){
            header.find('th').eq(index).width(item.scrollWidth);
        })
        wrap.append(tmpTable);
        header = tmpTable = null;
        return wrap;
    }
}

//事件控制器
var event = {
    onStartLoad      : tool.noop, //开始加载数据时触发
    onLoaded         : tool.noop, //数据加载完成触发
    onSelectedChange : tool.noop, //当选择项数量有变化时触发
    onComplete       : tool.noop, //数据全部加载完成时触发
    onDestroy        : tool.noop, //列表销毁时触发
    onError          : tool.noop, //当ajax请求发生错误时触发
    onRmoveData      : tool.noop, //当删除一条数据时触发
    onInit           : tool.noop, //列表初始化时触发
    onReLoad         : tool.noop, //当从第一页从新加载时触发
    onAfterLoad      : function(data){return data},
    onEmpty          : function(){},
    _proxy            : function(e, stopEle){ //事件代理
        var info = {}, e = e || window.event;
        var target = e.target || e.srcElement;
        var attrInfo = tool.getAttr('node-type', target, stopEle);
        if(attrInfo){
            info.nodeType = attrInfo.value;
            info.element  = attrInfo.element;
        }
        return info;
    }
}

var defaultColumn = {
    sort : true,
    curr : false,
    sortVal : 'asc'
}

widget.define('tableList', {
    _defaultOption:{
        
    },
    _init:function(setting){
        //默认配置项
        var _setting = {
            emptyMsg: '暂还没有任何内容',
            compluteTotal      : true,
            showHeader         : true,  //是否显示表头
            showPage           : false, //是否显示分页, 如果显示分页，则每次加载新的数据都会替换旧的数据，否则累加数据
            
            url                : '',    //数据请求url
            type               : 'get', //ajax请求类型
            dataType           : 'json',//ajax请求的数据类型
            pageSize           : 50,    //每页请求条数
            pageNumber         : 1,     //当前页码
            dragResize         : true,  //拖拽表头改变列宽
            fixedHeader        : false, //是否固定表头
            interVal           : 1000,   //监听表格宽度变化的间隔，毫秒数
            sortMode           : 'desc',
            ellipsis           : true,      //超长隐藏
            clientSort         : false,     //前端排序, 默认关闭
            headMinWidth       : 80,       //拖拽时表头的默认宽度
            selectWidth        : 30,
            selectable         : true,      //是否显示每条选中及全选input
            headerClass        : 'DataList_header', //表头容器class
            headerColumClass   : 'header_colum',    //表头单元格class
            headerSelectedClass: 'selected',        //如果表头有排序项，则表示选中时的class
            bodyClass          : 'DataList_body',   //列表容器class
            ListItemClass      : 'list_item' ,      //列表项class
            listItemColumClass : 'body_colum' ,     //列表项单元格class
            listSelectedClass  : 'select_wrap',     //列表选中class
            listSelectedInputClass : 'select_input', //列表选中项input的class
            allSelectItemClass : 'hd_colum allSelect_wrap',       //全选表头项容器class
            allSelectInputClass: 'allSelect',       //全选input元素class   
            updateDataByIdHandle : null,            //请求单条数据的代理方法，需要用户单独配置, 因为现在阶段项目的列表接口无法做到统一
            columns            : [],                //表头字段
            view               : {},                //渲染控制器, 可覆盖默认，用于自定义配置
            sourceKey          : 'data',            //ajax请求返回的数据主体
            listKey            : 'list',            //ajax请求列表数据对应的字段key
            codeKey            : 'code',            //用于判断ajax请求是否正常的值
            msgKey             : 'msg_show',             //当code值，异常时的提示信息字段
            filter             : function(data){ return data },         //数据加载过来时用于过滤数据
            event              : {},                 //事件配置
            data               : null,               //默认数据, 为数组
            itemHeight         : 40,                 // 每一个条目的高度
            activeIndex        : 0                  //活动数据在总数据数组中的索引值
        }
        
        this.setting = $.extend(_setting, setting);
        
        this.updateDataByIdHandle = this.setting.updateDataByIdHandle || null;
        
        //渲染控制器
        this.view    = $.extend({}, view, this.setting.view);
        //事件处理控制器
        this.event   = $.extend({}, event, this.setting.event);
        //总dom容器
        this.wrap    = this.setting.wrap;
        //列表头部dom容器
        this.header  = null;
        //列表dom容器
        this.body    = null;
        //总量
        this.total   = 0;
        //用于缓存转换过的数据项，包括数据及dom
        this.cache = [];
        
        if(this.setting.renderTo){
            if(typeof this.setting.renderTo == 'string'){
                this.setting.renderTo = $(this.setting.renderTo);
            }else if(this.setting.renderTo instanceof jQuery){
                
            } 
        }else{
            this.setting.renderTo = $('body');
        }
        this._create();
        this.bindEvent();
        if(this.setting.fixedHeader){
            this.listenResize();
        }
    },
    setTotal:function(total){
        
        this.total = total;
        if(this.isComplete()){
            this.completed = true;
            this.callEvent('onComplete');
        }else{
            this.completed = false;
            this.callEvent('onLoaded');
        }
    },
    _create:function(){
        var self = this;
        //创建列表容器
        this.$wrap = $('<div class="table-list-wrapper"></div>');
        this.table = this.view.createTable(this.setting);
        if(this.setting.ellipsis){
            this.table.addClass('ellipsis-table');
        }
        this.table.css({width: this.setting.width || '', height:this.setting.height || 'auto'});
        this.setting.id && this.table.attr('id', this.setting.id);
        this.setting.classes && this.table.addClass(this.setting.classes);
        //创建列表头部
        if(this.setting.showHeader && this.setting.columns.length > 0){
            this.header = this.view.createHeader(this.setting, this.table);
            this._mergeColumn(this.setting.columns);
            this.view.createHeaderItem(this.setting, this.header);
        }
        
        //创建tbody
        this.body = this.view.createBody(this.setting, this.table);
        this.query = {
            pageNumber  : this.setting.pageNumber || 1,
            pageSize : this.setting.pageSize || 50,
            search   : this.setting.search   || '',
            sortField: this.setting.sortField || '',
            sortMode : this.setting.sortMode || 'desc'
        }
        if(this.setting.style){
            this.table[0].style.cssText += this.setting.style;
        }
        this.query = $.extend(this.query, this.setting.query);
        this.table.appendTo(this.$wrap);

        
        this.$wrap.appendTo(this.setting.renderTo ? $(this.setting.renderTo) : $('body'));
        //如果固定表头
        if(this.setting.fixedHeader){
            this.createFixedHeader();
        }
        this.callEvent('onInit');
        if(this.setting.data && $.isArray(this.setting.data)){
            this.staticLoad(this.setting.data);
        }else{
            if(this.setting.url){
                //第一次加载数据
                //this.callEvent('onInitLoad');
                this.load(this.setting);
                //分页组件
                if(self.setting.showPage){
                    self.page = widget.create('page',{
                        renderTo: self.$wrap,
                        total: self.total,
                        index:self.pageNumber,
                        pageSize: self.pageSize,
                        onChange: function(pageNumber){
                            self.pageTo(pageNumber);
                        }
                    
                    })
                }
            }else {
                window.console&& console.log('No data and No ajax url!');
            }
        }
    },
    createFixedHeader:function(){
        if(!this.setting.fixedHeader){
            return;
        }
        var self = this;
        if(this.fixedHeader){
            this.fixedHeader.remove();
            this.fixedHeader = null;
        }
        this.fixedHeader = this.view.createFixedHeader(this.setting, this.table);
        var pos = this.setting.renderTo.position();
        var scrollLeft = this.setting.renderTo.parent().scrollLeft();
        
        if(pos.left < 0){
            pos.left += scrollLeft;
        }
        
        this.setting.renderTo.after(this.fixedHeader);
        this.fixedHeader.css({top:pos.top, left:pos.left,height:this.fixedHeader.find('thead').height()});
        this.bindFixedHeaderEvent();
        if(this.scrollTimer){
            clearInterval(this.scrollTimer);
        }

        this.scrollTimer = setInterval(function(){
            var scrollLeft = self.setting.renderTo.scrollLeft();
            if(self.fixedHeader.data('scrollLeft') === undefined){
                self.fixedHeader.data('scrollLeft',0)
            }
            
            if(scrollLeft !== self.fixedHeader.data('scrollLeft')){
                self.fixedHeader.data('scrollLeft', scrollLeft);
                setStyle();
            }
        },10)
        
        function setStyle(){

            var scrollLeft = self.setting.renderTo.scrollLeft();
            self.fixedHeader.css('left', -scrollLeft);
            /*var scrollLeft = self.setting.renderTo.scrollLeft();
            self.setting.renderTo.scrollLeft(scrollLeft+toggleNum(1));*/

        }
    },
    _mergeColumn:function(columns){
        columns = columns || [];
        tool.eachData(columns, function(d, i){
            tool.merge(d, defaultColumn);
        })
    },
    /*获取配置项的值*/
    getSettingVal:function(key){
        if(!key) return null;
        return this.setting[key];
    },
    /*
        获取表头的配置项
        @param name 表头项的name值
        @param name
     */
    getColumnByName:function(name){
        if(!name) return null;
        return this.getColumnBykv('name', name);
    },
    /*
         检索表头字段,如果某一项的key值等于val,则返回
     */
    getColumnBykv:function(key, val){
        if(!key || !val) return null;
        return tool.eachData(this.setting.columns, function(d, i){
            if(d[key] === val){
                return d;
            }
        }) || null;
    },
    //设置表头字段的值
    setColumn:function(name, key, val){
        var item;
        if(!name || !key || !val) return false;
        item = this.getColumnByName(name);
        if(item) {
            item[key] = val;
        }
    },
    setSort:function(info){
        
        var target = info.element;
        var sortName = target.getAttribute('data-name');
        var sortCode = target.getAttribute('data-sortCode');
        var sortData = this.getColumnByName(sortName);
        tool.eachData(this.setting.columns, function(d, i){
            $(d.element).removeClass('active').removeClass('asc').removeClass('desc');
            d.curr = false;
        });
        var oldSortVal = this.query.sortMode;
        var newSortVal = oldSortVal === 'asc' ? 'desc' : 'asc';
        sortData.sortMode = newSortVal;
//            this.query.sortField = sortName;
        this.query.sortField = sortCode;
        this.query.sortMode = newSortVal
        $(sortData.element).addClass('active').addClass(newSortVal);
        if(this.setting.clientSort){
//              this.sortData(sortName, newSortVal, this.cache);
            this.sortData(sortCode, newSortVal, this.cache);
            this.refresh();
        }else{
            this.reload();
        }
    },
    _translateData:function(data){
        var i=0,j=0, n=0,data = data || [],len=data.length, clen, cache=[], cacheLen = data.length;

        //转换数据结构
        for(;i<len;++i){
            var d = data[i];
            d.itemIndex = (i+1);
            var cacheData = tool.translateData(d);
            cache.push(cacheData);
        };


        if(this.setting.showPage){
            this.cache = [];
            this.cache = cache;
            this.body.html("");
        }else{
            var tmp = this.cache;
            this.cache = tmp.concat(cache);
        }
        

        //生成列表element对象
        for(clen=cache.length;j<clen;j++){
            var item = cache[j];
            item.element = this.view.createList(this.setting, item, this.body, j);
            this.body.append(item.element);
        }
        if(this.setting.afterRender){
            this.setting.afterRender();
        }
    },
    //更新某条数据
    /*
     * @param {
     * 
     *    key :val 
     *    
     * }
     * key 根据传入的某个属性来更新
     * val key的值
     * 
     * */
    updateDataByKey:function(kv){
        var key, val, data = kv || {},cache = this.cache, self = this;
        for (key in data){
            val = data[key];
            break;
        }

        for(var i=0;i<cache.length;i++){
            var d = cache[i].data;
            var element = cache[i].element;
            if(d[key] === val){
                (function(i, d, element){
                    //如果有用户配置的获取单条数据的代理处理方法则执行，否则暂时什么都不做
                    if(self.updateDataByIdHandle){
                        self.updateDataByIdHandle(kv).done(function(data){
                            data.itemIndex = d.itemIndex;
                            cache[i].data = data;
                            var ele =  self.view.createList(self.setting, cache[i]);
                            var classes = element.attr('class');
                            ele.addClass(classes);
                            element[0].parentNode.replaceChild(ele[0], element[0]);
                            cache[i].element = ele;
                        })
                    }
                    
                })(i, d, element)
                return;
            }
            
        }
    },
  
    getArrayByKey:function(key){
        var res = [], item;
        for(var i=0;i<this.cache.length;i++){
            item = this.cache[i].data;
            res.push(item[key]);
        }
        return  res;
    },
    getSelectedArrayByKey:function(key){
        var res = [], item;
        for(var i=0;i<this.cache.length;i++){
            item = this.cache[i];
            if(item.selected){
                res.push(item.data[key]);
            }
        }
        return  res;
    },
    
    
    renderList:function(cache){
        var n=0,len = cache.length, tableFragment = document.createElement('table');
        for(;n<len;n++){
            this.body.append(cache[n].element);
        }
        tableFragment = null;
    },
    refresh : function(){
        this.body.html('');
        this.renderList(this.cache);
    },
    clearData:function(){
        this.cache = [];
        this.body.html('');
    },
    //通过参数传入的数据，直接渲染
    staticLoad:function(data){
        var list = data, self = this;
        
        self.total = data.length;
        if(this.setting.filter){
            list = this.setting.filter(list);
        }
        self._translateData(list);
        //重新生成固定表头，防止这次的数据早上旧的表头宽度改变
        if(self.setting.fixedHeader){
            self.createFixedHeader();
        }
        
        self.callEvent('onLoaded', {code:0,msg:''});
        
        //全部加载完成
        if(self.isComplete()){
            self.callEvent('onComplete',  {code:0,msg:''});
        }
        
        //空列表
        if(self.isEmpty()){
            self.callEvent('onEmpty',  {code:0,msg:''});
            self.renderEmpty();
        }
    },
    renderEmpty: function(){
        this.body.html('<tr><td style="text-align:center;" colspan="'+this.setting.columns.length + (this.setting.selectable ? 1 : 0) +'">'+this.setting.emptyMsg+'</td></tr>')
    },
    load : function(setting, type){
        this.completed = false;
        this.callEvent('onStartLoad');
        var self = this;
        if(this.setting.queryFunction){
            var query = this.setting.queryFunction();
            query = $.extend(this.query,query);
        }else{
            var query = this.query;
        }
        
        
        widgetLoading.show();
        $.ajax({
            url : setting.url,
            data : query,
            type : 'get',
            cache:false,
            success : function(data){
                widgetLoading.hide();
                if(data && data[setting.codeKey] == '0000'){
                    if(type && type == 'reload'){
                        self.clearData();
                    }
                    
                    var source = data[setting.sourceKey];
                    //setting.compluteTotal && source.total && (self.total = source.total);
                    source.total && (self.total = source.total);
                    source.pageNumber && (self.pageNumber = self.query.pageNumber = source.pageNumber);
                    source.pageSize   && (self.pageSize = self.query.pageSize = source.pageSize);

                    
                    
                    //列表数据
                    var list = source[setting.listKey];
                    var len = list && list.length;
                    
                    if(list && list.length){
                        if(setting.filter){
                            list = setting.filter(list);
                        }
                        self._translateData(list);
                        //重新生成固定表头，防止这次的数据早上旧的表头宽度改变
                        if(self.setting.fixedHeader){
                            setTimeout(function(){
                                self.createFixedHeader();
                            },10)
                            
                        }
                    }
                    //ajax请求完成 
                    self.callEvent('onLoaded', data);
                    
                    
                    
                    //不用total做分页判断依据
                    if(self.total < 0){
                        //全部加载完
                        if(len < self.query.pageSize){
                            self.completed = true;
                            self.callEvent('onComplete', data);
                        }
                        
                    }else{
                        
                        //全部加载完成
                        if(setting.compluteTotal && self.isComplete()){
                            self.completed = true;
                            self.callEvent('onComplete', data);
                        }
                    }
                    
                    //空列表
                    if(self.isEmpty()){
                        self.callEvent('onEmpty', data);
                        self.renderEmpty();
                    }
                    
                    if(!self.initloaded){
                        self.callEvent('onInitLoad', data);
                        self.initLoaded = true;
                   }else{
                        
                   }

                   if(self.page){
                        self.page.setData(self.total, self.pageNumber, self.pageSize);
                    }
                   
                }else{
                    self.callEvent('onError', data);
                }
            },
            error:function(){
                widgetLoading.hide();
                self.callEvent('onError')
            }
        })
    },
    isEmpty:function(){
        return (this.query.pageNumber == 1) && (this.cache.length==0);
    },
    callEvent:function(name, data){
        var callback = this.event[name];
        if($.isFunction(callback)){
            callback(data);
        }else if($.isArray(callback)){
            for(var i=0;i<callback.length;i++){
                if($.isFunction(callback[i])){
                    callback[i](data);
                }
            }
        }
    },
    //获取已加载的数据条数
    getDataNumber:function(){
        return this.cache.length;
    },
    reStart : function(){
        this.query.page = 1;
        this.load(this.setting);
    },
    getTotalPage:function(){
        var totalPage = Math.ceil(this.total/this.query.pageSize);
        return totalPage;
    },
    isComplete:function(){
        var totalPage = this.getTotalPage();
        if(totalPage == this.query.pageNumber){
            return true;
        }else{
            return false;
        }
    },
    pageTo : function(page){
        this.query.pageNumber = page;
        this.load(this.setting);
    },
    nextPage : function(){
        
        if(this.completed !== true){
            this.query.pageNumber ++;
            this.pageTo(this.query.pageNumber)
        }
    },
    prePage : function(){
        if(this.query.pageNumber > 1){
            this.query.pageNumber --;
            this.pageTo(this.query.pageNumber);
        }
    },
    getElement:function(){
        return this.$wrap;
    },
    sortData:function(key, type){
        var d=this.cache, self = this;
        var dataType = self.getColumnByName(key).dataType || 'string';
        d.sort(function(a,b){
            if(dataType === 'number'){
                return type === 'asc' ? (a.data[key] - b.data[key] ):(b.data[key] - a.data[key]);
            }else if(dataType === 'string'){
                return type === 'asc' ? ( a.data[key].localeCompare(b.data[key])) : (b.data[key].localeCompare(a.data[key]));
            }else if(dataType === 'date'){

                var x = Date.parse( a.data[key]);
                var y = Date.parse( b.data[key]);
                
                if ( isNaN(x) || x==="" )
                {
                x = Date.parse( "01/01/1970 00:00:00" );
                }
                if ( isNaN(y) || y==="" )
                {
                    y = Date.parse( "01/01/1970 00:00:00" );
                }
                return type === 'asc' ? (x - y) : (y-x);
            }
        })
    },
    getDataByElement:function(element){

        return eachData(this.data, function(data, i){
            if(data.element === element){
                return data;
            }
        }, this) || null;
    },
    selectByElement:function(ele){

        tool.eachData(this.data, function(data, i){
            if(data.element === ele){
                if(data.selected){
                    data.selected = false;
                    ele.classList.remove('selected');
                    ele.getElementsByTagName('input')[0].checked = false;
                }else {
                    data.selected = true;
                    ele.classList.add('selected');
                    ele.getElementsByTagName('input')[0].checked = true;
                }
            }
        }, this)
        this._onSelectedChange();
        return null;
    },
    _onSelectedChange:function(){
        var allSelectedBtn = this.table.find('.'+this.setting.allSelectInputClass);
        var isSelectedAll = true;
        tool.eachData(this.cache, function(item, i){
            if(!item.selected){
                isSelectedAll = false;
                return;
            }
        }, this);
        
        if(!this.cache.length && allSelectedBtn.attr('checked')){
            isSelectedAll = false;
        }
        
        
        
        if(!isSelectedAll){
             allSelectedBtn.removeAttr('checked');
             if(this.setting.fixedHeader){
                this.fixedHeader.find('.'+this.setting.allSelectInputClass).removeAttr('checked');
             }
             

        }else{
             
             allSelectedBtn.attr('checked', 'checked');
             if(this.setting.fixedHeader){
                this.fixedHeader.find('.'+this.setting.allSelectInputClass).attr('checked', 'checked');
              }
        }
        this.callEvent('onSelectedChange');
    },
    selectedAll:function(){
        var self = this;
        tool.eachData(this.cache, function(item, i){
            
            if(!item.selected){
                item.selected = true;
                if(this.setting.selectable){
                    var ele = item.element;
                    ele.addClass('active');
                    if(item.data.claimed){
                        if(item.data.claimed == 'y' || item.data.claimed == 'n'){
                            ele.find('.checkbox,.select_input')[0].checked = true;
                        }else{
                            ele.find('.checkbox,.select_input')[0].checked = false;
                        }
                    }else{
                        ele.find('.checkbox,.select_input')[0].checked = true;
                    }
                    
                    
                }
            }
        }, this)
        this._onSelectedChange();
    },
    unSelectedAll:function(){
        tool.eachData(this.cache, function(item, i){
            if(item.selected){
                item.selected = false;
                if(this.setting.selectable){
                    var ele = item.element;
                    ele.removeClass('active');
                    ele.find('.checkbox,.select_input')[0].checked = false;
                }
            }
        }, this)
        this._onSelectedChange();
    },
    selectedByElement:function(element){
        tool.eachData(this.cache, function(item, i){
            
            var ele = item.element;
            if(ele[0] === element){
                item.selected = !item.selected;
                if(ele.hasClass('active')){
                    ele.removeClass('active');
                }else{
                    ele.addClass('active');
                }
                return false;
            }
            
        })
        this._onSelectedChange();
    },
    getSelected:function(allData=false){
         var res = [];
         tool.eachData(this.cache, function(item,i){
            if(item.selected){ 
                res.push(allData ? item : item.data)
            };
         }, this);
         return res;
    },
    reload : function(option){
        this.header.find(".allSelect").removeAttr("checked");
        this.unSelectedAll();
        this.query.pageNumber = 1;
        if(option && option.pageSize){
            this.setting.pageSize = option.pageSize;
            this.query.pageSize = option.pageSize;
        }
        this.load(this.setting, 'reload');
        this.callEvent('onReload')
    },
    search : function(key){
        if(!this.query.search || this.query.search != key){
            this.query.search = key;
            this.query.pageNumber = 1;
        }
        this.reload();
    },
    //根据uid删除一条
    removeDataByuid:function(uid){
        var self = this;
        tool.eachData(this.cache, function(item, index){
            if(item.uuid == uid){
                item.element.remove();
                self.cache.splice(index,1);
                self.callEvent('onRmoveData');
                return true;
            }
        })
    },
    
    //根据id删除一条
    removeDataByid:function(id){
        var self = this;

        tool.eachData(self.cache, function(item, index){
            if(item.data.id == id){
                item.element.remove();
                self.cache.splice(index,1);
                self.callEvent('onRmoveData');
                return true;
            }
        })
        
    },
    //根据uid获取一条数据
    getDataByuid:function(uid){
        var self = this;
        return tool.eachData(this.cache, function(item, index){
            if(item.uuid == uid){
                return item.data;
            }
        }) || null;
    },
    getDataByIndex:function(index){
        return this.data[index];
    },
    //获取全部数据
    getData:function(allData=false){
        var res = [];
        for(var i=0;i<this.cache.length;i++){
            res.push(allData ? this.cache[i] : this.cache[i].data);
        }
        return res;
    },
    removeFixedHeader:function(){
        this.fixedHeader && this.fixedHeader.remove();
    },
    bindFixedHeaderEvent:function(){
        var self = this;
        this.fixedHeader.bind('click', function(e){
            var info = self.event._proxy(e, self.setting.renderTo[0]);
            if(info.nodeType && info.element){
                self.handle(e, info);
            }
        });
        
        if(this.setting.dragResize){
            this.fixedHeader.find('.hd-resize-bar').click(function(e){
                e.stopPropagation();
            })
            this.fixedHeader.find('.hd-resize-bar').bind('mousedown.dragResize', function(e){
                e.stopPropagation();
                var fixedTh = self.fixedHeader.find('th');
                var th = self.header.find('th');
                var target = $(this).parents('th');
                var currWidth = target.width();
                var index = target.index();
                var currX = e.clientX;
                $(document).bind('mousemove.dragResize', function(e){
                    var disX = e.clientX - currX;
                    var newTwidth = currWidth + disX;
                    
                    self.header.find('th').eq(index).width(newTwidth);
                    fixedTh.each(function(index, item){
                        
                        fixedTh.eq(index).width(th.eq(index)[0].scrollWidth)
                    })
                    //target.width(self.header.find('th').eq(index).width());
                    return false;
                    
                })
                $(document).bind('mouseup.dragResize', function(e){
                    $(document).unbind('mousemove.dragResize').unbind('mouseup.dragResize')
                })
                return false;
            })
        }
    },
    dragResize:function(){
        
    },
    listenResize:function(){
        var self = this;
        this.timer = setInterval(function(){
            
            if(self.isDragResize){
                return;
            }
            
            var w = self.table.data('w'), nowWidth = self.table[0].offsetWidth;
            
            if(!w){
                self.table.data('w', nowWidth);
            }else{
                if(w !== nowWidth){
                    self.table.data('w', nowWidth);
                    self.createFixedHeader();
                    self.fire('resize');
                }
            }
        }, this.setting.interVal || 20)
    },
    stopListenResize:function(){
        this.timer && clearInterval(this.timer);
    },
    bindEvent:function(){
        var self = this;

        this.setting.renderTo.bind('click.listTable', function(e){
            var info = self.event._proxy(e, self.setting.renderTo[0]);
            if(info.nodeType && info.element){
                
                self.handle(e, info);
            }
        });
        
        if(this.setting.dragResize){
            this.header.find('.hd-resize-bar').click(function(e){
                e.stopPropagation();
            })
            this.header.find('.hd-resize-bar').bind('mousedown.dragResize', function(e){
                self.isDragResize = true;
                e.stopPropagation();
                var target = $(this).parents('th');
                var currWidth = target.width();
                var index = target.index();
                var currX = e.clientX;
                $(document).bind('mousemove.dragResize', function(e){
                    var disX = e.clientX - currX;
                    var newTwidth = currWidth + disX;
                    target.width(newTwidth);
                    return false;
                    
                })
                $(document).bind('mouseup.dragResize', function(e){
                    self.isDragResize = false;
                    $(document).unbind('mousemove.dragResize').unbind('mouseup.dragResize')
                })
                return false;
            })
        }
        
        
    },
    handle:function(e, info){
        switch(info.nodeType){
            //点击列表项
            case 'item' :
                break;
            //点击排序
            case 'sort':
                this.setSort(info);
                break;
            //选中数据
            case 'selectInput' :
                var box = $(info.element).parents('.list-item');
                if(!box[0]){
                    box = $(info.element).parents('.list_item');
                }
                this.selectedByElement(box[0]);
                break;
            //全选按钮
            case 'allSelect':
                var checked = info.element.checked;
                
                if(checked){
                    this.selectedAll();
                }else{
                    
                    this.unSelectedAll();
                }
                break;
        }
    },
    destroy:function(){
        this.header.find('.hd-resize-bar').unbind();
        this.fixedHeadedr && this.fixedHeadedr.find('.hd-resize-bar').unbind();
        $(document).unbind('mousemove.dragResize').unbind('mouseup.dragResize')
        this.table.unbind();
        this.cache = [];
        this.stopListenResize();
        this.removeFixedHeader();
        this.table.remove();
        this.callEvent('onDestroy');
    }
})

widget.Message = {
    success: function(message){
        var msg = widget.create('message',{});
        msg.show('success', message);
    },
    warning: function(message){
        var msg = widget.create('message',{});
        msg.show('warning', message);
    },
    danger: function(message){
        var msg = widget.create('message',{});
        msg.show('danger', message);
    },
    info: function(message){
        var msg = widget.create('message',{});
        msg.show('info', message);
    }
}

window.gWidget = widget;
export default widget;