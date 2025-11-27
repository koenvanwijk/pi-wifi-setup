"""Minimal BLE GATT server for Wi-Fi provisioning.

This uses the BlueZ D-Bus GATT API. It is intentionally simplified and
based on common BlueZ Python examples. You must run it with the
Bluetooth daemon configured for experimental features, e.g.:

  sudo bluetoothd --experimental

and often as root (so it can access D-Bus system bus and nmcli).
"""

import dbus
import dbus.mainloop.glib
import dbus.service
import json
import sys
from gi.repository import GLib

from wifi_helper import scan_wifi, apply_wifi


BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
ADAPTER_IFACE = 'org.bluez.Adapter1'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'

SERVICE_UUID = '12345678-1234-5678-1234-56789abcdef0'
SSID_UUID    = '12345678-1234-5678-1234-56789abcdef1'
PASS_UUID    = '12345678-1234-5678-1234-56789abcdef2'
CMD_UUID     = '12345678-1234-5678-1234-56789abcdef3'
STATUS_UUID  = '12345678-1234-5678-1234-56789abcdef4'
NETS_UUID    = '12345678-1234-5678-1234-56789abcdef5'


def str_to_bytes(s: str) -> bytes:
    return s.encode('utf-8')


def bytes_to_str(b: bytes) -> str:
    try:
        return b.decode('utf-8')
    except Exception:
        return ''


class Application(dbus.service.Object):
    PATH_BASE = '/org/example/wifiprov'

    def __init__(self, bus):
        self.path = self.PATH_BASE
        self.bus = bus
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(WifiProvService(bus, 0))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method('org.freedesktop.DBus.ObjectManager',
                         out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
        return response


class WifiProvService(dbus.service.Object):
    def __init__(self, bus, index):
        self.path = f'{Application.PATH_BASE}/service{index}'
        self.bus = bus
        self.uuid = SERVICE_UUID
        self.primary = True
        self.characteristics = []

        dbus.service.Object.__init__(self, bus, self.path)

        self.status_chrc = StatusCharacteristic(bus, 0, self)
        self.networks_chrc = NetworksCharacteristic(bus, 1, self)
        self.ssid_chrc = SSIDCharacteristic(bus, 2, self)
        self.pass_chrc = PassCharacteristic(bus, 3, self)
        self.cmd_chrc = CMDCharacteristic(bus, 4, self)

        self.characteristics = [
            self.status_chrc,
            self.networks_chrc,
            self.ssid_chrc,
            self.pass_chrc,
            self.cmd_chrc,
        ]

        self.current_ssid = ''
        self.current_pass = ''

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array(
                    [chrc.get_path() for chrc in self.characteristics],
                    signature='o'
                ),
            }
        }

    def get_characteristics(self):
        return self.characteristics

    def set_credentials(self, ssid: str, password: str):
        self.current_ssid = ssid
        self.current_pass = password

    def do_scan(self):
        self.status_chrc.set_status('SCANNING')
        nets = scan_wifi()
        payload = json.dumps(nets)
        self.networks_chrc.set_networks(payload)
        self.status_chrc.set_status('IDLE')

    def do_apply(self):
        if not self.current_ssid:
            self.status_chrc.set_status('FAIL:SSID empty')
            return
        self.status_chrc.set_status('CONNECTING')
        ok, msg = apply_wifi(self.current_ssid, self.current_pass)
        if ok:
            self.status_chrc.set_status('SUCCESS')
        else:
            self.status_chrc.set_status(f'FAIL:{msg}')


class Characteristic(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags, service):
        self.path = f'{service.get_path()}/char{index}'
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'UUID': self.uuid,
                'Service': self.service.get_path(),
                'Flags': dbus.Array(self.flags, signature='s'),
            }
        }

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='a{sv}',
                         out_signature='ay')
    def ReadValue(self, options):
        return dbus.Array([], signature='y')

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='aya{sv}')
    def WriteValue(self, value, options):
        pass

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        pass

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        pass


class StatusCharacteristic(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, STATUS_UUID, ['read', 'notify'], service)
        self.value = str_to_bytes('IDLE')
        self.notifying = False

    def set_status(self, text: str):
        self.value = str_to_bytes(text)
        if self.notifying:
            self.PropertiesChanged(GATT_CHRC_IFACE,
                                   {'Value': dbus.Array(self.value, signature='y')},
                                   [])

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='a{sv}',
                         out_signature='ay')
    def ReadValue(self, options):
        return dbus.Array(self.value, signature='y')

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        self.notifying = True

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        self.notifying = False

    @dbus.service.signal(dbus.PROPERTIES_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


class NetworksCharacteristic(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, NETS_UUID, ['read', 'notify'], service)
        self.value = str_to_bytes('[]')
        self.notifying = False

    def set_networks(self, json_text: str):
        self.value = str_to_bytes(json_text)
        if self.notifying:
            self.PropertiesChanged(GATT_CHRC_IFACE,
                                   {'Value': dbus.Array(self.value, signature='y')},
                                   [])

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='a{sv}',
                         out_signature='ay')
    def ReadValue(self, options):
        return dbus.Array(self.value, signature='y')

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        self.notifying = True

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        self.notifying = False

    @dbus.service.signal(dbus.PROPERTIES_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


class SSIDCharacteristic(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, SSID_UUID, ['write'], service)

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='aya{sv}')
    def WriteValue(self, value, options):
        ssid = bytes_to_str(bytes(value))
        self.service.set_credentials(ssid, self.service.current_pass)


class PassCharacteristic(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, PASS_UUID, ['write'], service)

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='aya{sv}')
    def WriteValue(self, value, options):
        password = bytes_to_str(bytes(value))
        self.service.set_credentials(self.service.current_ssid, password)


class CMDCharacteristic(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, CMD_UUID, ['write'], service)

    @dbus.service.method(GATT_CHRC_IFACE,
                         in_signature='aya{sv}')
    def WriteValue(self, value, options):
        cmd = bytes_to_str(bytes(value)).strip().upper()
        if cmd == 'SCAN':
            self.service.do_scan()
        elif cmd == 'APPLY':
            self.service.do_apply()


def find_adapter(bus):
    obj = bus.get_object(BLUEZ_SERVICE_NAME, '/')
    mgr = dbus.Interface(obj, 'org.freedesktop.DBus.ObjectManager')
    objects = mgr.GetManagedObjects()
    for path, ifaces in objects.items():
        if ADAPTER_IFACE in ifaces:
            return path
    return None


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    adapter_path = find_adapter(bus)
    if not adapter_path:
        print('Bluetooth adapter not found')
        sys.exit(1)

    service_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        GATT_MANAGER_IFACE
    )

    app = Application(bus)
    mainloop = GLib.MainLoop()

    print('Registering GATT application...')
    service_manager.RegisterApplication(
        app.get_path(), {},
        reply_handler=lambda: print('GATT application registered'),
        error_handler=lambda e: (print('Failed to register application', e), mainloop.quit()),
    )

    try:
        mainloop.run()
    except KeyboardInterrupt:
        print('Exiting')


if __name__ == '__main__':
    main()
