import threading

import hid
from pyee import EventEmitter


class DisplayPad(EventEmitter):
    ICON_SIZE = 102
    NUM_KEYS = 12
    NUM_KEYS_PER_ROW = 6
    PACKET_SIZE = 31438
    HEADER_SIZE = 306
    NUM_TOTAL_PIXELS = ICON_SIZE * ICON_SIZE

    VENDOR_ID = 0x3282
    PRODUCT_IDS = [0x0009]

    INIT_MSG_STR = (
        '00118000000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    )
    IMG_MSG_STR = (
        '0021000000FF3d00006565000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
    )

    NULLBYTE = bytes([0x00])

    def __init__(self, display_handle=None, device_handle=None):
        super().__init__()

        try:
            self.INIT_MSG = bytes.fromhex(self.INIT_MSG_STR)
        except ValueError as e:
            print(f"Error converting INIT_MSG_STR: {e}")
            self.INIT_MSG = b''

        try:
            self.IMG_MSG = bytes.fromhex(self.IMG_MSG_STR)
        except ValueError as e:
            print(f"Error converting IMG_MSG_STR: {e}")
            self.IMG_MSG = b''

        if display_handle and device_handle:
            self.display = display_handle
            self.device = device_handle
        else:
            devices = hid.enumerate()
            paths = self._get_device_paths(devices)
            self.display = hid.device()
            self.display.open_path(paths['display'])
            self.device = hid.device()
            self.device.open_path(paths['device'])

        self.image_header = bytearray(self.HEADER_SIZE)
        self.queue = []
        self.key_state = [0] * (self.NUM_KEYS + 1)

        self.initializing = False
        self.lock = threading.Lock()

        self.listener_thread = threading.Thread(target=self._device_listener, daemon=True)
        self.listener_thread.start()

        self.reset_device()

    def _get_device_paths(self, devices):
        connected_displaypads = [
            device for device in devices
            if device['vendor_id'] == self.VENDOR_ID and device['product_id'] in self.PRODUCT_IDS
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

    @staticmethod
    def _validate_rgb_value(value):
        if not (0 <= value <= 255):
            raise ValueError('Expected a valid color RGB value 0 - 255')

    def _validate_key_index(self, key_index):
        if not (0 <= key_index < self.NUM_KEYS):
            raise ValueError(f'Expected a valid keyIndex 0 - {self.NUM_KEYS - 1}')

    def set_key_color(self, key_index, r, g, b):
        self._validate_key_index(key_index)
        self._validate_rgb_value(r)
        self._validate_rgb_value(g)
        self._validate_rgb_value(b)

        pixel = bytes([b, g, r])
        pixel_data = bytearray(pixel * (self.PACKET_SIZE // 3))
        self._send_pixel_data(key_index, pixel_data)

    def set_key_image(self, key_index, image_buffer):
        self._validate_key_index(key_index)

        if len(image_buffer) != self.NUM_TOTAL_PIXELS * 3:
            raise ValueError(
                f'Expected image buffer of length {self.NUM_TOTAL_PIXELS * 3}, got length {len(image_buffer)}'
            )

        byte_buffer = bytearray(self.PACKET_SIZE)
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

        self._send_pixel_data(key_index, byte_buffer)

    def clear_key(self, key_index):
        self._validate_key_index(key_index)
        self._send_pixel_data(key_index, bytearray(self.PACKET_SIZE))

    def clear_all_keys(self):
        empty_buffer = bytearray(self.PACKET_SIZE)
        for key_index in range(self.NUM_KEYS):
            self._send_pixel_data(key_index, empty_buffer)

    def close_device(self):
        self.device.close()
        self.display.close()

    def _handle_key_press(self, key_index, key_pressed):
        state_changed = key_pressed != self.key_state[key_index]
        if state_changed:
            self.key_state[key_index] = key_pressed
            if key_pressed:
                self.emit('down', key_index)
            else:
                self.emit('up', key_index)

    def _process_device_event(self, data):
        if data[0] == 0x01:
            # Row 1
            self._handle_key_press(1, (data[42] & 0x02) != 0)
            self._handle_key_press(2, (data[42] & 0x04) != 0)
            self._handle_key_press(3, (data[42] & 0x08) != 0)
            self._handle_key_press(4, (data[42] & 0x10) != 0)
            self._handle_key_press(5, (data[42] & 0x20) != 0)
            self._handle_key_press(6, (data[42] & 0x40) != 0)

            # Row 2
            self._handle_key_press(7, (data[42] & 0x80) != 0)
            self._handle_key_press(8, (data[47] & 0x01) != 0)
            self._handle_key_press(9, (data[47] & 0x02) != 0)
            self._handle_key_press(10, (data[47] & 0x04) != 0)
            self._handle_key_press(11, (data[47] & 0x08) != 0)
            self._handle_key_press(12, (data[47] & 0x10) != 0)

        elif data[0] == 0x11:
            self.initializing = False
            if self.queue:
                self._initiate_pixel_transfer(self.queue[0]['key_index'])

        elif data[0] == 0x21:
            if data[1] == 0x00 and data[2] == 0x00:
                request = self.queue[0]
                combined_data = self.image_header + request['pixels']

                for i in range(0, len(combined_data), 1024):
                    chunk = combined_data[i:i + 1024]
                    self.display.write(self.NULLBYTE + chunk)

                self.display.write(self.image_header + request['pixels'])

            if data[1] == 0x00 and data[2] == 0xff:
                if hasattr(self, 'timeout'):
                    self.timeout.cancel()
                self.queue.pop(0)
                if self.queue:
                    self._initiate_pixel_transfer(self.queue[0]['key_index'])

    def _device_listener(self):
        while True:
            try:
                data = self.device.read(64, 100)
                if data:
                    self._process_device_event(bytes(data))
            except Exception as exception:
                self.emit('error', exception)
                break

    def reset_device(self):
        self.initializing = True
        self.device.write(self.INIT_MSG)

    def _send_pixel_data(self, key_index, pixels):
        with self.lock:
            self.queue.append({'key_index': key_index, 'pixels': pixels})
            if len(self.queue) == 1 and not self.initializing:
                self._initiate_pixel_transfer(key_index)

    def _initiate_pixel_transfer(self, key_index):
        self.timeout = threading.Timer(1.0, self.reset_device)
        self.timeout.start()

        data = bytearray(self.IMG_MSG)
        data[5] = key_index
        self.device.write(data)

    def get_image_buffer(self, img):
        img = img.resize((self.ICON_SIZE, self.ICON_SIZE))
        img = img.convert("RGB")
        return bytearray(img.tobytes())
