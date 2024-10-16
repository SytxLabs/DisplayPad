import threading

import hid
from PIL import Image
from pyee import EventEmitter

NUM_KEYS = 12
NUM_KEYS_PER_ROW = 6
PACKET_SIZE = 31438
HEADER_SIZE = 306
ICON_SIZE = 102
NUM_TOTAL_PIXELS = ICON_SIZE * ICON_SIZE

VENDOR_ID = 0x3282
PRODUCT_IDS = [0x0009]

INIT_MSG_STR = (
    '00118000000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
)

IMG_MSG_STR = (
    '0021000000FF3d00006565000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
)


def is_valid_hex(s):
    try:
        bytes.fromhex(s)
        return True
    except ValueError:
        return False


try:
    INIT_MSG = bytes.fromhex(INIT_MSG_STR)
except ValueError as e:
    print(f"Fehler beim Konvertieren von INIT_MSG_STR: {e}")
    INIT_MSG = b''

try:
    IMG_MSG = bytes.fromhex(IMG_MSG_STR)
except ValueError as e:
    print(f"Fehler beim Konvertieren von IMG_MSG_STR: {e}")
    IMG_MSG = b''

NULLBYTE = bytes([0x00])


def find_device_paths(devices):
    connected_displaypads = [
        device for device in devices
        if device['vendor_id'] == VENDOR_ID and device['product_id'] in PRODUCT_IDS
    ]
    if not connected_displaypads:
        raise RuntimeError('No Displaypads are connected.')

    display_devices = [
        device for device in connected_displaypads if device.get('interface_number') == 1
    ]
    if not display_devices:
        raise RuntimeError('No Displaypad display interface found.')
    display_path = display_devices[0]['path']

    device_devices = [
        device for device in connected_displaypads if device.get('interface_number') == 3
    ]
    if not device_devices:
        raise RuntimeError('No Displaypad device interface found.')
    device_path = device_devices[0]['path']

    return {'display': display_path, 'device': device_path}


class Displaypad(EventEmitter):
    ICON_SIZE = ICON_SIZE
    NUM_KEYS = NUM_KEYS
    NUM_KEYS_PER_ROW = NUM_KEYS_PER_ROW
    VENDOR_ID = VENDOR_ID
    PRODUCT_IDS = PRODUCT_IDS
    NUM_TOTAL_PIXELS = NUM_TOTAL_PIXELS

    def __init__(self, display_handle=None, device_handle=None):
        super().__init__()
        if display_handle and device_handle:
            self.display = display_handle
            self.device = device_handle
        else:
            devices = hid.enumerate()
            paths = find_device_paths(devices)
            self.display = hid.device()
            self.display.open_path(paths['display'])
            self.device = hid.device()
            self.device.open_path(paths['device'])

        self.image_header = bytearray(HEADER_SIZE)
        self.queue = []
        self.key_state = [0] * (NUM_KEYS + 1)

        self.initializing = False
        self.lock = threading.Lock()

        self.listener_thread = threading.Thread(target=self._listen_to_device, daemon=True)
        self.listener_thread.start()

        self.reset()

    @staticmethod
    def check_rgb_value(value):
        if not (0 <= value <= 255):
            raise ValueError('Expected a valid color RGB value 0 - 255')

    @staticmethod
    def check_valid_key_index(key_index):
        if not (0 <= key_index < NUM_KEYS):
            raise ValueError(f'Expected a valid keyIndex 0 - {NUM_KEYS - 1}')

    def fill_color(self, key_index, r, g, b):
        self.check_valid_key_index(key_index)
        self.check_rgb_value(r)
        self.check_rgb_value(g)
        self.check_rgb_value(b)

        pixel = bytes([b, g, r])
        pixel_data = bytearray(pixel * (PACKET_SIZE // 3))
        self._write_pixel_data(key_index, pixel_data)

    def fill_image(self, key_index, image_buffer):
        self.check_valid_key_index(key_index)

        if len(image_buffer) != self.NUM_TOTAL_PIXELS * 3:
            raise ValueError(
                f'Expected image buffer of length {self.NUM_TOTAL_PIXELS * 3}, got length {len(image_buffer)}'
            )

        byte_buffer = bytearray(PACKET_SIZE)
        for y in range(self.ICON_SIZE):
            row_offset = self.ICON_SIZE * 3 * y
            for x in range(self.ICON_SIZE):
                offset = row_offset + 3 * x
                red = image_buffer[offset]
                green = image_buffer[offset + 1]
                blue = image_buffer[offset + 2]

                byte_buffer[offset] = blue
                byte_buffer[offset + 1] = green
                byte_buffer[offset + 2] = red

        self._write_pixel_data(key_index, byte_buffer)

    def clear_key(self, key_index):
        self.check_valid_key_index(key_index)
        self._write_pixel_data(key_index, bytearray(PACKET_SIZE))

    def clear_all_keys(self):
        empty_buffer = bytearray(PACKET_SIZE)
        for key_index in range(NUM_KEYS):
            self._write_pixel_data(key_index, empty_buffer)

    def close(self):
        self.device.close()
        self.display.close()

    def _key_is_pressed(self, key_index, key_pressed):
        state_changed = key_pressed != self.key_state[key_index]
        if state_changed:
            self.key_state[key_index] = key_pressed
            if key_pressed:
                self.emit('down', key_index)
            else:
                self.emit('up', key_index)

    def _process_data_event(self, data):
        if data[0] == 0x01:
            # Row 1
            self._key_is_pressed(1, (data[42] & 0x02) != 0)
            self._key_is_pressed(2, (data[42] & 0x04) != 0)
            self._key_is_pressed(3, (data[42] & 0x08) != 0)
            self._key_is_pressed(4, (data[42] & 0x10) != 0)
            self._key_is_pressed(5, (data[42] & 0x20) != 0)
            self._key_is_pressed(6, (data[42] & 0x40) != 0)

            # Row 2
            self._key_is_pressed(7, (data[42] & 0x80) != 0)
            self._key_is_pressed(8, (data[47] & 0x01) != 0)
            self._key_is_pressed(9, (data[47] & 0x02) != 0)
            self._key_is_pressed(10, (data[47] & 0x04) != 0)
            self._key_is_pressed(11, (data[47] & 0x08) != 0)
            self._key_is_pressed(12, (data[47] & 0x10) != 0)

        elif data[0] == 0x11:
            self.initializing = False
            if self.queue:
                self._start_pixel_transfer(self.queue[0]['key_index'])

        elif data[0] == 0x21:
            if data[1] == 0x00 and data[2] == 0x00:
                request = self.queue[0]
                combined_data = self.image_header + request['pixels']

                for i in range(0, len(combined_data), 1024):
                    chunk = combined_data[i:i + 1024]
                    self.display.write(NULLBYTE + chunk)

                self.display.write(self.image_header + request['pixels'])

            if data[1] == 0x00 and data[2] == 0xff:
                if hasattr(self, 'timeout'):
                    self.timeout.cancel()
                self.queue.pop(0)
                if self.queue:
                    self._start_pixel_transfer(self.queue[0]['key_index'])

    def _listen_to_device(self):
        while True:
            try:
                data = self.device.read(64, 100)
                if data:
                    self._process_data_event(bytes(data))
            except Exception as exception:
                self.emit('error', exception)
                break

    def reset(self):
        self.initializing = True
        self.device.write(INIT_MSG)

    def _write_pixel_data(self, key_index, pixels):
        with self.lock:
            self.queue.append({'key_index': key_index, 'pixels': pixels})
            if len(self.queue) == 1 and not self.initializing:
                self._start_pixel_transfer(key_index)

    def _start_pixel_transfer(self, key_index):
        self.timeout = threading.Timer(1.0, self.reset)
        self.timeout.start()

        data = bytearray(IMG_MSG)
        data[5] = key_index
        self.device.write(data)

    @staticmethod
    def image_buffer(image_path):
        with Image.open(image_path) as img:
            img = img.resize((ICON_SIZE, ICON_SIZE))
            img = img.convert("RGB")
            return bytearray(img.tobytes())