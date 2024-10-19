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

    # Set the fourth key to an image
    pad.set_key_image(0, pad.get_image_buffer('icons/sl.png'))

    # Keep the script running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
