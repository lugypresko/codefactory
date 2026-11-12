import pennylane as qp
import pytest

# Define TemporaryAND gate for the decomposition
class TemporaryAND(qp.ControlledPhaseShift):
    num_wires = 3
    grad_method = None

# This test ensures that when num_work_wires is specified and minimize_work_wires is True,
# the graph decomposer successfully uses work wires if they are necessary for decomposition,
# instead of falling back to legacy decomposition.
def test_minimize_work_wires_with_required_work_wire():
    n = 4
    wires = range(n)

    @qp.decompose(
        gate_set={TemporaryAND, qp.CNOT, qp.X, qp.Toffoli, qp.GlobalPhase},
        num_work_wires=1,
        minimize_work_wires=True,
    )
    @qp.qnode(qp.device("default.qubit"))
    def circuit():
        qp.MultiControlledX(wires)
        return qp.state()

    # Execute the circuit to populate the tape

    drawn_circuit = qp.draw(circuit)();

    assert "Allocate" in drawn_circuit, (
        "Expected Allocate in drawn circuit for unfixed bug (decomposer fallback)."
    )
    assert "Deallocate" in drawn_circuit, (
        "Expected Deallocate in drawn circuit for unfixed bug (decomposer fallback)."
    )
    assert "DynamicWire" in drawn_circuit, (
        "Expected DynamicWire in drawn circuit for unfixed bug (decomposer fallback)."
    )

