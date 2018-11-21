import { createStore, applyMiddleware, compose } from 'redux';
import thunkMiddleware from 'redux-thunk';

import DevTools from '../components/dev-tools';
import { initialState, rootReducer } from '../reducers/root';

export default function configureStore() {
  const store = createStore(
    rootReducer,
    initialState,
    compose(
      // applyMiddleware(thunkMiddleware, createLogger()),
      //因为你的applyMiddleware可以存在异步行为，为了确保所有的actions显示在store中，所以要放在后面
      applyMiddleware(thunkMiddleware),
      //必须的！启用带有monitors（监视显示）的DevTools
      DevTools.instrument()//通过redux的compose来扩展store
    )
  );

  if (module.hot) {
    // Enable Webpack hot module replacement for reducers
    module.hot.accept('../reducers/root', () => {
      const nextRootReducer = require('../reducers/root').default;
      store.replaceReducer(nextRootReducer);
    });
  }

  return store;
}
