/*
    时间间隔队列, 以一定的时间间隔根据队列中的数据执行某种操作， 避免某种操作太过频繁
*/

import Queue from './queue';

function TimerQueue(option) {
    option = option || {};
    this.queue = new Queue();
    this.timer = null;
    this.isStarted = false;
    this.interval = option.interval || 300;
    this.onExecute = option.onExecute || function(){};
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

export default TimerQueue;