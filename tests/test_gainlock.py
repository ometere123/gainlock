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

    def test_saturation_prevents_integer_blowup(self):
        a = self.m.bounded_analysis(1, [(0, 0, 8)], 12, 100000)
        self.assertEqual(a["root_totals"], [100001])

    def test_safe_result_strict(self):
        self.assertEqual(self.m._safe_result('{"relation":"MATCH","reason":"valid"}')["relation"], "MATCH")
        self.assertEqual(self.m._safe_result('{"relation":true}')["relation"], "UNCERTAIN")
        self.assertEqual(self.m._safe_result("not json")["relation"], "UNCERTAIN")
        self.assertEqual(self.m._safe_result(None)["relation"], "UNCERTAIN")


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

    def test_sealed_graph_hash_is_stable(self):
        n = self.network()
        a = self.node(n,"alice","A payment event is reported.","When a payment event is reported.")
        self.sender("owner")
        h = self.c.seal_network(n)
        self.assertEqual(len(h),64)
        self.assertEqual(self.c.get_network(n)["graph_hash"],h)


if __name__ == "__main__":
    unittest.main()
