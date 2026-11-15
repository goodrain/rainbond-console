/* Recompile verified legacy webpack modules; leave unrelated modules byte untouched. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const output = path.resolve(root, '../weavescope-topolog');
const baseName = 'app-95196a50339e0f8f1469.js';
const baseSha = '0a9d6471ee22a315b220c6eb66123f4baa87f2860354150801d91d4da6682739';
const toolArg = process.argv.indexOf('--toolchain');
const toolchain = toolArg >= 0 ? path.resolve(process.argv[toolArg + 1]) : path.join(root, 'node_modules');
function dependency(name) { return require(require.resolve(name, { paths: [toolchain] })); }
const babel = dependency('@babel/core');
const parser = dependency('@babel/parser');
const generate = dependency('@babel/generator').default;
const traverse = dependency('@babel/traverse').default;
let preset;
try { preset = require.resolve('@babel/preset-env', { paths: [toolchain] }); }
catch (_) { preset = require.resolve('@umijs/deps/compiled/babel/preset-env', { paths: [toolchain] }); }
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const base = fs.readFileSync(path.join(output, baseName), 'utf8');
assert.equal(sha(base), baseSha, 'The frozen webpack base changed; review its module/dependency map before rebuilding.');
const ast = parser.parse(base, { sourceType: 'script' });
const registration = ast.program.body.find(statement => statement.type === 'ExpressionStatement' &&
  statement.expression.type === 'CallExpression' && statement.expression.callee.name === 'webpackJsonp');
assert.ok(registration, 'Expected a webpackJsonp registration');
const modules = registration.expression.arguments[1];
assert.equal(modules.type, 'ArrayExpression');
const candidates = modules.elements.filter(node => node && node.type === 'FunctionExpression' &&
  base.slice(node.start, node.end).includes("'scope:web-api-utils'"));
assert.equal(candidates.length, 1, 'web-api-utils factory must be unique');
const factory = candidates[0];
assert.equal(modules.elements.indexOf(factory), 426, 'Unexpected module identity');
const oldFactory = base.slice(factory.start, factory.end);
const mapping = {
  debug: 47,
  immutable: 11,
  'lodash/defaults': 1665,
  reqwest: 1824,
  '../actions/app-actions': 25,
  '../constants/timer': 198,
  '../selectors/resource-view/layout': 421
};
const dependencyIds = [...oldFactory.matchAll(/__webpack_require__\((\d+)\)/g)].map(match => Number(match[1]));
assert.deepEqual([...new Set(dependencyIds)].sort((a, b) => a - b), Object.values(mapping).sort((a, b) => a - b),
  'Legacy dependency identity changed');
assert.ok(oldFactory.includes('exports.getNodesDelta = getNodesDelta;') &&
  oldFactory.includes('exports.stopPolling = stopPolling;'), 'Not the expected CommonJS export contract');
const sourcePath = path.join(root, 'app/scripts/utils/web-api-utils.js');
const helperPath = path.join(root, 'app/scripts/utils/topology-polling.js');
const source = fs.readFileSync(sourcePath, 'utf8');
const helper = fs.readFileSync(helperPath, 'utf8');
const compiled = babel.transformSync(source, {
  babelrc: false, configFile: false, comments: true,
  presets: [[preset, { targets: { ie: '11' }, modules: 'commonjs' }]]
});
const compiledAst = parser.parse(compiled.code, { sourceType: 'script' });
traverse(compiledAst, {
  CallExpression(nodePath) {
    const node = nodePath.node;
    if (node.callee.type !== 'Identifier' || node.callee.name !== 'require') return;
    assert.equal(node.arguments.length, 1);
    assert.equal(node.arguments[0].type, 'StringLiteral', 'Dynamic imports are not supported by this scoped builder');
    const name = node.arguments[0].value;
    if (name === './topology-polling') nodePath.replaceWith(babel.types.identifier('__topologyPolling'));
    else {
      assert.ok(Object.hasOwn(mapping, name), `Unmapped dependency ${name}`);
      nodePath.replaceWith(babel.types.callExpression(babel.types.identifier('__webpack_require__'), [babel.types.numericLiteral(mapping[name])]));
    }
  }
});
const code = generate(compiledAst, { comments: true }).code;
const replacement = 'function(module, exports, __webpack_require__) {\n' +
  `/* topology-source-sha256: ${sha(source)}; topology-helper-sha256: ${sha(helper)} */\n` +
  'var __topologyPolling = (function() { var module = { exports: {} };\n' + helper +
  '\nreturn module.exports; }());\n' + code + '\n}';
let reactPreset;
try { reactPreset = require.resolve('@babel/preset-react', { paths: [toolchain] }); }
catch (_) { reactPreset = require.resolve('@umijs/deps/compiled/babel/preset-react', { paths: [toolchain] }); }
const chartModules = [
  { id: 414, name: 'node.js', mapping: {
    classnames: 26, immutable: 11, react: 1, 'react-redux': 14,
    '../actions/app-actions': 25, '../components/matched-results': 756,
    '../components/matched-text': 92, '../constants/styles': 27,
    '../utils/color-utils': 118, './node-networks-overlay': 741,
    './node-shape-stack': 742, './node-shapes': 743
  } },
  { id: 743, name: 'node-shapes.js', mapping: {
    react: 1, classnames: 26, '../constants/styles': 27,
    '../utils/metric-utils': 789, '../utils/node-shape-utils': 790
  } }
];
const replacements = [{ factory, replacement }];
const chartSources = [];
for (const chart of chartModules) {
  const chartFactory = modules.elements[chart.id];
  assert.equal(chartFactory.type, 'FunctionExpression');
  const original = base.slice(chartFactory.start, chartFactory.end);
  const ids = [...new Set([...original.matchAll(/__webpack_require__\((\d+)\)/g)].map(match => Number(match[1])))];
  assert.deepEqual(ids.sort((a, b) => a - b), Object.values(chart.mapping).sort((a, b) => a - b),
    `Legacy dependency identity changed for ${chart.name}`);
  const chartSource = fs.readFileSync(path.join(root, 'app/scripts/charts', chart.name), 'utf8');
  const transformed = babel.transformSync(chartSource, {
    babelrc: false, configFile: false, comments: true,
    presets: [[preset, { targets: { ie: '11' }, modules: 'commonjs' }], [reactPreset, { runtime: 'classic' }]]
  });
  const chartAst = parser.parse(transformed.code, { sourceType: 'script' });
  traverse(chartAst, {
    CallExpression(nodePath) {
      const node = nodePath.node;
      if (node.callee.type !== 'Identifier' || node.callee.name !== 'require') return;
      assert.equal(node.arguments.length, 1);
      assert.equal(node.arguments[0].type, 'StringLiteral');
      const name = node.arguments[0].value;
      assert.ok(Object.hasOwn(chart.mapping, name), `Unmapped dependency ${name}`);
      nodePath.replaceWith(babel.types.callExpression(babel.types.identifier('__webpack_require__'),
        [babel.types.numericLiteral(chart.mapping[name])]));
    }
  });
  const digest = sha(chartSource);
  chartSources.push({ moduleId: chart.id, name: chart.name, sourceSha256: digest });
  replacements.push({ factory: chartFactory,
    replacement: `function(module, exports, __webpack_require__) {\n/* topology-chart-${chart.name}-sha256: ${digest} */\n` +
      generate(chartAst, { comments: true }).code + '\n}' });
}
// Splice verified AST bounds from right to left so all original offsets remain valid.
let asset = base;
for (const item of replacements.sort((a, b) => b.factory.start - a.factory.start)) {
  asset = asset.slice(0, item.factory.start) + item.replacement + asset.slice(item.factory.end);
}
parser.parse(asset, { sourceType: 'script' });
const name = `app-polling-${sha(asset).slice(0, 20)}.js`;
fs.writeFileSync(path.join(output, name), asset);
const indexPath = path.join(output, 'index.html');
const index = fs.readFileSync(indexPath, 'utf8');
const entries = [...index.matchAll(/src="(app(?:-polling)?-[a-z0-9]+\.js)(?:\?[^"]*)?"/g)];
assert.equal(entries.length, 1, 'Expected exactly one topology app entry');
fs.writeFileSync(indexPath, index.replace(entries[0][0], `src="${name}"`));
console.log(JSON.stringify({ asset: name, sha256: sha(asset), baseSha256: sha(base), moduleId: 426,
  sourceSha256: sha(source), helperSha256: sha(helper), chartSources,
  unchangedModules: modules.elements.filter(Boolean).length - replacements.length,
  babelVersion: babel.version, toolchain }, null, 2));
