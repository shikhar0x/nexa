// Nexa Focused Window — GNOME Shell extension.
//
// Wayland deliberately does not let applications query which window is
// focused. The compositor (GNOME Shell) always knows, so this tiny extension
// answers on Nexa's behalf over the session D-Bus. The object is exported on
// GNOME Shell's OWN bus connection (the Shell already owns org.gnome.Shell),
// so no extra well-known name or manual register_object plumbing is needed:
//
//   gdbus call --session \
//     --dest org.gnome.Shell \
//     --object-path /org/nexa/FocusedWindow \
//     --method org.nexa.FocusedWindow.Get
//
// returns ('{"title": "...", "app": "..."}',)
//
// It does nothing else: no timers, no listeners, no UI. Read-only getter.

import Gio from 'gi://Gio';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const DBUS_IFACE = `<node>
  <interface name="org.nexa.FocusedWindow">
    <method name="Get">
      <arg type="s" name="json" direction="out"/>
    </method>
  </interface>
</node>`;

export default class NexaFocusedWindowExtension extends Extension {
    enable() {
        this._dbus = Gio.DBusExportedObject.wrapJSObject(DBUS_IFACE, this);
        this._dbus.export(Gio.DBus.session, '/org/nexa/FocusedWindow');
    }

    // Exported as org.nexa.FocusedWindow.Get() -> 's'
    Get() {
        try {
            const win = global.display.get_focus_window();
            if (win) {
                return JSON.stringify({
                    title: win.get_title() ?? '',
                    app: win.get_wm_class() ?? '',
                });
            }
        } catch (e) {
            log(`nexa-focused-window: get_focus_window failed: ${e}`);
        }
        return '{}';
    }

    disable() {
        if (this._dbus) {
            this._dbus.flush();
            this._dbus.unexport();
            this._dbus = null;
        }
    }
}
