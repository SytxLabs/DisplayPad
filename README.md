# Example

```python
import time

from DisplayPad import DisplayPad

def main():
    pad = DisplayPad.DisplayPad()

    @pad.on('down')
    def on_key_down(key_index):
        print(f"Key {key_index} has been pressed.")

    @pad.on('error')
    def on_error(error):
        print(f"Error: {error}")

    pad.clear_all_keys()

    pad.set_key_color(0, 255, 0, 0)
    pad.set_key_color(1, 0, 255, 0)
    pad.set_key_color(2, 0, 0, 255)

    image = bytearray(pad.ICON_SIZE * pad.ICON_SIZE * 3)
    for i in range(pad.ICON_SIZE * pad.ICON_SIZE):
        image[i * 3] = 0xff
        image[i * 3 + 1] = 0x00
        image[i * 3 + 2] = 0x00
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()


```