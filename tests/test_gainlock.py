"""Dependency-free protocol tests using a lightweight SDK stand-in.

These verify the pure graph kernel and contract authorization/state transitions.
They DO NOT simulate the real GenVM or Studio consensus; on-chain tests remain
necessary. The stand-in calls leader and validator independently.
"""
import hashlib
import importlib.util
import json
import pathlib
import sys
import types
import unittest

CONTRACT = pathlib.Path(__file__).resolve().parents[1] / "contracts" / "gainlock.py"


def reference_totals(node_count, edges, max_hops):
    """Independent small-graph enumerator used as a mathematical oracle."""
    matrix = [[0] * node_count for _ in range(node_count)]
    for source, target, multiplicity in edges:
        matrix[source][target] += multiplicity
    totals = []
    for root in range(node_count):
        layer = [0] * node_count
        layer[root] = 1
        total = 1
        for _ in range(max_hops):
            next_layer = [0] * node_count
            for source in range(node_count):
                for target in range(node_count):
                    next_layer[target] += layer[source] * matrix[source][target]
            total += sum(next_layer)
            layer = next_layer
        totals.append(total)
    return totals


def reference_has_cycle(node_count, edges):
    adjacency = [[] for _ in range(node_count)]
    for source, target, _ in edges:
        adjacency[source].append(target)

    def visit(node, active, seen):
        if node in active:
            return True
        if node in seen:
            return False
        seen.add(node)
        active.add(node)
        if any(visit(child, active, seen) for child in adjacency[node]):
            return True
        active.remove(node)
        return False

    return any(visit(root, set(), set()) for root in range(node_count))


class FakeTreeMap:
    def __class_getitem__(cls, item):
        return dict


class FakeEvent:
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def emit(cls, *args, **kwargs):
        return None


class FakeContract:
    pass


class Return:
    def __init__(self, value):
        self.calldata = value


class FakeVM:
    Return = Return

    class UserError(Exception):
        pass

    def __init__(self):
        self.validate = True
        self.last_validator_result = None
        self.calls = 0

    def run_nondet_unsafe(self, leader, validator):
        proposed = leader()
        self.calls += 1
        # Each validator calls its own LLM independently through leader().
        self.last_validator_result = validator(Return(proposed))
        if not self.last_validator_result:
            raise ValueError("validator rejected leader")
        return proposed


class LLM:
    def __init__(self):
        self.answers = []
        self.prompts = []

    def exec_prompt(self, prompt):
        self.prompts.append(prompt)
        if not self.answers:
            raise RuntimeError("mock LLM exhausted")
        return self.answers.pop(0)


class SDK:
    def __init__(self):
        self.mod = types.ModuleType("genlayer")
        self.gl = types.SimpleNamespace()
        self.gl.Contract = FakeContract
        self.gl.Event = FakeEvent
        self.gl.vm = FakeVM()
        self.gl.nondet = LLM()
        self.gl.message = types.SimpleNamespace(sender_address="owner")
        self.gl.contract_interface = lambda cls: cls
        self.gl.public = types.SimpleNamespace(write=lambda fn: fn, view=lambda fn: fn)
        self.mod.gl = self.gl
        self.mod.Address = str
        self.mod.u256 = int
        self.mod.u8 = int
        self.mod.u32 = int
        self.mod.TreeMap = FakeTreeMap
        self.mod.DynArray = list
        self.mod.allow_storage = lambda cls: cls
        self.mod.Keccak256 = lambda data: hashlib.sha3_256(data)
        self.mod.__all__ = ["gl", "Address", "u256", "u8", "u32", "TreeMap", "DynArray", "allow_storage", "Keccak256"]

    def load(self):
        sys.modules["genlayer"] = self.mod
        spec = importlib.util.spec_from_file_location("gainlock_contract", CONTRACT)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


class KernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = SDK().load()

    def test_empty_acyclic(self):
        a = self.m.bounded_analysis(3, [], 5, 10)
        self.assertEqual(a["cycle_kind"], "ACYCLIC")
        self.assertEqual(a["root_totals"], [1, 1, 1])

    def test_persistent_unit_cycle(self):
        a = self.m.bounded_analysis(2, [(0, 1, 1), (1, 0, 1)], 7, 9)
        self.assertEqual(a["cycle_kind"], "PERSISTENT")
        self.assertEqual(a["root_totals"], [8, 8])
        self.assertTrue(a["admissible"])

    def test_branching_diamond_amplifies_with_unit_edge_weights(self):
        edges = [(0, 1, 1), (0, 2, 1), (1, 0, 1), (2, 0, 1)]
        a = self.m.bounded_analysis(3, edges, 7, 15)
        self.assertEqual(a["cycle_kind"], "AMPLIFYING")
        self.assertFalse(a["admissible"])
        self.assertGreater(a["max_total"], 15)

    def test_self_loop_with_multiple_outputs(self):
        a = self.m.bounded_analysis(1, [(0, 0, 2)], 6, 30)
        self.assertEqual(a["cycle_kind"], "AMPLIFYING")
        self.assertFalse(a["admissible"])

    def test_acyclic_branching_can_exceed_budget(self):
        a = self.m.bounded_analysis(3, [(0, 1, 8), (1, 2, 8)], 2, 50)
        self.assertEqual(a["cycle_kind"], "ACYCLIC")
        self.assertFalse(a["admissible"])

    def test_parallel_edges_sum(self):
        a = self.m.bounded_analysis(2, [(0, 1, 3), (0, 1, 2)], 1, 6)
        self.assertEqual(a["root_totals"], [6, 1])

    def test_independent_sccs(self):
        a = self.m.bounded_analysis(4, [(0, 1, 1), (1, 0, 1), (2, 3, 2), (3, 2, 1)], 3, 30)
        self.assertEqual(a["cycle_kind"], "AMPLIFYING")
        self.assertEqual(len(a["cycles"]), 2)

    def test_out_of_bounds_rejected(self):
        for args in [(0, [], 2, 50), (2, [(0, 2, 1)], 2, 50),
                     (2, [(0, 1, 0)], 2, 50), (2, [], 13, 50), (2, [], 1, 0)]:
            with self.assertRaises(ValueError):
                self.m.bounded_analysis(*args)

    def test_reference_limits_are_exact(self):
        self.assertEqual(self.m.bounded_analysis(1, [], 1, 1)["root_totals"], [1])
        self.assertEqual(self.m.bounded_analysis(12, [], 12, 100000)["max_total"], 1)
        with self.assertRaises(ValueError):
            self.m.bounded_analysis(13, [], 1, 1)
        with self.assertRaises(ValueError):
            self.m.bounded_analysis(1, [], 13, 1)
        with self.assertRaises(ValueError):
            self.m.bounded_analysis(1, [(0, 0, 9)], 1, 1)
        with self.assertRaises(ValueError):
            self.m.bounded_analysis(1, [], 1, 100001)

    def test_saturation_prevents_integer_blowup(self):
        a = self.m.bounded_analysis(1, [(0, 0, 8)], 12, 100000)
        self.assertEqual(a["root_totals"], [100001])

    def test_safe_result_strict(self):
        self.assertEqual(self.m._safe_result('{"relation":"MATCH","reason":"valid"}')["relation"], "MATCH")
        self.assertEqual(self.m._safe_result('{"relation":true}')["relation"], "MODEL_ERROR")
        self.assertEqual(self.m._safe_result("not json")["relation"], "MODEL_ERROR")
        self.assertEqual(self.m._safe_result(None)["relation"], "MODEL_ERROR")
        self.assertEqual(self.m._safe_result('{"relation":"MATCH","reason":"x","extra":1}') ["relation"], "MODEL_ERROR")
        self.assertEqual(self.m._safe_result('{"relation":"MATCH","reason":"x"}' + " " * 2001)["relation"], "MODEL_ERROR")
        bounded = self.m._safe_result(json.dumps({"relation": "MATCH", "reason": "r" * 400}))
        self.assertEqual(bounded["relation"], "MATCH")
        self.assertEqual(len(bounded["reason"]), self.m.MAX_REASON)

    def test_reference_graph_totals_and_cycle_presence(self):
        cases = [
            (3, [(0, 1, 1), (1, 2, 1)], 6, [3, 2, 1], False),
            (2, [(0, 1, 1), (1, 0, 1)], 5, [6, 6], True),
            (3, [(0, 1, 1), (0, 2, 1), (1, 0, 1), (2, 0, 1)], 6,
             [29, 22, 22], True),
        ]
        for node_count, edges, hops, expected, has_cycle in cases:
            self.assertEqual(reference_totals(node_count, edges, hops), expected)
            self.assertEqual(reference_has_cycle(node_count, edges), has_cycle)
            actual = self.m.bounded_analysis(node_count, edges, hops, 100000)
            self.assertEqual(actual["root_totals"], expected)

    def test_reference_saturation_is_budget_plus_one(self):
        actual = self.m.bounded_analysis(3,
            [(0, 1, 1), (0, 2, 1), (1, 0, 1), (2, 0, 1)], 6, 12)
        self.assertEqual(actual["max_total"], 13)
        self.assertFalse(actual["admissible"])


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.sdk = SDK()
        self.m = self.sdk.load()
        self.c = self.m.GainLock()
        for key in ("networks", "nodes", "edges", "runs", "permits", "parent_spawn_count"):
            setattr(self.c, key, {})
        self.sdk.gl.message.sender_address = "owner"

    def sender(self, identity):
        self.sdk.gl.message.sender_address = identity

    def network(self, budget=35, hops=6):
        self.sender("owner")
        return self.c.create_network("Demo event trigger network", hops, budget)

    def node(self, network, controller, output, trigger):
        self.sender("owner")
        nid = self.c.register_node(network, controller, "Event channel alpha", output, trigger)
        self.sender(controller)
        self.c.accept_node(nid, self.c.get_node(nid)["spec_hash"])
        return nid

    def edge(self, network, src, dst, fanout=1, relation="MATCH", validator=None):
        self.sender("owner")
        eid = self.c.propose_edge(network, src, dst, fanout)
        for controller in (self.c.nodes[src].controller, self.c.nodes[dst].controller):
            self.sender(controller)
            self.c.consent_edge(eid, self.c.get_edge(eid)["proposal_hash"])
        self.sdk.gl.nondet.answers = [
            json.dumps({"relation": relation, "reason": "Descriptions satisfy the frozen trigger."}),
            json.dumps({"relation": validator or relation, "reason": "Independent check."}),
        ]
        self.sender("third-party")
        return eid, self.c.assess_edge(eid)

    def test_controller_must_accept_spec(self):
        n = self.network()
        self.sender("owner")
        nid = self.c.register_node(n, "alice", "Invoice approval", "An invoice is approved for payment.", "When a payment is authorized.")
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.accept_node(nid, "wrong")
        self.sender("alice")
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.accept_node(nid, "wrong")
        self.c.accept_node(nid, self.c.get_node(nid)["spec_hash"])
        self.assertTrue(self.c.get_node(nid)["approved"])

    def test_unauthorized_node_add_fails(self):
        n = self.network()
        self.sender("attacker")
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.register_node(n, "attacker", "Invoice approval", "An invoice is approved for payment.", "When an invoice is approved.")

    def test_edge_requires_bilateral_consent(self):
        n = self.network()
        a = self.node(n, "alice", "An invoice is approved for payment.", "When an invoice is approved.")
        b = self.node(n, "bob", "A payment alert is delivered.", "When an invoice is approved.")
        self.sender("owner")
        eid = self.c.propose_edge(n, a, b, 1)
        self.sender("alice")
        self.c.consent_edge(eid, self.c.get_edge(eid)["proposal_hash"])
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.assess_edge(eid)
        self.assertFalse(self.c.get_edge(eid)["target_ok"])

    def test_validator_disagreement_is_not_a_receipt(self):
        n = self.network()
        a = self.node(n, "alice", "An invoice is approved for payment.", "When an invoice is approved.")
        b = self.node(n, "bob", "A payment alert is delivered.", "When an invoice is approved.")
        self.sender("owner")
        eid = self.c.propose_edge(n, a, b, 1)
        for who in ("alice", "bob"):
            self.sender(who)
            self.c.consent_edge(eid, self.c.get_edge(eid)["proposal_hash"])
        self.sdk.gl.nondet.answers = [
            '{"relation":"MATCH","reason":"leader fabricated"}',
            '{"relation":"NO_MATCH","reason":"independent validator disagrees"}',
        ]
        with self.assertRaisesRegex(ValueError, "validator rejected"):
            self.c.assess_edge(eid)
        self.assertEqual(self.c.get_edge(eid)["status"], self.m.PROPOSED)
        self.assertEqual(len(self.c.get_graph_analysis(n)["cycles"]), 0)

    def test_disagreement_fail_closed(self):
        n = self.network()
        a = self.node(n,"alice","Invoice approved for payment.","When an invoice is approved.")
        b = self.node(n,"bob","Payment alert delivered to user.","When invoice approved for payment.")
        eid, state = self.edge(n,a,b,relation="UNCERTAIN")
        self.assertEqual(state, self.m.REJECTED_UNCERTAIN)
        self.assertEqual(self.c.get_graph_analysis(n)["max_total"], 1)

    def test_model_error_is_retryable_and_preserves_consents(self):
        n = self.network()
        a = self.node(n, "alice", "An invoice is approved for payment.", "When an invoice is approved.")
        b = self.node(n, "bob", "A payment alert is delivered.", "When an invoice is approved.")
        self.sender("owner")
        eid = self.c.propose_edge(n, a, b, 1)
        for who in ("alice", "bob"):
            self.sender(who)
            self.c.consent_edge(eid, self.c.get_edge(eid)["proposal_hash"])
        self.sdk.gl.nondet.answers = ["not json", "not json"]
        self.sender("third-party")
        self.assertEqual(self.c.assess_edge(eid), self.m.MODEL_ERROR)
        first = self.c.get_edge(eid)
        self.assertEqual(first["assessment_attempts"], 1)
        self.assertTrue(first["source_ok"] and first["target_ok"])
        self.assertEqual(self.c.get_graph_analysis(n)["max_total"], 1)
        self.sdk.gl.nondet.answers = [
            json.dumps({"relation": "MATCH", "reason": "The frozen descriptions entail the trigger."}),
            json.dumps({"relation": "MATCH", "reason": "Independent agreement."}),
        ]
        self.assertEqual(self.c.assess_edge(eid), self.m.ACTIVE)
        final = self.c.get_edge(eid)
        self.assertEqual(final["assessment_attempts"], 2)
        self.assertEqual(final["relation"], "MATCH")

    def test_model_error_retry_limit_is_committed_and_terminal(self):
        n = self.network()
        a = self.node(n, "alice", "An invoice is approved for payment.", "When an invoice is approved.")
        b = self.node(n, "bob", "A payment alert is delivered.", "When an invoice is approved.")
        self.sender("owner")
        eid = self.c.propose_edge(n, a, b, 1)
        for who in ("alice", "bob"):
            self.sender(who)
            self.c.consent_edge(eid, self.c.get_edge(eid)["proposal_hash"])
        self.sender("third-party")
        self.sdk.gl.nondet.answers = ["bad", "bad", "bad", "bad", "bad", "bad"]
        self.assertEqual(self.c.assess_edge(eid), self.m.MODEL_ERROR)
        self.assertEqual(self.c.assess_edge(eid), self.m.MODEL_ERROR)
        self.assertEqual(self.c.assess_edge(eid), self.m.RETRY_EXHAUSTED)
        edge = self.c.get_edge(eid)
        self.assertEqual(edge["assessment_attempts"], 3)
        self.assertTrue(edge["retry_exhausted"])
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.assess_edge(eid)
        self.assertEqual(self.c.get_graph_analysis(n)["max_total"], 1)

    def test_uncertain_is_terminal_not_retryable(self):
        n = self.network()
        a = self.node(n, "alice", "An invoice is approved for payment.", "When an invoice is approved.")
        b = self.node(n, "bob", "A payment alert is delivered.", "When an invoice is approved.")
        eid, state = self.edge(n, a, b, relation="UNCERTAIN")
        self.assertEqual(state, self.m.REJECTED_UNCERTAIN)
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.assess_edge(eid)

    def test_no_match_rejected(self):
        n = self.network()
        a = self.node(n,"alice","A draft invoice is created.","When a draft invoice is created.")
        b = self.node(n,"bob","Payment alert delivered to user.","When a payment is confirmed.")
        eid, state = self.edge(n,a,b,relation="NO_MATCH")
        self.assertEqual(state, self.m.REJECTED_SEMANTIC)

    def test_safe_two_node_cycle_has_bounded_permits(self):
        n = self.network(budget=7,hops=5)
        a = self.node(n,"alice","An invoice is approved for payment.","When a notification is sent.")
        b = self.node(n,"bob","A notification is sent to account owner.","When an invoice is approved for payment.")
        self.assertEqual(self.edge(n,a,b)[1],self.m.ACTIVE)
        self.assertEqual(self.edge(n,b,a)[1],self.m.ACTIVE)
        self.assertEqual(self.c.get_graph_analysis(n)["cycle_kind"],"PERSISTENT")
        self.sender("owner")
        self.c.seal_network(n)
        self.sender("alice")
        run = self.c.start_run(n,a)
        self.assertTrue(self.c.get_run(run)["active"])
        self.assertFalse(self.c.get_permit(1)["spent"])
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.spawn_child(1, 1)
        self.c.consume_permit(1)
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.consume_permit(1)
        p2 = self.c.spawn_child(1, 1)
        self.sender("bob")
        self.c.consume_permit(p2)
        p3 = self.c.spawn_child(p2, 2)
        self.assertEqual(self.c.get_permit(p3)["depth"],2)
        self.sender("alice")
        self.c.consume_permit(p3)
        self.assertEqual(self.c.get_run(run)["permits_issued"],3)

    def test_amplifying_edge_rejected_by_budget(self):
        n = self.network(budget=12,hops=6)
        a = self.node(n,"alice","Approved payment reported to public ledger.","When a payment alert is reported.")
        b = self.node(n,"bob","Payment alert is reported to coordinator.","When approved payment reported.")
        c = self.node(n,"carol","Payment alert is reported to coordinator.","When approved payment reported.")
        self.assertEqual(self.edge(n,a,b)[1],self.m.ACTIVE)
        self.assertEqual(self.edge(n,a,c)[1],self.m.ACTIVE)
        self.assertEqual(self.edge(n,b,a)[1],self.m.ACTIVE)
        eid, state = self.edge(n,c,a)
        self.assertEqual(state,self.m.REJECTED_BUDGET)
        self.assertEqual(self.c.get_edge(eid)["assessed_graph_kind"],"AMPLIFYING")
        self.assertEqual(self.c.get_graph_analysis(n)["cycle_kind"],"PERSISTENT")

    def test_fanout_cap_applies_per_parent_and_edge(self):
        n = self.network(budget=30,hops=2)
        a = self.node(n,"alice","A public alert is raised now.","When an alert is raised.")
        b = self.node(n,"bob","A notification is sent to operator.","When a public alert is raised now.")
        e, state = self.edge(n,a,b,fanout=2)
        self.assertEqual(state, self.m.ACTIVE)
        self.sender("owner")
        self.c.seal_network(n)
        self.sender("alice")
        run = self.c.start_run(n,a)
        self.c.consume_permit(1)
        p2 = self.c.spawn_child(1,e)
        p3 = self.c.spawn_child(1,e)
        self.assertNotEqual(p2,p3)
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.spawn_child(1,e)
        self.sender("bob")
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.consume_permit(1)
        self.c.consume_permit(p2)
        self.c.consume_permit(p3)
        self.assertEqual(self.c.get_run(run)["permits_issued"],3)

    def test_no_edit_after_seal(self):
        n = self.network()
        a = self.node(n,"alice","A public alert has been raised.","When a public alert is raised.")
        self.sender("owner")
        self.c.seal_network(n)
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.register_node(n,"alice","Another event","Another event has been raised.","When another event is raised.")
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.seal_network(n)

    def test_networks_are_isolated(self):
        n1 = self.network()
        n2 = self.network()
        a = self.node(n1,"alice","A payment event is reported.","When a payment event is reported.")
        b = self.node(n2,"bob","An invoice event is reported.","When a payment event is reported.")
        self.sender("owner")
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.propose_edge(n1,a,b,1)

    def test_run_can_close_permits(self):
        n = self.network()
        a = self.node(n,"alice","A payment event is reported.","When payment event is reported.")
        self.sender("owner")
        self.c.seal_network(n)
        self.sender("alice")
        run = self.c.start_run(n,a)
        self.c.close_run(run)
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.consume_permit(1)
        self.assertFalse(self.c.is_permit_spendable(1,"alice"))

    def test_closed_run_releases_active_capacity_without_reusing_ids(self):
        n1 = self.network()
        a1 = self.node(n1, "alice", "A payment event is reported.", "When a payment event is reported.")
        n2 = self.network()
        a2 = self.node(n2, "bob", "An invoice event is reported.", "When an invoice event is reported.")
        for network, node, controller in ((n1, a1, "alice"), (n2, a2, "bob")):
            self.sender("owner")
            self.c.seal_network(network)
            self.sender(controller)
            run = self.c.start_run(network, node)
            permit = self.c.get_run(run)["root_permit_id"]
            self.c.close_run(run)
            self.assertFalse(self.c.is_permit_spendable(permit, controller))
        self.sender("owner")
        self.assertEqual(self.c.get_network(n1)["active_runs"], 0)
        self.assertEqual(self.c.get_network(n1)["active_permits"], 0)
        self.assertEqual(self.c.get_network(n2)["active_runs"], 0)
        self.assertEqual(self.c.get_network(n2)["active_permits"], 0)

    def test_many_closed_runs_do_not_hit_historical_lifetime_ceiling(self):
        n = self.network(budget=1, hops=1)
        a = self.node(n, "alice", "A payment event is reported.", "When a payment event is reported.")
        self.sender("owner")
        self.c.seal_network(n)
        self.sender("alice")
        last_run = 0
        last_permit = 0
        for _ in range(self.m.MAX_RUNS + 1):
            last_run = self.c.start_run(n, a)
            last_permit = self.c.get_run(last_run)["root_permit_id"]
            self.c.close_run(last_run)
        self.assertEqual(int(last_run), self.m.MAX_RUNS + 1)
        self.assertEqual(int(last_permit), self.m.MAX_RUNS + 1)
        self.assertEqual(self.c.get_network(n)["active_runs"], 0)
        self.assertEqual(self.c.get_network(n)["active_permits"], 0)

    def test_active_run_capacity_is_per_network(self):
        n1 = self.network(budget=1, hops=1)
        a1 = self.node(n1, "alice", "A payment event is reported.", "When a payment event is reported.")
        n2 = self.network(budget=1, hops=1)
        a2 = self.node(n2, "bob", "An invoice event is reported.", "When an invoice event is reported.")
        self.sender("owner")
        self.c.seal_network(n1)
        self.c.seal_network(n2)
        self.sender("alice")
        runs = [self.c.start_run(n1, a1) for _ in range(self.m.MAX_RUNS)]
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.start_run(n1, a1)
        self.sender("bob")
        run2 = self.c.start_run(n2, a2)
        self.assertEqual(self.c.get_run(run2)["network_id"], n2)
        self.sender("alice")
        for run in runs:
            self.c.close_run(run)
        self.sender("bob")
        self.c.close_run(run2)

    def test_sealed_graph_hash_is_stable(self):
        n = self.network()
        a = self.node(n,"alice","A payment event is reported.","When a payment event is reported.")
        self.sender("owner")
        h = self.c.seal_network(n)
        self.assertEqual(len(h),64)
        self.assertEqual(self.c.get_network(n)["graph_hash"],h)

    def test_network_and_text_boundaries(self):
        self.sender("owner")
        n = self.c.create_network("N" * self.m.MAX_NAME, self.m.MAX_HOPS, self.m.MAX_BUDGET)
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.create_network("N" * (self.m.MAX_NAME + 1), 1, 1)
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.create_network("Valid network", 0, 1)
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.create_network("Valid network", 13, 1)
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.create_network("Valid network", 1, 0)
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.create_network("Valid network", 1, self.m.MAX_BUDGET + 1)
        node = self.c.register_node(n, "alice", "L" * self.m.MAX_NAME,
            "E" * self.m.MAX_EVENT_TEXT, "T" * self.m.MAX_TRIGGER_TEXT)
        self.sender("alice")
        self.c.accept_node(node, self.c.get_node(node)["spec_hash"])
        self.assertEqual(len(self.c.get_node(node)["output_event"]), self.m.MAX_EVENT_TEXT)
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.sender("owner")
            self.c.register_node(n, "alice", "Label ok", "E" * (self.m.MAX_EVENT_TEXT + 1), "Trigger ok")
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.register_node(n, "alice", "Label ok", "Event ok", "T" * (self.m.MAX_TRIGGER_TEXT + 1))
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.register_node(n, "alice", "Label ok", "Bad\nEvent", "Trigger ok")

    def test_node_and_edge_limits_are_exact(self):
        n = self.network()
        nodes = []
        for index in range(self.m.MAX_NODES):
            self.sender("owner")
            node = self.c.register_node(n, "controller", f"Node {index:02d} label",
                "A registered event is emitted.", "When a registered event is emitted.")
            self.sender("controller")
            self.c.accept_node(node, self.c.get_node(node)["spec_hash"])
            nodes.append(node)
        self.sender("owner")
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.register_node(n, "controller", "Node overflow", "A registered event is emitted.",
                                 "When a registered event is emitted.")
        pairs = [(source, target) for source in nodes for target in nodes if source != target]
        for source, target in pairs[:self.m.MAX_EDGES]:
            self.c.propose_edge(n, source, target, 1)
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.propose_edge(n, pairs[self.m.MAX_EDGES][0], pairs[self.m.MAX_EDGES][1], 1)

    def test_fanout_boundaries_are_exact(self):
        n = self.network()
        a = self.node(n, "alice", "A payment event is reported.", "When a payment event is reported.")
        b = self.node(n, "bob", "A notification event is reported.", "When a notification event is reported.")
        self.sender("owner")
        edge = self.c.propose_edge(n, a, b, self.m.MAX_FANOUT)
        self.assertEqual(self.c.get_edge(edge)["fanout"], self.m.MAX_FANOUT)
        with self.assertRaises(self.sdk.gl.vm.UserError):
            self.c.propose_edge(n, b, a, self.m.MAX_FANOUT + 1)


if __name__ == "__main__":
    unittest.main()
