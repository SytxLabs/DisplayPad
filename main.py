from mountain import Displaypad, ICON_SIZE
import time

def main():
    try:
        pad = Displaypad()

        @pad.on('down')
        def on_key_down(key_index):
            print(f"Key {key_index} has been pressed.")

        @pad.on('up')
        def on_key_up(key_index):
            print(f"Key {key_index} has been released.")

        @pad.on('error')
        def on_error(error):
            print(f"Error: {error}")

        pad.clear_all_keys()

        pad.fill_color(0, 255, 0, 0)
        pad.fill_color(1, 0, 255, 0)
        pad.fill_color(2, 0, 0, 255)
        pad.fill_color(3, 0, 0, 255)
        pad.fill_color(4, 0, 0, 255)
        pad.fill_color(5, 0, 0, 255)
        pad.fill_color(6, 0, 0, 255)
        pad.fill_color(7, 0, 0, 255)
        pad.fill_color(8, 0, 0, 255)
        pad.fill_color(9, 0, 0, 255)
        pad.fill_color(10, 0, 0, 255)
        pad.fill_color(11, 0, 0, 255)

        image = bytearray(ICON_SIZE * ICON_SIZE * 3)
        for i in range(ICON_SIZE * ICON_SIZE):
            image[i * 3] = 0xff
            image[i * 3 + 1] = 0x00
            image[i * 3 + 2] = 0x00
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("Programm has been interrupted.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        pad.close()
        print("Programm has been closed.")

if __name__ == "__main__":
    main()
