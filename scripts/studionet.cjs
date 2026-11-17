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
  return invoke(args, ['inherit', 'pipe', 'pipe']).trim();
}
function invoke(args, stdio) {
  const options = {cwd: root, encoding: 'utf8', stdio};
  if (process.platform === 'win32') {
    const entry = path.join(root, 'node_modules', 'genlayer', 'dist', 'index.js');
    return cp.execFileSync(process.execPath, [entry, ...args], options);
  }
  return cp.execFileSync(cmd, args, options);
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
let account;
try { account = run(['account']); }
catch (e) { fail('Unable to inspect the selected deployment account: ' + (e.stderr || e.message)); }
const addressMatch = account.match(/address:\s*['"](0x[0-9a-fA-F]{40})['"]/);
if (!addressMatch) fail('Selected account did not expose a valid public address.');
const expectedAccount = process.env.GAINLOCK_DEPLOYER_ADDRESS;
if (expectedAccount && addressMatch[1].toLowerCase() !== expectedAccount.toLowerCase()) {
  fail(`Selected account ${addressMatch[1]} does not match GAINLOCK_DEPLOYER_ADDRESS.`);
}
console.log('Selected deployment account: ' + addressMatch[1]);
console.log(account);
async function verifyRpc() {
  const response = await fetch(expectedRpc, {
    method: 'POST',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify({jsonrpc: '2.0', id: 1, method: 'eth_chainId', params: []}),
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new Error(`RPC HTTP ${response.status}`);
  const body = await response.json();
  if (body.error || body.result !== '0xf22f') throw new Error(`Unexpected eth_chainId: ${JSON.stringify(body)}`);
  console.log('GAINLOCK GUARD PASS: stable StudioNet only (61999), live eth_chainId=0xf22f.');
  if (mode === '--deploy') {
    console.log('Deploying GainLock on stable StudioNet. Wallet and balance must be configured locally.');
    try {
      invoke(['deploy', '--contract', 'contracts/gainlock.py'], 'inherit');
    } catch (e) { fail('Deployment command failed. Check wallet/funding/network; do not infer any successful transaction.'); }
  }
}
verifyRpc().catch(e => fail(e.message));
