from mycroft import MycroftSkill, intent_file_handler


class BluetoothAudio(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('audio.bluetooth.intent')
    def handle_audio_bluetooth(self, message):
        self.speak_dialog('audio.bluetooth')


def create_skill():
    return BluetoothAudio()

