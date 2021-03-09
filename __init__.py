from mycroft import MycroftSkill, intent_file_handler
from mycroft.util.parse import match_one
import bluetooth
import subprocess
import pexpect
import time
import sys
import logging


class BluetoothAudio(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
    
    def initialize(self):
        self.bl = Bluetoothctl()
        self.settings["known.device"] = self.settings.get('known.device', None)
        if not self.settings["known.device"] is None:
            self.pair_device(self.settings["known.device"])
            self.connect_device(self.settings["known.device"])

    @intent_file_handler('audio.bluetooth.intent')
    def handle_audio_bluetooth(self, message):
        devices = self.scann_bluetooth()
        if len(devices) == 1:
            if self.ask_yesno("found.one.device", data={"device": "".join(devices.keys())}) != "yes":
                return
            self.settings["known.device"] = list(devices.values())[0]
        elif len(devices) > 1:
            device = self.get_response('audio.bluetooth', 
                                        data={"number": str(len(devices)),
                                            "devices": list(devices.keys())})
            match, confidence = match_one(device, list(devices.keys()))
            self.settings["known.device"] = devices.get(match)
        else:
            self.speak_dialog("no.device")
            return
        self.log.info("set standard Bluetooth Device to "+str(self.settings["known.device"]))
        self.pair_device(self.settings["known.device"])

    def scann_bluetooth(self):
        self.log.info("Performing inquiry...")

        nearby_devices = bluetooth.discover_devices(duration=8, lookup_names=True,
                                                    flush_cache=True, lookup_class=False)

        self.log.info("Found {} devices".format(len(nearby_devices)))

        devices = {}
        for addr, name in nearby_devices:
            try:
                self.log.info("   {} - {}".format(addr, name))
            except UnicodeEncodeError:
                name = name.encode("utf-8", "replace")
                self.log.info("   {} - {}".format(addr, name))
            devices.update({name:addr})
        self.log.info("devices: "+str(devices))
        return devices

    def pair_device(self, mac):
        self.bl.pair(mac)
        self.log.info("paird "+str(mac))

    def connect_device(self, mac):
        self.bl.connect(mac)
        self.log.info("connect "+str(mac))


def create_skill():
    return BluetoothAudio()

logger = logging.getLogger("btctl")

class Bluetoothctl:
    """A wrapper for bluetoothctl utility."""

    def __init__(self):
        subprocess.check_output("rfkill unblock bluetooth", shell=True)
        self.process = pexpect.spawnu("bluetoothctl", echo=False)

    def send(self, command, pause=0):
        self.process.send(f"{command}\n")
        time.sleep(pause)
        if self.process.expect(["bluetooth", pexpect.EOF]):
            raise Exception(f"failed after {command}")

    def get_output(self, *args, **kwargs):
        """Run a command in bluetoothctl prompt, return output as a list of lines."""
        self.send(*args, **kwargs)
        return self.process.before.split("\r\n")

    def start_scan(self):
        """Start bluetooth scanning process."""
        try:
            self.send("scan on")
        except Exception as e:
            logger.error(e)

    def make_discoverable(self):
        """Make device discoverable."""
        try:
            self.send("discoverable on")
        except Exception as e:
            logger.error(e)

    def parse_device_info(self, info_string):
        """Parse a string corresponding to a device."""
        device = {}
        block_list = ["[\x1b[0;", "removed"]
        if not any(keyword in info_string for keyword in block_list):
            try:
                device_position = info_string.index("Device")
            except ValueError:
                pass
            else:
                if device_position > -1:
                    attribute_list = info_string[device_position:].split(" ", 2)
                    device = {
                        "mac_address": attribute_list[1],
                        "name": attribute_list[2],
                    }
        return device

    def get_available_devices(self):
        """Return a list of tuples of paired and discoverable devices."""
        available_devices = []
        try:
            out = self.get_output("devices")
        except Exception as e:
            logger.error(e)
        else:
            for line in out:
                device = self.parse_device_info(line)
                if device:
                    available_devices.append(device)
        return available_devices

    def get_paired_devices(self):
        """Return a list of tuples of paired devices."""
        paired_devices = []
        try:
            out = self.get_output("paired-devices")
        except Exception as e:
            logger.error(e)
        else:
            for line in out:
                device = self.parse_device_info(line)
                if device:
                    paired_devices.append(device)
        return paired_devices

    def get_discoverable_devices(self):
        """Filter paired devices out of available."""
        available = self.get_available_devices()
        paired = self.get_paired_devices()
        return [d for d in available if d not in paired]

    def get_device_info(self, mac_address):
        """Get device info by mac address."""
        try:
            out = self.get_output(f"info {mac_address}")
        except Exception as e:
            logger.error(e)
            return False
        else:
            return out

    def pair(self, mac_address):
        """Try to pair with a device by mac address."""
        try:
            self.send(f"pair {mac_address}", 4)
        except Exception as e:
            logger.error(e)
            return False
        else:
            res = self.process.expect(
                ["Failed to pair", "Pairing successful", pexpect.EOF]
            )
            return res == 1

    def trust(self, mac_address):
        try:
            self.send(f"trust {mac_address}", 4)
        except Exception as e:
            logger.error(e)
            return False
        else:
            res = self.process.expect(
                ["Failed to trust", "Pairing successful", pexpect.EOF]
            )
            return res == 1

    def remove(self, mac_address):
        """Remove paired device by mac address, return success of the operation."""
        try:
            self.send(f"remove {mac_address}", 3)
        except Exception as e:
            logger.error(e)
            return False
        else:
            res = self.process.expect(
                ["not available", "Device has been removed", pexpect.EOF]
            )
            return res == 1

    def connect(self, mac_address):
        """Try to connect to a device by mac address."""
        try:
            self.send(f"connect {mac_address}", 2)
        except Exception as e:
            logger.error(e)
            return False
        else:
            res = self.process.expect(
                ["Failed to connect", "Connection successful", pexpect.EOF]
            )
            return res == 1

    def disconnect(self, mac_address):
        """Try to disconnect to a device by mac address."""
        try:
            self.send(f"disconnect {mac_address}", 2)
        except Exception as e:
            logger.error(e)
            return False
        else:
            res = self.process.expect(
                ["Failed to disconnect", "Successful disconnected", pexpect.EOF]
            )
            return res == 1