// Run against a fresh GainLock deployment. Writes JSON Lines to stdout.
import assert from 'node:assert/strict';
import { closeSync, openSync, readFileSync, writeSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { Wallet } from 'ethers';
import { createClient, createAccount, generatePrivateKey } from 'genlayer-js';
import { studionet } from 'genlayer-js/chains';
import { CalldataAddress } from 'genlayer-js/types';

const rpc = 'https://studio.genlayer.com/api';
const address = process.argv[2];
assert.match(address ?? '', /^0x[0-9a-fA-F]{40}$/);
async function request(method, params = []) {
  const response = await fetch(rpc, {
    method: 'POST', headers: {'content-type': 'application/json'},
    body: JSON.stringify({jsonrpc: '2.0', id: 1, method, params}),
    signal: AbortSignal.timeout(15000),
  });
  const body = await response.json();
  if (!response.ok || body.error) throw new Error(JSON.stringify(body.error ?? response.status));
  return body.result;
}
assert.equal(await request('eth_chainId'), '0xf22f');
assert.equal(JSON.parse(readFileSync(new URL('../node_modules/genlayer/package.json', import.meta.url))).version, '0.39.1');
function password() {
  const {stdin, stderr} = process;
  assert.ok(stdin.isTTY);
  stderr.write('PRAEST keystore password: ');
  return new Promise((resolve, reject) => {
    let value = '';
    function finish(error) {
      stdin.off('data', receive);
      stdin.setRawMode(false);
      stdin.pause();
      stderr.write('\n');
      if (error) reject(error); else resolve(value);
    }
    function receive(chunk) {
      for (const c of chunk.toString()) {
        if (c === '\r' || c === '\n') return finish();
        if (c === '\u0003') return finish(new Error('Cancelled'));
        if (c === '\u007f' || c === '\b') value = value.slice(0, -1);
        else value += c;
      }
    }
    stdin.setRawMode(true);
    stdin.on('data', receive);
    stdin.resume();
  });
}
const keystore = join(process.env.GENLAYER_HOME ?? join(homedir(), '.genlayer'), 'keystores', 'praest-deployer.json');
const owner = createAccount((await Wallet.fromEncryptedJson(readFileSync(keystore, 'utf8'), await password())).privateKey);
const peer = createAccount(generatePrivateKey());
const client = account => createClient({chain: studionet, endpoint: rpc, account});
const readers = client(owner);
const writers = new Map([[owner, readers], [peer, client(peer)]]);
const records = [];
const evidenceFd = process.argv[3] ? openSync(process.argv[3], 'wx') : null;
const emit = value => {
  const line = JSON.stringify(value, (_, v) => typeof v === 'bigint' ? v.toString() : v);
  if (evidenceFd !== null) writeSync(evidenceFd, line + '\n');
  console.log(line);
};
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function wait(hash, requireFinal) {
  for (let i = 0; i < 120; ++i) {
    await pause(4500);
    const t = await request('eth_getTransactionByHash', [hash]);
    if (t && (t.status === 'FINALIZED' || (!requireFinal && t.status === 'ACCEPTED'))) return t;
  }
  throw new Error(`Timed out waiting for ${hash}`);
}
function result(t) {
  const leader = t.consensus_data?.leader_receipt?.[0];
  return {status: t.status, consensus: t.result_name ?? t.result,
    execution: leader?.execution_result, error: leader?.genvm_result?.error_description
      ?? leader?.genvm_result?.raw_error, votes: t.consensus_data?.votes};
}
async function write(actor, method, args, expected = 'SUCCESS') {
  const hash = await writers.get(actor).writeContract({address, functionName: method, args, value: 0n});
  emit({submitted: hash, caller: actor.address, method, args: args.map(a => a instanceof CalldataAddress ? '0x' + Buffer.from(a.bytes).toString('hex') : a)});
  records.push({hash, method, expected});
  const observed = result(await wait(hash, false));
  emit({hash, method, observed});
  assert.equal(observed.execution, expected, JSON.stringify(observed));
  return observed;
}
async function read(method, ...args) {
  const value = await readers.readContract({address, functionName: method, args});
  emit({read: method, args, value});
  return value;
}
let networkId = 0, nodeId = 0, edgeId = 0;
const addressArg = actor => new CalldataAddress(Buffer.from(actor.address.slice(2), 'hex'));
const event = 'Every output is an event tagged REVIEW-DEMO with payment confirmed.';
const trigger = 'Trigger on every event tagged REVIEW-DEMO with payment confirmed.';
async function network(name, hops, budget, specs) {
  const id = ++networkId;
  await write(owner, 'create_network', [name, hops, budget]);
  assert.equal((await read('get_network', id)).name, name);
  const nodes = [];
  for (const [label, actor, output, condition] of specs) {
    const n = ++nodeId;
    await write(owner, 'register_node', [id, addressArg(actor), label, output ?? event, condition ?? trigger]);
    const proposed = await read('get_node', n);
    await write(actor, 'accept_node', [n, proposed.spec_hash]);
    assert.equal((await read('get_node', n)).approved, true);
    nodes.push({id: n, actor});
  }
  return {id, nodes};
}
async function edge(network, u, v, expected) {
  const id = ++edgeId;
  const from = network.nodes[u], to = network.nodes[v];
  await write(owner, 'propose_edge', [network.id, from.id, to.id, 1]);
  const proposed = await read('get_edge', id);
  for (const actor of new Set([from.actor, to.actor])) {
    await write(actor, 'consent_edge', [id, proposed.proposal_hash]);
  }
  await write(owner, 'assess_edge', [id]);
  const assessed = await read('get_edge', id);
  assert.equal(Number(assessed.status), expected, JSON.stringify(assessed));
  return {id, assessed};
}
const pair = [['A', owner], ['B', peer]];
const trio = [...pair, ['C', owner]];
try {
  const dag = await network('Review DAG', 6, 25, trio);
  await edge(dag, 0, 1, 2);
  await edge(dag, 1, 2, 2);
  const acyclic = await read('get_graph_analysis', dag.id);
  assert.equal(acyclic.cycle_kind, 'ACYCLIC');
  assert.equal(Number(acyclic.max_total), 3);
  emit({scenario: 'safe acyclic chain', passed: true});

  const cycle = await network('Review persistent', 5, 7, pair);
  const ab = await edge(cycle, 0, 1, 2);
  await edge(cycle, 1, 0, 2);
  const bounded = await read('get_graph_analysis', cycle.id);
  assert.equal(bounded.cycle_kind, 'PERSISTENT');
  assert.deepEqual(bounded.root_totals.map(Number), [6, 6]);
  await write(owner, 'seal_network', [cycle.id]);
  assert.equal((await read('get_network', cycle.id)).sealed, true);
  await write(owner, 'start_run', [cycle.id, cycle.nodes[0].id]);
  const run = await read('get_run', 1);
  const permit = Number(run.root_permit_id);
  const unauthorized = await write(peer, 'consume_permit', [permit], 'ERROR');
  assert.match(JSON.stringify(unauthorized), /wrong event controller/i);
  assert.equal((await read('get_permit', permit)).spent, false);
  await write(owner, 'consume_permit', [permit]);
  const replay = await write(owner, 'consume_permit', [permit], 'ERROR');
  assert.match(JSON.stringify(replay), /permit already spent/i);
  assert.equal((await read('get_permit', permit)).spent, true);
  await write(owner, 'spawn_child', [permit, ab.id]);
  const child = await read('get_permit', permit + 1);
  assert.equal(Number(child.depth), 1);
  assert.equal(Number(child.node_id), cycle.nodes[1].id);
  await write(peer, 'consume_permit', [permit + 1]);
  assert.equal((await read('get_permit', permit + 1)).spent, true);
  emit({scenario: 'bounded persistent cycle and permit controls', passed: true});

  const amp = await network('Review branching', 6, 12, trio);
  await edge(amp, 0, 1, 2);
  await edge(amp, 0, 2, 2);
  await edge(amp, 1, 0, 2);
  const rejected = await edge(amp, 2, 0, 4);
  assert.equal(rejected.assessed.assessed_graph_kind, 'AMPLIFYING');
  assert.equal((await read('get_graph_analysis', amp.id)).cycle_kind, 'PERSISTENT');
  emit({scenario: 'unit-fanout branching amplification', passed: true});

  const uncertain = await network('Review uncertain', 3, 8, [
    ['A', owner, 'Every output says an invoice was created. A payment may or may not have been confirmed.'],
    ['B', peer, event, 'Trigger only if payment was confirmed for that invoice.'],
  ]);
  const ambiguous = await edge(uncertain, 0, 1, 5);
  assert.equal(ambiguous.assessed.relation, 'UNCERTAIN');
  assert.equal(Number((await read('get_graph_analysis', uncertain.id)).max_total), 1);
  emit({scenario: 'uncertain trigger', passed: true});
} catch (error) {
  emit({scenario_error: error.message});
  process.exitCode = 1;
}
for (const {hash, method, expected} of records) {
  const tx = await request('eth_getTransactionByHash', [hash]);
  const verification = result(tx?.status === 'FINALIZED' ? tx : await wait(hash, true));
  emit({hash, method, verification, explorer: `https://explorer-studio.genlayer.com/tx/${hash}`});
  if (verification.execution !== expected) process.exitCode = 1;
}
if (evidenceFd !== null) closeSync(evidenceFd);
