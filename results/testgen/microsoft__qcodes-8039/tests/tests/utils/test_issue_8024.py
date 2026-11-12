import pytest
import qcodes
import traceback

class Foo(qcodes.Instrument):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

    @property
    def faulty_property(self):
        # This property will raise an AttributeError because 'bar' does not exist
        return self.bar

    @property
    def another_faulty_property(self):
        # This property will raise a TypeError
        return 1 + "string"

def test_faulty_property_traceback():
    instr = Foo('test_foo')

    # Expecting an AttributeError to be raised, originating from 'self.bar'
    # The current behavior is that qcodes catches this and re-raises a generic AttributeError
    # that obscures the original source.
    with pytest.raises(AttributeError) as excinfo:
        _ = instr.faulty_property

    # Check that the traceback contains the expected line from our faulty_property
    # The issue states that the traceback should point to 'self.bar'.
    # On the unfixed code, this assertion is expected to FAIL.
    tb_str = "".join(traceback.format_exception(type(excinfo.type), excinfo.value, excinfo.tb))
    assert "return self.bar" in tb_str
    assert "faulty_property" in tb_str
    assert "qcodes/utils/attribute_helpers.py" not in tb_str

def test_another_faulty_property_traceback():
    instr = Foo('test_another_foo')

    # Expecting a TypeError to be raised, originating from '1 + "string"'
    with pytest.raises(TypeError) as excinfo:
        _ = instr.another_faulty_property

    tb_str = "".join(traceback.format_exception(type(excinfo.type), excinfo.value, excinfo.tb))
    assert 'return 1 + "string"' in tb_str
    assert "another_faulty_property" in tb_str
    assert "qcodes/utils/attribute_helpers.py" not in tb_str
