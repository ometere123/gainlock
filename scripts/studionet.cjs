'use strict';
// ALWAYS use project-local GenLayer CLI 0.39.1. Never fall back to global 0.40.0rc2.
const path = require('path');
const fs = require('fs');
const cp = require('child_process');
const root = path.resolve(__dirname, '..');
const cmd = path.join(root, 'node_modules', '.bin', process.platform === 'win32' ? 'genlayer.cmd' : 'genlayer');
const expectedVersion = '0.39.1';
const expectedAlias = 'studionet';
const expectedRpc = 'https://studio.genlayer.com/api';
const expectedId = '61999';
function fail(message) { console.error('GAINLOCK NETWORK GUARD: ' + message); process.exit(1); }
if (!fs.existsSync(cmd)) fail('Project-local CLI not installed. Run npm install in repository first.');
function run(args) {
  return cp.execFileSync(cmd, args, {cwd: root, encoding: 'utf8', stdio: ['inherit', 'pipe', 'pipe']}).trim();
}
let version;
try { version = run(['--version']); } catch (e) { fail('Unable to inspect local CLI version: ' + (e.stderr || e.message)); }
if (!new RegExp('(?:^|[^0-9])0\\.39\\.1(?:[^0-9]|$)').test(version)) fail('CLI must be 0.39.1, saw: ' + version);
console.log('Project-local CLI version: ' + version);
const mode = process.argv[2] || '--check';
if (mode === '--select') {
  try { console.log(run(['network', 'set', expectedAlias])); }
  catch (e) { fail('Unable to select stable studionet: ' + (e.stderr || e.message)); }
} else if (mode !== '--check' && mode !== '--deploy') {
  fail('Expected --check, --select, or --deploy');
}
let info;
try { info = run(['network', 'info']); }
catch (e) { fail('Unable to read active network info: ' + (e.stderr || e.message)); }
console.log(info);
const normalized = info.toLowerCase();
if (!normalized.includes(expectedAlias) || !normalized.includes(expectedRpc) ||
    !info.includes(expectedId) || normalized.includes('studio-dev') || info.includes('61997')) {
  fail(`Expected alias ${expectedAlias}, chain ${expectedId}, RPC ${expectedRpc}. Refusing operation.`);
}
console.log('GAINLOCK GUARD PASS: stable StudioNet only (61999).');
if (mode === '--deploy') {
  console.log('Deploying GainLock on stable StudioNet. Wallet and balance must be configured locally.');
  try {
    cp.execFileSync(cmd, ['deploy', '--contract', 'contracts/gainlock.py'], {cwd: root, stdio: 'inherit'});
  } catch (e) { fail('Deployment command failed. Check wallet/funding/network; do not infer any successful transaction.'); }
}
