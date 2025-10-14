import pytest

from features_pipeline.config.confload import to_bool, to_int


@pytest.mark.parametrize(
    "input_val, expected",
    [
        (True, True),
        (False, False),
        ("True", True),
        ("False", False),
        ("true", True),
        ("false", False),
        ("TrUe", True),
        ("faLse", False)
    ]
)
def test_to_bool(input_val, expected):
    assert to_bool(input_val) is expected


def test_to_bool_invalid():
    with pytest.raises(ValueError) as e:
        to_bool("talse")


@pytest.mark.parametrize(
    "input_val, expected",
    [
        ("1", 1),
        (1, 1),
        (1.5, 1)
    ]
)
def test_to_int(input_val, expected):
    assert to_int(input_val) is expected

def test_to_int_invalid():
    with pytest.raises(ValueError) as e:
        to_int("1.5")
