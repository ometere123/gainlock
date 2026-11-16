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
