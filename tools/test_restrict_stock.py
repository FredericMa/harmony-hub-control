"""Run with python3 tools/test_restrict_stock.py; does not contact a hub."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.restrict_stock import configure_transport


HEADER = bytes.fromhex("1b4c75615100010404040804")


def lua_chunk(address: bytes) -> bytes:
    def lua_string(value: bytes) -> bytes:
        return len(value).to_bytes(4, "little") + value

    return (
        HEADER
        + lua_string(b"")
        + bytes(12)
        + bytes(4)
        + (1).to_bytes(4, "little")
        + b"\x04"
        + lua_string(address + b"\0")
        + bytes(16)
    )


hbus = lua_chunk(b"0.0.0.0")
restricted_hbus = configure_transport(hbus, "hbushttpserverconnector.lua")
assert b"127.0.0.1\0" in restricted_hbus
assert configure_transport(restricted_hbus, "hbushttpserverconnector.lua") == restricted_hbus

restricted_xmpp = lua_chunk(b"127.0.0.1")
public_xmpp = configure_transport(restricted_xmpp, "xmppserverconnector.lua")
assert b"*\0" in public_xmpp
assert configure_transport(public_xmpp, "xmppserverconnector.lua") == public_xmpp

print("HBus remains loopback-only; XMPP remains network-accessible")
