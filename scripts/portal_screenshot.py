#!/usr/bin/env python3
"""One-shot screenshot bridge for Nexa on GNOME/Wayland (v2, forensic).

Why this exists: the xdg-desktop-portal Screenshot method is asynchronous.
The method call returns a Request handle immediately; the actual outcome (the
PNG file URI) arrives later as an org.freedesktop.portal.Request.Response
signal. If the caller's D-Bus connection dies before the response — which is
exactly what `gdbus call ...` does when the process exits after printing the
token — the portal CANCELS the request and no file is produced. That was the
"only some screenshots land" flakiness seen in live testing.

This helper keeps the connection alive on a GLib main loop until the real
Response arrives. Run with the SYSTEM python (needs python3-gi):

    /usr/bin/python3 scripts/portal_screenshot.py

v2 added staged, forensic error reporting; v3 fixes the bug it exposed live.
On gi 3.56 + Python 3.14, `GLib.Variant("(sa{sv})", ("", options))` — with a
PRE-BUILT `a{sv}` Variant as the tuple child — raises `KeyError(0)` (seen live:
`ERR variant-build: type=builtins.KeyError args=(0,)`). The canonical pattern
builds the options dict INLINE inside the single Variant construction; v3 does
that, with a fully-plain fallback shape, and reports each attempt forensically.

Stdout contract: zero or more `# <diagnostic>` lines, then exactly one final
line: `OK <png path>` or `ERR <stage>: <detail>`. Exit status follows.
"""
import os
import sys
import time

TIMEOUT_SECONDS = 20

# GNOME portal response codes of interest.
_RESPONSE_MEANINGS = {
    1: "cancelled",
    2: "portal-side error",
}


def _describe_error(e: BaseException) -> str:
    """Unmask an exception completely: type, args, str, GLib.Error attributes."""
    parts = [
        f"type={type(e).__module__}.{type(e).__name__}",
        f"args={e.args!r}",
        f"str={e}",
    ]
    for attr in ("domain", "code", "message"):
        val = getattr(e, attr, None)
        if val is not None:
            parts.append(f"{attr}={val!r}")
    return " ".join(parts)


def _note(msg: str) -> None:
    """Emit a `# ...` diagnostic line (never part of the OK/ERR protocol)."""
    print(f"# {msg}", flush=True)


def main() -> int:
    try:
        import gi
        gi.require_version("Gio", "2.0")
        gi.require_version("GLib", "2.0")
        from gi.repository import Gio, GLib
    except Exception as e:
        print(f"ERR import: {_describe_error(e)} — fix: sudo apt install -y python3-gi")
        return 1

    _note(f"python={sys.version.split()[0]} gi={gi.__version__}")
    _note(
        f"desktop={os.environ.get('XDG_CURRENT_DESKTOP', '?')} "
        f"session-type={os.environ.get('XDG_SESSION_TYPE', '?')} "
        f"bus={'set' if os.environ.get('DBUS_SESSION_BUS_ADDRESS') else 'MISSING'}"
    )

    try:
        conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    except Exception as e:
        print(f"ERR bus-connect: {_describe_error(e)}")
        return 1
    _note(f"unique-name={conn.get_unique_name()}")

    # Canary probe: is the Screenshot interface published at all? Non-fatal —
    # this only enriches the diagnostics if the real call then fails.
    try:
        ver = conn.call_sync(
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.DBus.Properties",
            "Get",
            GLib.Variant("(ss)", ("org.freedesktop.portal.Screenshot", "version")),
            GLib.VariantType.new("(v)"),
            Gio.DBusCallFlags.NONE,
            5000,
            None,
        )
        _note(f"screenshot-interface-version={ver.get_child_value(0).get_variant().get_uint32()}")
    except Exception as e:
        _note(f"screenshot-interface-probe failed: {_describe_error(e)}")

    unique = conn.get_unique_name().lstrip(":").replace(".", "_")
    token = f"nexa{int(time.time() * 1000)}"
    req_path = f"/org/freedesktop/portal/desktop/request/{unique}/{token}"
    _note(f"request-path={req_path}")

    loop = GLib.MainLoop()
    state = {"done": False, "code": None, "uri": None, "results": None}

    def on_response(_conn, _sender, _path, _iface, _signal, params):
        try:
            code = params.get_child_value(0).get_uint32()
            results = params.get_child_value(1)
            uri_variant = results.lookup_value("uri", GLib.VariantType("s"))
        except Exception:
            code, results, uri_variant = 2, None, None
        state["code"] = code
        state["results"] = results
        state["uri"] = uri_variant.get_string() if uri_variant else None
        state["done"] = True
        loop.quit()

    def on_timeout():
        state["done"] = True
        loop.quit()
        return GLib.SOURCE_REMOVE

    # Subscribe BEFORE the call so the Response can't slip past us.
    sub = conn.signal_subscribe(
        "org.freedesktop.portal.Desktop",
        "org.freedesktop.portal.Request",
        "Response",
        req_path,
        None,
        Gio.DBusSignalFlags.NONE,
        on_response,
    )
    GLib.timeout_add_seconds(TIMEOUT_SECONDS, on_timeout)

    # Variant construction — two shapes. gi 3.56 / Python 3.14 raises
    # KeyError(0) for the historically common `GLib.Variant("(sa{sv})",
    # ("", options_variant))` form (pre-built Variant as tuple child), so
    # build the options dict INLINE (canonical, documented pattern), falling
    # back to fully-plain values (pygobject type-guessing) if the explicit
    # `v`-boxed form itself misbehaves on this stack.
    attempt_shapes = (
        ("inline-dict, v-boxed values", lambda: GLib.Variant(
            "(sa{sv})",
            ("", {
                "handle_token": GLib.Variant("s", token),
                "interactive": GLib.Variant("b", False),
            }),
        )),
        ("inline-dict, plain values", lambda: GLib.Variant(
            "(sa{sv})",
            ("", {
                "handle_token": token,
                "interactive": False,
            }),
        )),
    )
    params = None
    quirks: list[str] = []
    for name, build in attempt_shapes:
        try:
            params = build()
            if quirks:
                _note(f"variant shape '{name}' succeeded after: " + "; ".join(quirks))
            break
        except Exception as e:
            quirks.append(f"'{name}': {_describe_error(e)}")
    if params is None:
        conn.signal_unsubscribe(sub)
        print("ERR variant-build: " + "; ".join(quirks))
        return 1

    try:
        conn.call_sync(
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.Screenshot",
            "Screenshot",
            params,
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )
    except Exception as e:
        conn.signal_unsubscribe(sub)
        print(f"ERR portal-call: {_describe_error(e)}")
        return 1

    loop.run()
    conn.signal_unsubscribe(sub)

    if state["code"] is None:
        print(f"ERR wait: no portal Response signal within {TIMEOUT_SECONDS}s")
        return 1
    if state["code"] != 0:
        meaning = _RESPONSE_MEANINGS.get(state["code"], f"response {state['code']}")
        try:
            dumped = state["results"].print_(True) if state["results"] is not None else "<none>"
        except Exception:
            dumped = "<unprintable>"
        print(f"ERR response: request was {meaning} (code={state['code']}, results={dumped})")
        return 1
    if not state["uri"]:
        print("ERR response: portal reported success but returned no file URI")
        return 1
    try:
        path, _host = GLib.filename_from_uri(state["uri"])
    except Exception:
        path = state["uri"].replace("file://", "")
    print("OK " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
