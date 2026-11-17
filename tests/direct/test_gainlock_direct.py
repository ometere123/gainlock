"""Official genlayer-test Direct Mode scenarios (not a live Studio consensus proof)."""
import json

def setup(direct_vm, direct_deploy, direct_owner, direct_alice):
    direct_vm.sender = direct_owner
    contract = direct_deploy("contracts/gainlock.py", sdk_version="v0.2.12")
    from gltest.direct import create_address
    direct_alice = create_address("gainlock-alice")
    network = contract.create_network("Direct Mode event network", 5, 16)
    node = contract.register_node(network, direct_alice, "Alpha event",
        "An approved batch is published.", "When a notification is published.")
    with direct_vm.prank(direct_alice):
        contract.accept_node(node, contract.get_node(node)["spec_hash"])
    return contract, network, node


def test_sealed_root_and_replay(direct_vm, direct_deploy, direct_owner, direct_alice):
    contract, network, node = setup(direct_vm, direct_deploy, direct_owner, direct_alice)
    from gltest.direct import create_address
    direct_alice = create_address("gainlock-alice")
    fingerprint = contract.seal_network(network)
    assert len(fingerprint) == 64
    with direct_vm.prank(direct_alice):
        run = contract.start_run(network, node)
    permit = contract.get_run(run)["root_permit_id"]
    assert contract.is_permit_spendable(permit, direct_alice)
    with direct_vm.prank(direct_alice):
        assert contract.consume_permit(permit)
    assert not contract.is_permit_spendable(permit, direct_alice)


def connected(direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob):
    contract, network, node = setup(direct_vm, direct_deploy, direct_owner, direct_alice)
    from gltest.direct import create_address
    direct_alice = create_address("gainlock-alice")
    direct_bob = create_address("gainlock-bob")
    other = contract.register_node(network, direct_bob, "Beta event",
        "A notification is published to the owner.",
        "Whenever an approved batch is published.")
    with direct_vm.prank(direct_bob):
        contract.accept_node(other, contract.get_node(other)["spec_hash"])
    edge = contract.propose_edge(network, node, other, 1)
    fingerprint = contract.get_edge(edge)["proposal_hash"]
    with direct_vm.prank(direct_alice):
        contract.consent_edge(edge, fingerprint)
    with direct_vm.prank(direct_bob):
        contract.consent_edge(edge, fingerprint)
    return contract, network, edge


def test_consensus_match_and_validator(direct_vm, direct_deploy, direct_owner,
                                       direct_alice, direct_bob):
    contract, network, edge = connected(direct_vm, direct_deploy,
        direct_owner, direct_alice, direct_bob)
    direct_vm.mock_llm(r"You are verifying ONE declared trigger relationship",
        json.dumps({"relation":"MATCH","reason":"The descriptions entail the frozen trigger."}))
    assert contract.assess_edge(edge) == 2
    assert contract.get_graph_analysis(network)["cycle_kind"] == "ACYCLIC"
    assert direct_vm.run_validator() is True


def test_uncertain_does_not_activate(direct_vm, direct_deploy, direct_owner,
                                     direct_alice, direct_bob):
    contract, network, edge = connected(direct_vm, direct_deploy,
        direct_owner, direct_alice, direct_bob)
    direct_vm.mock_llm(r"You are verifying ONE declared trigger relationship",
        json.dumps({"relation":"UNCERTAIN","reason":"Missing condition."}))
    assert contract.assess_edge(edge) == 5
    assert contract.get_graph_analysis(network)["max_total"] == 1
    assert direct_vm.run_validator() is True


def test_model_error_can_retry_to_match(direct_vm, direct_deploy, direct_owner,
                                        direct_alice, direct_bob):
    contract, network, edge = connected(direct_vm, direct_deploy,
        direct_owner, direct_alice, direct_bob)
    direct_vm.mock_llm(r"You are verifying ONE declared trigger relationship",
        "not-json")
    assert contract.assess_edge(edge) == 6
    first = contract.get_edge(edge)
    assert first["assessment_attempts"] == 1
    assert first["source_ok"] and first["target_ok"]
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"You are verifying ONE declared trigger relationship",
        json.dumps({"relation":"MATCH", "reason":"The frozen descriptions entail the trigger."}))
    assert contract.assess_edge(edge) == 2
    final = contract.get_edge(edge)
    assert final["assessment_attempts"] == 2
    assert final["relation"] == "MATCH"


def test_model_error_retry_limit_is_terminal(direct_vm, direct_deploy,
                                             direct_owner, direct_alice,
                                             direct_bob):
    contract, network, edge = connected(direct_vm, direct_deploy,
        direct_owner, direct_alice, direct_bob)
    direct_vm.mock_llm(r"You are verifying ONE declared trigger relationship",
        "not-json")
    assert contract.assess_edge(edge) == 6
    assert contract.assess_edge(edge) == 6
    assert contract.assess_edge(edge) == 7
    final = contract.get_edge(edge)
    assert final["assessment_attempts"] == 3
    assert final["retry_exhausted"] is True
    with direct_vm.expect_revert("assessment retry limit reached"):
        contract.assess_edge(edge)
    assert contract.get_graph_analysis(network)["max_total"] == 1


def test_direct_unit_fanout_branching_cycle_denied(
        direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob, direct_charlie):
    """A->B, A->C, B->A, C->A; the last edge amplifies even though each fanout is one."""
    from gltest.direct import create_address
    direct_vm.sender = direct_owner
    contract = direct_deploy("contracts/gainlock.py", sdk_version="v0.2.12")
    network = contract.create_network("Branching unit feedback case", 6, 12)
    people = [create_address(x) for x in ("gainlock-alice", "gainlock-bob", "gainlock-charlie")]
    nodes = []
    for i, controller in enumerate(people):
        output = "A payment is approved and publicly acknowledged." if i == 0 else "A payment alert is publicly acknowledged."
        trigger = "Whenever a payment alert is publicly acknowledged." if i == 0 else "Whenever a payment is approved and publicly acknowledged."
        node = contract.register_node(network, controller, f"Feedback event {i}", output, trigger)
        with direct_vm.prank(controller):
            contract.accept_node(node, contract.get_node(node)["spec_hash"])
        nodes.append(node)
    direct_vm.mock_llm(r"You are verifying ONE declared trigger relationship",
        json.dumps({"relation":"MATCH", "reason":"Exact registered event necessarily matches trigger."}))
    statuses = []
    for source_index, target_index in [(0,1),(0,2),(1,0),(2,0)]:
        source, target = nodes[source_index], nodes[target_index]
        edge = contract.propose_edge(network, source, target, 1)
        fingerprint = contract.get_edge(edge)["proposal_hash"]
        with direct_vm.prank(people[source_index]):
            contract.consent_edge(edge, fingerprint)
        with direct_vm.prank(people[target_index]):
            contract.consent_edge(edge, fingerprint)
        statuses.append(int(contract.assess_edge(edge)))
    assert statuses == [2,2,2,4]
    assert contract.get_edge(edge)["assessed_graph_kind"] == "AMPLIFYING"
    assert contract.get_graph_analysis(network)["cycle_kind"] == "PERSISTENT"
    assert direct_vm.run_validator() is True


def test_direct_wrong_controller_cannot_start_run(
        direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob):
    from gltest.direct import create_address
    contract, network, node = setup(direct_vm, direct_deploy, direct_owner, direct_alice)
    contract.seal_network(network)
    with direct_vm.prank(create_address("gainlock-bob")):
        with direct_vm.expect_revert("only root controller"):
            contract.start_run(network, node)


def test_closed_run_releases_capacity_without_identifier_reuse(
        direct_vm, direct_deploy, direct_owner, direct_alice):
    contract, network, node = setup(direct_vm, direct_deploy, direct_owner,
                                    direct_alice)
    from gltest.direct import create_address
    direct_alice = create_address("gainlock-alice")
    contract.seal_network(network)
    with direct_vm.prank(direct_alice):
        first_run = contract.start_run(network, node)
    first_permit = contract.get_run(first_run)["root_permit_id"]
    with direct_vm.prank(direct_alice):
        contract.close_run(first_run)
        second_run = contract.start_run(network, node)
    second_permit = contract.get_run(second_run)["root_permit_id"]
    assert second_run != first_run
    assert second_permit != first_permit
    assert not contract.is_permit_spendable(first_permit, direct_alice)
    assert contract.is_permit_spendable(second_permit, direct_alice)


def test_direct_validator_detects_fabricated_semantic_match(
        direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob):
    contract, network, edge = connected(direct_vm, direct_deploy,
        direct_owner, direct_alice, direct_bob)
    direct_vm.mock_llm(r"You are verifying ONE declared trigger relationship",
        json.dumps({"relation":"MATCH", "reason":"leader claims match"}))
    assert contract.assess_edge(edge) == 2
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"You are verifying ONE declared trigger relationship",
        json.dumps({"relation":"NO_MATCH", "reason":"validator rejects the entailment"}))
    assert direct_vm.run_validator() is False
