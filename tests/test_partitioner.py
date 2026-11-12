"""Partition tests."""

from coordinator.partitioner import partition_frame, read_dataset


def test_partition_covers_every_row_once() -> None:
    frame = read_dataset("delay\n1\n2\n3\n4\n5\n")
    chunks = partition_frame(frame, 2)
    assert [len(chunk) for chunk in chunks] == [2, 2, 1]
    assert list(chunks[0]["delay"]) == [1, 2]
    assert list(chunks[2]["delay"]) == [5]
