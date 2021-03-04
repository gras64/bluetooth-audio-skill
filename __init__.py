from mycroft import MycroftSkill, intent_file_handler
from mycroft.util.parse import match_one
import bluetooth

class BluetoothAudio(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
    
    def initialize(self):
        self.settings["known.device"] = self.settings.get('known.device', None)
        #self.scann_bluetooth()

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
                                            "devices": " ".join(devices.keys())})
            match, confidence = match_one(device, list(devices.keys()))
            self.settings["known.device"] = devices.get(match)   
        else:
            self.speak_dialog("no.device")
            return
        self.log.info("set standard Bluetooth Device to "+str(device))

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
            


def create_skill():
    return BluetoothAudio()

