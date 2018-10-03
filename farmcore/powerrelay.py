from usbrelay import USBRelay


# TODO: Make this not Paladin specific
class PowerRelay(USBRelay):
    def __init__(self, usb_device):
        USBRelay.__init__(usb_device)

    def on(self):
            self.toggle(1, 'A')
            self.toggle(2, 'B')
            time.sleep(0.1)

            self.toggle(2, 'A')
            time.sleep(0.1)
            self.toggle(2, 'B')

    def off(self)
            self.toggle(1, 'B')
            self.toggle(2, 'B')