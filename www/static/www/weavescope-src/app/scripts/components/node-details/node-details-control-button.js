import React from 'react';
import { connect } from 'react-redux';

import { doControl } from '../../actions/app-actions';

class NodeDetailsControlButton extends React.Component {
  constructor(props, context) {
    super(props, context);
    this.handleClick = this.handleClick.bind(this);
  }

  render() {
    let className = `node-control-button fa ${this.props.control.icon}`;
    if (this.props.pending) {
      className += ' node-control-button-pending';
    }
    return (
      <span className={className} title={this.props.control.human} onClick={this.handleClick} />
    );
  }

  handleClick(ev) {
    ev.preventDefault();
    this.props.dispatch(doControl(this.props.nodeId, this.props.control));
  }
}

// Using this instead of PureComponent because of props.dispatch
export default connect()(NodeDetailsControlButton);
