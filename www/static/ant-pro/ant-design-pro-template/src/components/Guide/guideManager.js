import React, {PureComponent, Fragment} from 'react';
import tasks from './tasks';


class GuideManager extends PureComponent {
    constructor(props){
        super(props);
        this.state = {
            group:0,
            task:0,
            show: true
        }
    }
    componentWillMount(){
        try{
            var task =  localStorage.getItem('goodrain_task');
            if(task){
                task = JSON.parse(task);
                this.setState({group: task.group, task: task.task})
            }else{
                this.setState({group:0, task:0})
            }
        }catch(e){

        }
        
    }
    componentDidMount(){

    }
    getNextTask = () => {
        var group = this.state.group;
        var task = this.state.task;
        var nextGroup = group+1;
        var nextTask = task+1;
        if(tasks['group'+group+'task'+nextTask]){
            return {
                group: group,
                task: nextTask
            }
        }

        if(tasks['group'+nextGroup+'task'+0]){
             return {
                 group: nextGroup,
                 task: 0
             }
        }
        return null;
    }
    next = () => {
        var next = this.getNextTask();
        if(next){
            this.setState({group:next.group, task: next.task});
        }else{
            this.stop();
        }
    }
    stop = () => {
        this.setState({show: false})
    }
    render(){
        var group = this.state.group;
        var task  = this.state.task;
        var show = this.state.show;
        var Com = tasks['group'+group+'task'+task];
        if(!show || !Com){
            return null;
        }
        return (
            <Com manager={this} />
        )
    }
}
export default GuideManager;