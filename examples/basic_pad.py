import asyncio

from displaypad import DisplayPad


async def main():
    # Create a new DisplayPad instance
    pad = DisplayPad.DisplayPad()

    # Define event handlers
    @pad.on('down')
    def on_key_down(key_index):
        print(f"Key {key_index} has been pressed.")

    # Define event handlers
    @pad.on('up')
    def on_key_down(key_index):
        print(f"Key {key_index} has been released.")

    # Define event handlers
    @pad.on('error')
    def on_error(error):
        print(f"Error: {error}")

    # Clear all keys
    pad.clear_all_keys()

    # Set the first three keys to red, green and blue
    pad.set_key_color(0, 255, 0, 0)
    pad.set_key_color(1, 0, 255, 0)
    pad.set_key_color(2, 0, 0, 255)

    # Keep the script running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
