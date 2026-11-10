"""Processor tests begin in Phase 4."""

import worker.processor as processor


def test_processor_module_imports() -> None:
    assert processor.__doc__
