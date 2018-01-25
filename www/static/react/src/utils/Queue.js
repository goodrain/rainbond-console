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

export default Queue;