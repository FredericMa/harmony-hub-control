"""Configure stock Lua 5.1 listener bindings without changing engine logic."""
import struct


def configure_transport(data: bytes, name: str, public_xmpp: bool = True, public_hbus: bool = False) -> bytes:
    bindings = {
        "hbushttpserverconnector.lua": (
            b"0.0.0.0" if public_hbus else b"127.0.0.1",
            (b"0.0.0.0", b"127.0.0.1"),
        ),
        "xmppserverconnector.lua": (
            b"*" if public_xmpp else b"127.0.0.1",
            (b"*", b"127.0.0.1"),
        ),
    }
    if name not in bindings or data[:12] != bytes.fromhex("1b4c75615100010404040804"):
        raise ValueError("Unsupported transport or Lua bytecode; no changes made")
    pos, strings = 12, []

    def count():
        nonlocal pos
        if pos + 4 > len(data):
            raise ValueError("Truncated bytecode")
        value = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        if value > 1_000_000:
            raise ValueError("Invalid bytecode count")
        return value

    def skip(size):
        nonlocal pos
        pos += size
        if pos > len(data):
            raise ValueError("Truncated bytecode")

    def string(constant=False):
        start = pos
        size = count()
        value = data[pos:pos + size]
        if size and (len(value) != size or value[-1] != 0):
            raise ValueError("Malformed Lua string")
        skip(size)
        if constant:
            strings.append((start, pos, value[:-1]))

    def function(depth=0):
        if depth > 32:
            raise ValueError("Bytecode nesting limit")
        string()
        skip(12)  # lines, upvalues, parameters, vararg, stack size
        skip(count() * 4)
        for _ in range(count()):
            if pos >= len(data):
                raise ValueError("Truncated bytecode")
            kind = data[pos]
            skip(1)
            if kind == 1:
                skip(1)
            elif kind == 3:
                skip(8)
            elif kind == 4:
                string(True)
            elif kind != 0:
                raise ValueError("Unsupported constant type")
        for _ in range(count()):
            function(depth + 1)
        skip(count() * 4)
        for _ in range(count()):
            string()
            skip(8)
        for _ in range(count()):
            string()

    function()
    if pos != len(data):
        raise ValueError("Unexpected trailing bytecode")
    target, valid_bindings = bindings[name]
    matches = [(start, end, value) for start, end, value in strings if value in valid_bindings]
    if len(matches) != 1:
        raise ValueError("Expected exactly one listener address; no changes made")
    start, end, current = matches[0]
    if current == target:
        return data
    value = target + b"\0"
    return data[:start] + struct.pack("<I", len(value)) + value + data[end:]
