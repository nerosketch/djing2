import os
import subprocess
from typing import Optional


def _filter_uname(uname: str) -> bytes:
    _uname = str(uname).encode()
    _uname = _uname.replace(b'"', b"")
    _uname = _uname.replace(b"'", b"")
    return _uname


def _exec_radclient(script_name: str, params_list: list, stdin_data: Optional[bytes] = None) -> bool:
    """
    Exec radclient from customizable bash scripts.
    :param script_name: bash file name from 'radclient' sub directory.
            For example 'radclient-coa-guest2inet.sh'.
    :param params_list: additional params to bash script.
    :param stdin_data: stdin for radclient.
    :return: boolean, is return code of script is equal 0
    """
    file_dir = os.path.dirname(__file__)
    exec_path = os.path.join(file_dir, "radclient", script_name)
    exec_params = [exec_path] + params_list
    r = subprocess.run(exec_params, input=stdin_data)
    return r.returncode == 0


def finish_session(radius_uname: str) -> bool:
    """Send radius disconnect packet to BRAS."""
    if not radius_uname:
        return False
    uname = _filter_uname(radius_uname)
    return _exec_radclient("radclient-disconnect.sh", params_list=[uname])


def change_session_inet2guest(radius_uname: str) -> bool:
    if not radius_uname:
        return False
    uname = _filter_uname(radius_uname)
    # COA inet -> guest
    return _exec_radclient("radclient-coa-inet2guest.sh", params_list=[uname])


def change_session_guest2inet(
    radius_uname: str, speed_in: int, speed_out: int, speed_in_burst: int, speed_out_burst: int
) -> bool:
    """
    Send COA via radclient, change guest service type to inet service type.
    :param radius_uname: User-Name from radius
    :param speed_in: Customer service input speed in bits/s
    :param speed_out: Customer service output speed in bits/s
    :param speed_in_burst: Customer service input speed burst
    :param speed_out_burst: Customer service output speed burst
    :return: boolean, is return code of script is equal 0
    """
    if not radius_uname:
        return False
    uname = _filter_uname(radius_uname)
    speed_in = int(speed_in)
    speed_out = int(speed_out)
    speed_in_burst, speed_out_burst = int(speed_in_burst), int(speed_out_burst)

    # COA guest -> inet
    return _exec_radclient(
        "radclient-coa-guest2inet.sh", params_list=[uname, speed_in, speed_out, speed_in_burst, speed_out_burst]
    )
