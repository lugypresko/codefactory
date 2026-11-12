import pytest
from vllm_mlx.reasoning.gemma4_parser import Gemma4ReasoningParser
from vllm_mlx.reasoning.base import DeltaMessage

def test_delta_straddling_channel_close_splits_reasoning_and_content():
    parser = Gemma4ReasoningParser()
    # Simulate stream_interval > 1 flush: one delta containing the
    # tail of thought, the channel-close marker, and the start of content.
    previous = "<|channel>thoughtthinking..."
    delta    = " final thought<channel|><|channel>contentHello"
    current  = previous + delta
    msg = parser.extract_reasoning_streaming(previous, current, delta)
    assert msg.reasoning == " final thought"
    assert msg.content == "Hello"
