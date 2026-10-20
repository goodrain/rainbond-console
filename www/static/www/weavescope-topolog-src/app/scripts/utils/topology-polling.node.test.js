// capability_id: console.topology.polling-lifecycle
const assert = require('node:assert/strict');
const test = require('node:test');
const { createTopologyPolling, inspectTopologyResponse } = require('./topology-polling');

function fixture() {
  let now = 0;
  let scope = 'app-a';
  let visible = true;
  let nextId = 0;
  const timers = new Map();
  const requests = [];
  const applied = [];
  const errors = [];
  const polling = createTopologyPolling({
    getScope: () => scope,
    isVisible: () => visible,
    setTimer: (fn, delay) => { timers.set(++nextId, { fn, at: now + delay }); return nextId; },
    clearTimer: id => timers.delete(id),
    request: (identity, success, failure) => {
      const item = { identity, success, failure, aborted: false, at: now };
      requests.push(item);
      return { abort() { item.aborted = true; } };
    },
    apply: response => applied.push(response),
    onError: error => errors.push(error)
  });
  function tick(ms) {
    const end = now + ms;
    while (true) {
      const first = [...timers.entries()].sort((a, b) => a[1].at - b[1].at)[0];
      if (!first || first[1].at > end) break;
      now = first[1].at;
      timers.delete(first[0]);
      first[1].fn();
    }
    now = end;
  }
  return { polling, requests, applied, errors, timers, tick,
    setScope(value) { scope = value; },
    setVisible(value) { visible = value; polling.visibilityChanged(); } };
}

const response = (status = 'running') => ({ code: 200, data: { bean: {
  json_data: { one: { cur_status: status, service_id: 'one' } }, json_svg: { one: [] }
} } });

test('full payload determines stability, including unknown/operator/empty cases', () => {
  ['running', 'closed', 'third_party', 'stopped'].forEach(status => assert.equal(inspectTopologyResponse(response(status)).stable, true));
  ['starting', 'building', 'Unknown', 'unKnow', '', 'operator'].forEach(status => assert.equal(inspectTopologyResponse(response(status)).stable, false));
  assert.equal(inspectTopologyResponse({ code: 200, data: { bean: { json_data: {}, json_svg: {} } } }).stable, true);
  [null, {}, { code: 500 }, { code: 200, data: { bean: {} } }, { code: 200, data: { bean: { json_data: [], json_svg: {} } } }].forEach(value => assert.equal(inspectTopologyResponse(value).valid, false));
  const mixed = response(); mixed.data.bean.json_data.two = { cur_status: 'starting' };
  assert.equal(inspectTopologyResponse(mixed).stable, false);
});

test('stable minute has exactly four follow-ups; transition remains five seconds', () => {
  const f = fixture(); f.polling.start();
  assert.equal(f.requests.length, 1);
  for (let i = 0; i < 4; i += 1) { f.requests.at(-1).success(response()); f.tick(15000); }
  assert.equal(f.requests.length - 1, 4);
  f.requests.at(-1).success(response('starting')); f.tick(4999);
  assert.equal(f.requests.length, 5); f.tick(1); assert.equal(f.requests.length, 6);
});

test('refresh coalesces while in-flight and never forks a timer chain', () => {
  const f = fixture(); f.polling.start();
  f.polling.start(); f.polling.refresh(); f.polling.refresh();
  assert.equal(f.requests.length, 1);
  f.requests[0].success(response());
  assert.equal(f.requests.length, 2);
  f.requests[1].success(response()); f.tick(15000);
  assert.equal(f.requests.length, 3);
  assert.equal(f.timers.size, 1, 'only the active request timeout exists');
});

test('hidden pauses, aborts and rejects late results; resume reads immediately', () => {
  const f = fixture(); f.polling.start(); f.setVisible(false);
  assert.equal(f.requests[0].aborted, true);
  f.requests[0].success(response()); f.tick(60000);
  assert.equal(f.applied.length, 0); assert.equal(f.requests.length, 1);
  assert.equal(f.timers.size, 0);
  f.polling.refresh(); f.setVisible(true); assert.equal(f.requests.length, 2);
  f.requests[1].success(response()); assert.equal(f.requests.length, 2);
});

test('failure and invalid/business payload retain graph and use bounded exponential backoff', () => {
  const f = fixture(); f.polling.start();
  for (const delay of [10000, 20000, 40000, 60000, 60000]) {
    const count = f.requests.length; f.requests.at(-1).success({ code: 503 });
    f.tick(delay - 1); assert.equal(f.requests.length, count);
    f.tick(1); assert.equal(f.requests.length, count + 1);
  }
  assert.equal(f.applied.length, 0);
  f.requests.at(-1).success(response()); f.tick(15000);
  f.requests.at(-1).failure(new Error('network')); f.tick(10000);
  assert.equal(f.requests.length, 8, 'success resets the error counter');
});

test('finite timeout aborts before retry and discards timeout callback', () => {
  const f = fixture(); f.polling.start(); f.tick(12000);
  assert.equal(f.requests[0].aborted, true); assert.equal(f.requests.length, 1);
  f.requests[0].success(response()); assert.equal(f.applied.length, 0);
  f.tick(10000); assert.equal(f.requests.length, 2);
});

test('stop and scope switch discard old success/errors without rearming', () => {
  const f = fixture(); f.polling.start();
  f.setScope('app-b'); f.polling.start();
  assert.equal(f.requests[0].aborted, true); assert.equal(f.requests[1].identity, 'app-b');
  f.requests[0].success(response()); assert.equal(f.applied.length, 0);
  f.polling.stop(); f.requests[1].failure(new Error('late')); f.tick(120000);
  assert.equal(f.requests.length, 2); assert.equal(f.errors.length, 0); assert.equal(f.timers.size, 0);
});

test('apply exceptions settle as failures rather than killing the chain', () => {
  const f = fixture(); f.polling.start();
  f.requests[0].success(response()); f.polling.stop();
  const polling = createTopologyPolling({ getScope: () => 'app', request: (s, ok) => { ok(response()); return { abort() {} }; },
    apply: () => { throw new Error('render'); }, setTimer: () => 1, clearTimer: () => {} });
  assert.doesNotThrow(() => polling.start()); polling.stop();
});

test('scope changed during a request immediately replaces transport without applying the old graph', () => {
  const f = fixture(); f.polling.start(); f.setScope('app-b');
  f.requests[0].success(response());
  assert.equal(f.applied.length, 0); assert.equal(f.requests[0].aborted, true);
  assert.equal(f.requests[1].identity, 'app-b');
  f.requests[1].success(response()); f.tick(15000); assert.equal(f.requests.length, 3);
});

test('throwing abort or error presentation cannot prevent invalidation or bounded scheduling', () => {
  let failure; let calls = 0; const delays = [];
  const polling = createTopologyPolling({ getScope: () => 'app',
    request: (scope, ok, fail) => { failure = fail; calls += 1; return { abort() { throw new Error('abort'); } }; },
    apply() {}, onError() { throw new Error('presentation'); },
    setTimer: (fn, delay) => { delays.push(delay); return 1; }, clearTimer() {} });
  polling.start(); assert.doesNotThrow(() => failure(new Error('network')));
  assert.equal(delays.at(-1), 10000); assert.doesNotThrow(() => polling.stop());
  polling.start(); assert.equal(calls, 2); assert.doesNotThrow(() => polling.stop());
});

test('explicit operation refresh gets only three fast follow-ups even when async status is still stable', () => {
  const f = fixture(); f.polling.start(); f.requests[0].success(response());
  f.polling.refresh(); assert.equal(f.requests.length, 2);
  for (let i = 0; i < 3; i += 1) {
    f.requests.at(-1).success(response(i % 2 ? 'closed' : 'running'));
    const count = f.requests.length;
    f.tick(4999); assert.equal(f.requests.length, count); f.tick(1);
    assert.equal(f.requests.length, count + 1);
  }
  f.requests.at(-1).success(response());
  const count = f.requests.length; f.tick(14999); assert.equal(f.requests.length, count);
  f.tick(1); assert.equal(f.requests.length, count + 1);
});

test('operation grace never overrides failed-request backoff, including a refresh queued in flight', () => {
  const f = fixture(); f.polling.start(); f.polling.refresh(); f.polling.refresh();
  f.requests[0].failure(new Error('network'));
  assert.equal(f.requests.length, 1, 'queued refresh must not immediately retry a failed transport');
  for (const delay of [10000, 20000, 40000, 60000]) {
    const count = f.requests.length;
    f.tick(delay - 1); assert.equal(f.requests.length, count); f.tick(1);
    assert.equal(f.requests.length, count + 1);
    if (delay < 60000) f.requests.at(-1).failure(new Error('network'));
  }
  f.requests.at(-1).success(response()); const count = f.requests.length;
  f.tick(5000); assert.equal(f.requests.length, count + 1);
});

test('scope change and stop/re-entry clear operation fast-follow-up budget', () => {
  const f = fixture(); f.polling.start(); f.requests[0].success(response()); f.polling.refresh();
  f.setScope('app-b'); f.polling.start(); f.requests.at(-1).success(response());
  const count = f.requests.length; f.tick(14999); assert.equal(f.requests.length, count); f.tick(1);
  assert.equal(f.requests.length, count + 1);
  f.polling.refresh(); f.polling.stop(); f.polling.start(); f.requests.at(-1).success(response());
  const restarted = f.requests.length; f.tick(14999); assert.equal(f.requests.length, restarted); f.tick(1);
  assert.equal(f.requests.length, restarted + 1);
});
