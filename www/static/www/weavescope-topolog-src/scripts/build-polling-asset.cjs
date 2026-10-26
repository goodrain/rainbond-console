/* Recompile one verified legacy webpack module; leave every other asset byte untouched. */
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
// The splice bounds come from the verified AST node, never from a compressed text replacement.
const asset = base.slice(0, factory.start) + replacement + base.slice(factory.end);
parser.parse(asset, { sourceType: 'script' });
assert.equal(asset.slice(0, factory.start), base.slice(0, factory.start));
assert.equal(asset.slice(factory.start + replacement.length), base.slice(factory.end));
const name = `app-polling-${sha(asset).slice(0, 20)}.js`;
fs.writeFileSync(path.join(output, name), asset);
const indexPath = path.join(output, 'index.html');
const index = fs.readFileSync(indexPath, 'utf8');
const entries = [...index.matchAll(/src="(app(?:-polling)?-[a-z0-9]+\.js)(?:\?[^"]*)?"/g)];
assert.equal(entries.length, 1, 'Expected exactly one topology app entry');
fs.writeFileSync(indexPath, index.replace(entries[0][0], `src="${name}"`));
console.log(JSON.stringify({ asset: name, sha256: sha(asset), baseSha256: sha(base), moduleId: 426,
  sourceSha256: sha(source), helperSha256: sha(helper), unchangedModules: modules.elements.filter(Boolean).length - 1,
  babelVersion: babel.version, toolchain }, null, 2));
