(function(){

var utils = window.utils || {};

/*
空函数
*/
utils.noop = function(){}

/*
    队列结构
*/

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
utils.Queue = Queue;


/*
    时间间隔队列, 以一定的时间间隔根据队列中的数据执行某种操作， 避免某种操作太过频繁
*/
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
utils.TimerQueue = TimerQueue;


/*
    对外抛出变量　
*/
window.utils = utils;
})();
