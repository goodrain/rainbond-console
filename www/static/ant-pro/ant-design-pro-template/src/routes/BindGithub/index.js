import React, {PureComponent} from 'react';
import { connect } from 'dva';
import { routerRedux } from 'dva/router';
@connect()
export default class CreateCheck extends PureComponent {
     constructor(props){
     }

     componentWillMount(){
          var params = this.props.match.params;
          this.props.dispatch({
              type:'global/bindGithub',
              payload: {
                  code: params.code,
                  state: params.state
              },
              callback: () => {
                  this.props.dispatch(routerRedux.replace("/create/code/github"))
              }
          })
     }
     render(){
       return null;
     }
}