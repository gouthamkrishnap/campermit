from campermit.__main__ import main


def test_main_print_version_and_returns_zero(capsys):
    exit_code = main()
    output = capsys.readouterr().out

    assert exit_code == 0
    assert output.startswith("campermit")
