# Targeted topology polling build

The original `npm run build` requires the unavailable Node 6 / Webpack 2 / node-sass 4
toolchain. Do not upgrade those dependencies to make this polling-only change.

With Node 18+ and an explicitly selected Babel 7 toolchain (`@babel/core`, parser,
generator, traverse and preset-env), run:

```sh
npm run build:polling -- --toolchain /path/to/node_modules
node --test app/scripts/utils/topology-polling.node.test.js scripts/polling-asset.node.test.cjs
```

An existing Rainbond UI `node_modules` is supported (its bundled UMI preset-env is
used if standalone preset-env is absent). Nothing is installed or upgraded.

The builder checks the frozen app bundle SHA-256, uniquely identifies its
CommonJS web-api-utils module and verifies all dependency IDs. It recompiles
`web-api-utils.js` from source and inlines `topology-polling.js`, replaces only the
verified AST factory bounds, writes a content-hashed new entry and updates
`index.html`. Every other module byte, vendors file and stylesheet is unchanged.
The original bundle is retained as the reproducible base. A changed base,
unmapped import or uncertain module identity fails closed. Repeating a build with
the same sources/toolchain produces the same asset. This is a targeted asset
build, **not** a successful run of the original full Webpack build.

For a local iframe fixture, serve the actual `weavescope-topolog/index.html`
same-origin with a parent defining `iframeGetNodeUrl()` (a fixture API URL),
`iframeGetTopologyScope()` (JSON string of `[team, region, application]`),
`iframeGetTenantName()`, `iframeGetRegion()`, `iframeGetGroupId()`. Minimal valid
response: `{ "code": 200, "data": { "bean": { "json_data": {}, "json_svg": {} } } }`.
A node uses its service ID as key and at least `service_id`, `service_alias`,
`service_cname`, `cur_status`; matching `json_svg` values are adjacency arrays.
`running`/`closed`/`stopped`/`third_party` are stable; all other states, including
operator resources without reliable desired replicas, remain conservative 5s.

The parent may post `{type: 'rainbond:topology-refresh', scope}` to the iframe's
exact origin. Only its actual parent, same origin and current scope are accepted.
This requests through the same single-flight scheduler, not a frame reload.
Because an accepted start/stop/upgrade action may still report its old stable
status before the worker begins, an explicit refresh grants at most three 5s
follow-up reads, then stable polling returns to 15s. Failures always use the
normal 10/20/40/60s backoff, including refreshes queued during a failed request.
Changing application identity or stopping discards this fast-follow-up budget.
`rainbond:topology-stop` stops and invalidates it. API schemas are unchanged.
