// capability_id: console.topology.polling-lifecycle
const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const output = path.resolve(root, '../weavescope-topolog');
const index = fs.readFileSync(path.join(output, 'index.html'), 'utf8');
const entry = index.match(/src="(app-polling-[a-z0-9]+\.js)"/)[1];
const asset = fs.readFileSync(path.join(output, entry), 'utf8');
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const bean = status => ({ code: 200, data: { bean: {
  json_data: { one: { service_id: 'one', service_alias: 'one', service_cname: 'one', cur_status: status } }, json_svg: { one: [] }
} } });

function fixture() {
  let now = 0; let nextTimer = 0; let url = '/fixture/app-a'; let scope = '["team","region","a"]';
  const timers = new Map(); const requests = []; const actions = [];
  const listeners = {};
  const parent = { iframeGetNodeUrl: () => url, iframeGetTopologyScope: () => scope };
  const window = { parent, location: { origin: 'http://fixture' },
    addEventListener: (name, listener) => { listeners[name] = listener; },
    removeEventListener: name => { delete listeners[name]; } };
  const document = { cookie: '', hidden: false,
    addEventListener: (name, listener) => { listeners[name] = listener; },
    removeEventListener: name => { delete listeners[name]; } };
  let factories;
  const context = vm.createContext({ window, parent, document, process: { env: {} }, console,
    setTimeout: (fn, delay) => { timers.set(++nextTimer, { fn, at: now + delay }); return nextTimer; },
    clearTimeout: id => timers.delete(id), webpackJsonp: (ids, modules) => { factories = modules; } });
  vm.runInContext(asset, context);
  const dependencies = {
    47: () => () => {}, 11: { List: { isList: () => false }, Map: () => ({}) },
    1665: (opts, defaults) => Object.assign({}, defaults, opts),
    1824: options => { const request = { options, aborted: false, at: now }; requests.push(request);
      return { abort() { request.aborted = true; } }; },
    25: { receiveNodesDelta: delta => ({ type: 'DELTA', delta }), receiveError: failedUrl => ({ type: 'ERROR', url: failedUrl }) },
    198: {}, 421: {}
  };
  const exports = {}; factories[426]({ exports }, exports, id => {
    assert.ok(Object.hasOwn(dependencies, id), `Unexpected dependency ${id}`); return dependencies[id];
  });
  function tick(ms) {
    const end = now + ms;
    while (true) {
      const first = [...timers.entries()].sort((a, b) => a[1].at - b[1].at)[0];
      if (!first || first[1].at > end) break;
      now = first[1].at; timers.delete(first[0]); first[1].fn();
    }
    now = end;
  }
  const start = () => exports.getNodesDelta('/legacy', null, action => actions.push(action));
  const message = data => listeners.message({ source: parent, origin: 'http://fixture', data });
  return { factories, exports, start, requests, actions, tick, timers, listeners, window, parent, document, message,
    setScope(next) { url = `/fixture/app-${next}`; scope = JSON.stringify(['team', 'region', next]); },
    get scope() { return scope; } };
}

test('actual index loads content-hashed source-correlated factory; all other modules are byte-identical', () => {
  assert.equal(entry, `app-polling-${sha(asset).slice(0, 20)}.js`);
  for (const [name, marker] of [['web-api-utils.js', 'topology-source'], ['topology-polling.js', 'topology-helper']]) {
    const digest = sha(fs.readFileSync(path.join(root, 'app/scripts/utils', name)));
    assert.ok(asset.includes(`${marker}-sha256: ${digest}`), `${name} is stale`);
  }
  let old;
  vm.runInNewContext(fs.readFileSync(path.join(output, 'app-95196a50339e0f8f1469.js'), 'utf8'), { webpackJsonp: (ids, modules) => { old = modules; } });
  const current = fixture().factories;
  assert.equal(old.length, current.length);
  old.forEach((factory, i) => { if (i !== 426) assert.equal(String(factory), String(current[i]), `Unrelated module ${i} changed`); });
});

test('compiled production entry is single-flight at 15s stable and 5s transition, no duplicate route chains', () => {
  const f = fixture(); for (let i = 0; i < 6; i += 1) f.start();
  assert.equal(f.requests.length, 1); assert.equal(f.requests[0].options.timeout, 12000);
  for (let i = 0; i < 4; i += 1) { f.requests.at(-1).options.success(bean('running')); f.tick(15000); }
  assert.equal(f.requests.length - 1, 4);
  f.requests.at(-1).options.success(bean('Unknown')); f.tick(5000); assert.equal(f.requests.length, 6);
  f.exports.stopPolling(); assert.equal(f.timers.size, 0);
});

test('actual visibility/bridge handlers validate source, origin and scope; resume and coalesce', () => {
  const f = fixture(); f.start(); const first = f.requests[0];
  for (const event of [{ source: {}, origin: 'http://fixture', data: { type: 'rainbond:topology-refresh', scope: f.scope } },
    { source: f.parent, origin: 'https://wrong', data: { type: 'rainbond:topology-refresh', scope: f.scope } },
    { source: f.parent, origin: 'http://fixture', data: { type: 'rainbond:topology-refresh', scope: 'wrong' } }]) f.listeners.message(event);
  first.options.success(bean('running')); assert.equal(f.requests.length, 1);
  f.message({ type: 'rainbond:topology-refresh', scope: f.scope }); assert.equal(f.requests.length, 2);
  f.message({ type: 'rainbond:topology-refresh', scope: f.scope });
  f.message({ type: 'rainbond:topology-refresh', scope: f.scope });
  f.requests[1].options.success(bean('running')); assert.equal(f.requests.length, 3);
  f.document.hidden = true; f.listeners.visibilitychange();
  assert.equal(f.requests[2].aborted, true); f.requests[2].options.success(bean('running')); f.tick(60000);
  assert.equal(f.requests.length, 3);
  f.document.hidden = false; f.listeners.visibilitychange(); assert.equal(f.requests.length, 4);
  f.message({ type: 'rainbond:topology-stop', scope: f.scope });
  assert.equal(f.listeners.message, undefined); assert.equal(f.listeners.visibilitychange, undefined);
  f.requests[3].options.error({}); f.tick(120000); assert.equal(f.requests.length, 4);
  f.start(); assert.equal(f.requests.length, 5, 'stop then re-entry restarts immediately');
});

test('compiled business failures preserve graph, timeout aborts, identity changes discard late callbacks', () => {
  const f = fixture(); f.start(); f.requests[0].options.success(bean('running'));
  const applied = f.actions.filter(action => action.type === 'DELTA').length;
  f.tick(15000); f.requests[1].options.success({ code: 500 });
  assert.equal(f.actions.filter(action => action.type === 'DELTA').length, applied);
  f.tick(10000); f.tick(12000); assert.equal(f.requests[2].aborted, true);
  f.requests[2].options.success(bean('closed'));
  assert.equal(f.actions.filter(action => action.type === 'DELTA').length, applied);
  f.tick(20000); f.setScope('b'); f.start();
  assert.equal(f.requests[3].aborted, true); assert.equal(f.requests[4].options.url, '/fixture/app-b');
  f.requests[3].options.success(bean('closed'));
  assert.equal(f.actions.filter(action => action.type === 'DELTA').length, applied);
  f.exports.stopPolling();
});

test('a valid empty application removes previous nodes and can populate again', () => {
  const f = fixture(); f.start(); f.requests[0].options.success(bean('running')); f.tick(15000);
  f.requests[1].options.success({ code: 200, data: { bean: { json_data: {}, json_svg: {} } } });
  assert.deepEqual(Array.from(f.actions.filter(action => action.type === 'DELTA').at(-1).delta.remove), ['one']);
  f.tick(15000); f.requests[2].options.success(bean('running'));
  assert.equal(f.actions.filter(action => action.type === 'DELTA').at(-1).delta.add.length, 1);
  f.exports.stopPolling();
});

test('real operation message grants three bounded 5s follow-ups while async backend status remains stable', () => {
  const f = fixture(); f.start(); f.requests[0].options.success(bean('running'));
  f.message({ type: 'rainbond:topology-refresh', scope: f.scope }); assert.equal(f.requests.length, 2);
  for (let i = 0; i < 3; i += 1) {
    f.requests.at(-1).options.success(bean(i % 2 ? 'closed' : 'running'));
    const count = f.requests.length; f.tick(4999); assert.equal(f.requests.length, count); f.tick(1);
    assert.equal(f.requests.length, count + 1);
  }
  f.requests.at(-1).options.success(bean('running'));
  const count = f.requests.length; f.tick(14999); assert.equal(f.requests.length, count); f.tick(1);
  assert.equal(f.requests.length, count + 1);
  f.exports.stopPolling();
});

test('compiled queued operation refresh cannot bypass failure backoff and identity changes reset grace', () => {
  const f = fixture(); f.start();
  f.message({ type: 'rainbond:topology-refresh', scope: f.scope });
  f.message({ type: 'rainbond:topology-refresh', scope: f.scope });
  f.requests[0].options.success({ code: 503 });
  assert.equal(f.requests.length, 1); f.tick(9999); assert.equal(f.requests.length, 1);
  f.tick(1); assert.equal(f.requests.length, 2);
  f.setScope('b'); f.start(); f.requests.at(-1).options.success(bean('running'));
  const count = f.requests.length; f.tick(14999); assert.equal(f.requests.length, count); f.tick(1);
  assert.equal(f.requests.length, count + 1); f.exports.stopPolling();
});
