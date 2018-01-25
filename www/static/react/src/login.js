import React from 'react';
import ReactDOM from 'react-dom';
import store from './store/store';
import {Provider} from 'react-redux';
import Login from './components/Login';



ReactDOM.render((
	<Login />
), document.querySelector('#login'))