// Run the live semantic-uncertainty acceptance against an existing deployment.
import assert from 'node:assert/strict';
import { closeSync, openSync, readFileSync, writeSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { Wallet } from 'ethers';
import { createAccount, createClient } from 'genlayer-js';
import { studionet } from 'genlayer-js/chains';
import { CalldataAddress } from 'genlayer-js/types';

const rpc = 'https://studio.genlayer.com/api';
const address = process.argv[2];
const evidencePath = process.argv[3];
assert.match(address ?? '', /^0x[0-9a-fA-F]{40}$/);
assert.ok(evidencePath, 'an evidence path is required');
async function request(method, params = []) {
  for (let attempt = 0; attempt < 5; ++attempt) {
    const response = await fetch(rpc, {
      method: 'POST', headers: {'content-type': 'application/json'},
      body: JSON.stringify({jsonrpc: '2.0', id: 1, method, params}),
      signal: AbortSignal.timeout(15000),
    });
    const raw = await response.text();
    try {
      const body = JSON.parse(raw);
      if (!response.ok || body.error) throw new Error(JSON.stringify(body.error ?? response.status));
      return body.result;
    } catch (error) {
      if (attempt === 4) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
    }
  }
  throw new Error(`RPC retry limit reached for ${method}`);
}
assert.equal(await request('eth_chainId'), '0xf22f');
assert.equal(JSON.parse(readFileSync(new URL('../node_modules/genlayer/package.json', import.meta.url))).version, '0.39.1');
function password() {
  const {stdin, stderr} = process;
  assert.ok(stdin.isTTY);
  stderr.write('GainLock StudioNet keystore password: ');
  return new Promise((resolve, reject) => {
    let value = '';
    function finish(error) {
      stdin.off('data', receive); stdin.setRawMode(false); stdin.pause(); stderr.write('\n');
      if (error) reject(error); else resolve(value);
    }
    function receive(chunk) {
      for (const c of chunk.toString()) {
        if (c === '\r' || c === '\n') return finish();
        if (c === '\u0003') return finish(new Error('Cancelled'));
        if (c === '\u007f' || c === '\b') value = value.slice(0, -1); else value += c;
      }
    }
    stdin.setRawMode(true); stdin.on('data', receive); stdin.resume();
  });
}
const keystore = join(process.env.GENLAYER_HOME ?? join(homedir(), '.genlayer'), 'keystores', 'praest-deployer.json');
const owner = createAccount((await Wallet.fromEncryptedJson(readFileSync(keystore, 'utf8'), await password())).privateKey);
const client = createClient({chain: studionet, endpoint: rpc, account: owner});
const fd = openSync(evidencePath, 'wx');
const emit = value => { const line = JSON.stringify(value, (_, v) => typeof v === 'bigint' ? v.toString() : v); writeSync(fd, line + '\n'); console.log(line); };
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function pendingNonce() { return BigInt(await request('eth_getTransactionCount', [owner.address, 'pending'])); }
function result(t) {
  const leader = t.consensus_data?.leader_receipt?.[0];
  return {status: t.status, consensus: t.result_name ?? t.result, execution: leader?.execution_result,
    error: leader?.genvm_result?.error_description ?? leader?.genvm_result?.raw_error ?? null,
    return_data: leader?.result ?? null, votes: t.consensus_data?.votes};
}
async function wait(hash) {
  for (let i = 0; i < 120; ++i) {
    await pause(4500);
    const tx = await request('eth_getTransactionByHash', [hash]);
    if (tx?.status === 'FINALIZED') return tx;
  }
  throw new Error(`Timed out waiting for ${hash}`);
}
async function write(method, args, expected = 'SUCCESS') {
  const before = await pendingNonce();
  let hash;
  for (let attempt = 1; attempt <= 5; ++attempt) {
    try { hash = await client.writeContract({address, functionName: method, args, value: 0n}); break; }
    catch (error) {
      const after = await pendingNonce().catch(() => null);
      emit({write_error: error.message, method, attempt, nonce_advanced: after === null ? null : after !== before});
      if (after !== null && after !== before) throw new Error(`Broadcast status is ambiguous for ${method}`);
      if (attempt === 5) throw error;
      await pause(2000 * attempt);
    }
  }
  emit({submitted: hash, caller: owner.address, method, args: args.map(a => a instanceof CalldataAddress ? '0x' + Buffer.from(a.bytes).toString('hex') : a)});
  const observed = result(await wait(hash));
  emit({hash, method, observed});
  assert.equal(observed.status, 'FINALIZED', JSON.stringify(observed));
  assert.equal(observed.execution, expected, JSON.stringify(observed));
  return {hash, observed};
}
async function read(method, ...args) {
  const value = await client.readContract({address, functionName: method, args});
  emit({read: method, args, value});
  return value;
}
async function nextId(method) {
  for (let id = 1; id <= 1000000; ++id) { try { await client.readContract({address, functionName: method, args: [id]}); } catch (_) { return id; } }
  throw new Error(`No available ${method} identifier`);
}
try {
  const networkId = await nextId('get_network');
  await write('create_network', ['Review uncertain final', 3, 8]);
  const sourceId = await nextId('get_node');
  const targetId = sourceId + 1;
  const sourceText = 'Every output says an invoice was created. A payment may or may not have been confirmed.';
  const targetText = 'Trigger only if payment was confirmed for that invoice.';
  await write('register_node', [networkId, new CalldataAddress(Buffer.from(owner.address.slice(2), 'hex')), 'Review node A', sourceText, targetText]);
  const source = await read('get_node', sourceId);
  await write('accept_node', [sourceId, source.spec_hash]);
  await write('register_node', [networkId, new CalldataAddress(Buffer.from(owner.address.slice(2), 'hex')), 'Review node B', 'Every output is an event tagged REVIEW-DEMO with payment confirmed.', targetText]);
  const target = await read('get_node', targetId);
  await write('accept_node', [targetId, target.spec_hash]);
  const edgeId = await nextId('get_edge');
  await write('propose_edge', [networkId, sourceId, targetId, 1]);
  const proposed = await read('get_edge', edgeId);
  await write('consent_edge', [edgeId, proposed.proposal_hash]);
  let assessed;
  for (let attempt = 1; attempt <= 3; ++attempt) {
    const tx = await write('assess_edge', [edgeId]);
    assessed = await read('get_edge', edgeId);
    if (Number(assessed.status) !== 6) break;
    emit({edge_id: edgeId, attempt, status: Number(assessed.status), retrying: attempt < 3});
    if (attempt === 3) throw new Error('uncertainty edge reached retry exhaustion instead of a semantic decision');
  }
  assert.equal(Number(assessed.status), 5, JSON.stringify(assessed));
  assert.equal(assessed.relation, 'UNCERTAIN', JSON.stringify(assessed));
  const network = await read('get_network', networkId);
  assert.deepEqual(network.edge_ids.map(Number), [edgeId]);
  const graph = await read('get_graph_analysis', networkId);
  assert.equal(graph.cycle_kind, 'ACYCLIC');
  assert.deepEqual(graph.root_totals.map(Number), [1, 1]);
  emit({scenario: 'genuine semantic uncertainty', network_id: networkId, edge_id: edgeId, passed: true});
} catch (error) {
  emit({scenario_error: error.message}); process.exitCode = 1;
} finally { closeSync(fd); }
