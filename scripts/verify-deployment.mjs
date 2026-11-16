import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';

const rpc = 'https://studio.genlayer.com/api';
const hash = process.argv[2];
const commit = process.argv[3];
assert.match(hash ?? '', /^0x[0-9a-f]{64}$/i);
assert.match(commit ?? '', /^[0-9a-f]{40}$/i);
async function query(method, params = []) {
  const response = await fetch(rpc, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({jsonrpc: '2.0', id: 1, method, params}),
    signal: AbortSignal.timeout(15000),
  });
  const body = await response.json();
  if (!response.ok || body.error) throw new Error(JSON.stringify(body.error ?? response.status));
  return body.result;
}
const chainId = await query('eth_chainId');
assert.equal(chainId, '0xf22f');
const tx = await query('eth_getTransactionByHash', [hash]);
assert.equal(tx?.hash, hash);
const leader = tx.consensus_data?.leader_receipt?.[0];
const deployed = Buffer.from(tx.data.contract_code, 'base64');
const committed = execFileSync('git', ['show', `${commit}:contracts/gainlock.py`], {
  cwd: new URL('../', import.meta.url),
});
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const exactMatch = deployed.equals(committed);
const success = tx.status === 'FINALIZED' && leader?.execution_result === 'SUCCESS';
const candidateAddress = tx.data.contract_address ?? tx.to_address;
const live = success ? await query('gen_getContractCode', [candidateAddress]) : null;
const deployedBytes = typeof live === 'string' ? Buffer.from(live, 'base64') : null;
const liveMatch = deployedBytes?.equals(committed) ?? false;
const evidence = {
  rpc, chainId, hash, sourceCommit: commit, status: tx.status,
  consensus: tx.result_name ?? tx.result, execution: leader?.execution_result ?? null,
  executionError: leader?.genvm_result?.error_description ?? null,
  candidateAddress,
  verifiedAddress: success && liveMatch && exactMatch ? candidateAddress : null,
  source: {
    transactionPayloadSha256: digest(deployed), committedSha256: digest(committed),
    bytes: deployed.byteLength, exactMatch,
    liveSha256: deployedBytes ? digest(deployedBytes) : null, liveMatch,
  },
  explorer: `https://explorer-studio.genlayer.com/tx/${hash}`,
  receipt: await query('eth_getTransactionReceipt', [hash]),
};
const json = JSON.stringify(evidence, null, 2);
if (process.argv[4]) writeFileSync(process.argv[4], json + '\n', {flag: 'wx'});
console.log(json);
if (!success || !exactMatch || !liveMatch) process.exitCode = 1;
