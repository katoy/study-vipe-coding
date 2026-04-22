from PIL import Image

try:
    with Image.open("app/static/calculator_demo.webp") as im:
        frames = []
        try:
            while True:
                frames.append(im.copy())
                im.seek(len(frames))
        except EOFError:
            pass

        print(f"Frames extracted: {len(frames)}")
        if frames:
            frames[0].save(
                "app/static/calculator_demo.gif", save_all=True, append_images=frames[1:], loop=0
            )
            print("GIF saved successfully.")
        else:
            print("No frames found.")
except Exception as e:
    print(f"Error: {e}")
