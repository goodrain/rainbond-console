/* A single owner for the HTTP topology polling lifecycle. No browser globals in this helper. */
function isRecord(value) {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function inspectTopologyResponse(response) {
  var bean = response && response.data && response.data.bean;
  if (!response || response.code !== 200 || !isRecord(bean) ||
      !isRecord(bean.json_data) || !isRecord(bean.json_svg)) {
    return { valid: false, stable: false };
  }
  var keys = Object.keys(bean.json_data);
  var valid = keys.every(function (key) {
    var node = bean.json_data[key];
    return isRecord(node) && typeof node.service_id === 'string' && Boolean(node.service_id);
  }) && Object.keys(bean.json_svg).every(function (key) {
    return bean.json_svg[key] === null || Array.isArray(bean.json_svg[key]);
  });
  // Operator resources do not expose a reliable desired replica count here. Poll conservatively.
  var stable = valid && keys.every(function (key) {
    var status = String(bean.json_data[key].cur_status || '').toLowerCase();
    return ['running', 'closed', 'stopped', 'third_party'].indexOf(status) !== -1;
  });
  return { valid: valid, stable: stable };
}

function getTopologyDelay(failed, failures, stable) {
  return failed ? Math.min(60000, 10000 * Math.pow(2, Math.max(0, failures - 1))) : (stable ? 15000 : 5000);
}

function createTopologyPolling(config) {
  var setTimer = config.setTimer || setTimeout;
  var clearTimer = config.clearTimer || clearTimeout;
  var isVisible = config.isVisible || function () { return true; };
  var generation = 0;
  var running = false;
  var scope = null;
  var active = null;
  var timer = null;
  var pendingRefresh = false;
  var failures = 0;
  var fastFollowups = 0;

  function clearSchedule() {
    if (timer !== null) clearTimer(timer);
    timer = null;
  }

  function invalidate() {
    generation += 1;
    clearSchedule();
    var previous = active;
    active = null;
    if (previous) {
      clearTimer(previous.timeout);
      if (previous.transport && typeof previous.transport.abort === 'function') {
        try { previous.transport.abort(); } catch (_) { /* Already invalidated; never retain a dead request lock. */ }
      }
    }
  }

  function isCurrent(request) {
    return running && active === request && request.generation === generation &&
      request.scope === scope && request.scope === config.getScope() && isVisible();
  }

  function schedule(delay) {
    clearSchedule();
    if (!running || !isVisible()) return;
    timer = setTimer(function () { timer = null; read(); }, delay);
  }

  function read() {
    if (!running || !isVisible() || active) return;
    clearSchedule();
    var identity = config.getScope();
    if (!identity) return;
    if (identity !== scope) { invalidate(); scope = identity; failures = 0; fastFollowups = 0; }
    pendingRefresh = false;
    var request = { generation: generation, scope: scope, transport: null, timeout: null };
    active = request;

    function settle(error, response, timedOut) {
      if (running && active === request && request.scope !== config.getScope()) {
        invalidate();
        scope = config.getScope();
        failures = 0;
        fastFollowups = 0;
        read();
        return;
      }
      if (!isCurrent(request)) return;
      clearTimer(request.timeout);
      active = null;
      var inspection = error ? { valid: false, stable: false } : inspectTopologyResponse(response);
      if (!inspection.valid) error = error || new Error('Invalid topology response');
      if (!error) {
        try { config.apply(response); } catch (applyError) { error = applyError; }
      }
      if (timedOut && request.transport && typeof request.transport.abort === 'function') {
        try { request.transport.abort(); } catch (_) { /* Transport is already invalidated. */ }
      }
      if (error) {
        failures += 1;
        if (config.onError) {
          try { config.onError(error, request.scope); } catch (_) { /* Presentation failures must not fork or kill polling. */ }
        }
      } else failures = 0;
      if (!running || !isVisible()) return;
      if (pendingRefresh && !error) read();
      else {
        var delay = getTopologyDelay(Boolean(error), failures, inspection.stable);
        // Accepted actions are asynchronous: a few old stable responses must not hide their transition.
        if (!error && fastFollowups > 0) { fastFollowups -= 1; delay = 5000; }
        schedule(delay);
      }
    }

    request.timeout = setTimer(function () { settle(new Error('Topology request timed out'), null, true); }, config.requestTimeout || 12000);
    try {
      request.transport = config.request(scope,
        function (response) { settle(null, response, false); },
        function (error) { settle(error || new Error('Topology request failed'), null, false); });
    } catch (error) { settle(error, null, false); }
  }

  return {
    start: function () {
      var identity = config.getScope();
      if (running && identity === scope) return;
      invalidate(); scope = identity; running = true; failures = 0; pendingRefresh = false; fastFollowups = 0;
      read();
    },
    refresh: function () {
      if (!running) return;
      if (scope !== config.getScope()) {
        invalidate(); scope = config.getScope(); failures = 0; fastFollowups = 0;
        read();
        return;
      }
      fastFollowups = 3;
      pendingRefresh = true;
      if (!active) read();
    },
    visibilityChanged: function () {
      if (!running) return;
      invalidate();
      if (isVisible()) read();
    },
    stop: function () {
      running = false; pendingRefresh = false; fastFollowups = 0; invalidate();
    }
  };
}

module.exports = { createTopologyPolling: createTopologyPolling, inspectTopologyResponse: inspectTopologyResponse };
