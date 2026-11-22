import pytest

from campermit.identity import is_trusted_serial


@pytest.mark.parametrize(
    "serial",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param("0001", id="laptop-camera-placeholder"),
        pytest.param("SN0001", id="xiaomi-placeholder"),
        pytest.param("00000", id="short-zeros"),
        pytest.param("000000000000", id="one-repeated-character"),
        pytest.param("000000000001", id="two-distinct-characters"),
        pytest.param("00000000050C", id="real-but-mostly-zeros"),
        pytest.param("0123456789ABCDEF", id="android-default"),
        pytest.param("0123456789abcdef", id="android-default-lowercase"),
        pytest.param("ABCDEF\x00123456", id="not-printable"),
        pytest.param("ÄBCDEF123456", id="not-ascii"),
    ],
)
def test_untrusted_serials(serial):
    assert not is_trusted_serial(serial)


@pytest.mark.parametrize(
    "serial",
    [
        pytest.param("A1B2C3D4E5F6", id="twelve-mixed"),
        pytest.param("2F7K9Q4M8X1B", id="twelve-random"),
        pytest.param("ABCDEF123456XYZ", id="fifteen-mixed"),
    ],
)
def test_trusted_serials(serial):
    assert is_trusted_serial(serial)
