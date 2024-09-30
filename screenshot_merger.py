#!/usr/bin/env python3
import re
import sys
from tempfile import TemporaryFile, mkstemp, mktemp
import time
from threading import Thread
from PIL import Image
import numpy as np
import mss
import mss.tools
from pynput import keyboard
import platform
import subprocess
from io import BytesIO
import os

# Check Operating System
OS_NAME = platform.system()

# Conditional imports based on OS
if OS_NAME == 'Windows':
    try:
        import win32clipboard # type: ignore
    except ImportError:
        print("pywin32 is not installed. Please install it using 'pip install pywin32'")
        sys.exit(1)

# Global variables to store selection and control flags
selection = None
captured_images = []
screenshot_event = False
exit_event = False

def select_region_windows():
    """
    Allows the user to select a screen region using a fullscreen transparent Tkinter window on Windows.
    Returns the selected region as a dictionary compatible with mss.
    """
    import tkinter as tk

    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-alpha', 0.3)  # Transparency
    root.attributes('-topmost', True)
    root.config(cursor="cross")

    start_x = start_y = end_x = end_y = 0

    # Create a canvas to draw the selection rectangle
    canvas = tk.Canvas(root, cursor="cross", bg="grey")
    canvas.pack(fill=tk.BOTH, expand=True)

    def on_mouse_down(event):
        nonlocal start_x, start_y
        start_x, start_y = event.x, event.y
        canvas.delete("sel_rect")
        canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2, tags="sel_rect")

    def on_mouse_move(event):
        nonlocal start_x, start_y, end_x, end_y
        end_x, end_y = event.x, event.y
        canvas.coords("sel_rect", start_x, start_y, end_x, end_y)

    def on_mouse_up(event):
        nonlocal start_x, start_y, end_x, end_y
        global selection
        end_x, end_y = event.x, event.y
        root.destroy()
        x = min(start_x, end_x)
        y = min(start_y, end_y)
        w = abs(end_x - start_x)
        h = abs(end_y - start_y)
        selection = {'top': y, 'left': x, 'width': w, 'height': h}

    # Bind mouse events
    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_move)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)

    root.mainloop()
    return selection

def select_region_linux():
    """
    Allows the user to select a screen region using xrectsel on Linux (GNOME/X11).
    Returns the selected region as a dictionary compatible with mss.
    """
    try:
        # Run xrectsel and capture the output
        # xrectsel returns geometry in format: x,y,width,height
        result = subprocess.run(['xrectsel'], capture_output=True, text=True, check=True)
        geometry = result.stdout.strip()
        if not geometry:
            raise ValueError("No geometry received from xrectsel.")
        w, h, l, t = tuple(map(int, re.findall(r'\d+', geometry)))
        selection = {'left': l, 'top': t, 'width': w, 'height': h}
        return selection
    except subprocess.CalledProcessError as e:
        print(f"Error selecting region with xrectsel: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("xrectsel is not installed. Please install it using your package manager (e.g., sudo apt-get install xrectsel).")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error during region selection: {e}")
        sys.exit(1)

def select_region():
    """
    Selects the screen region based on the operating system.
    """
    if OS_NAME == 'Windows':
        return select_region_windows()
    elif OS_NAME == 'Linux':
        # Verify if DISPLAY is set to ensure X11 session
        if os.environ.get('DISPLAY') is None:
            print("DISPLAY environment variable not set. Ensure you are running an X11 session.")
            sys.exit(1)
        return select_region_linux()
    else:
        print(f"Unsupported Operating System: {OS_NAME}")
        sys.exit(1)

def on_press(key):
    """
    Keyboard listener callback.
    Sets flags based on key presses.
    """
    global screenshot_event, exit_event
    try:
        if key == keyboard.Key.enter:
            screenshot_event = True
        elif key == keyboard.Key.esc:
            exit_event = True
            return False  # Stop listener
    except AttributeError:
        pass

def listen_keyboard():
    """
    Starts a keyboard listener in a separate thread.
    """
    with keyboard.Listener(on_press=on_press) as listener: # type: ignore
        listener.join()

def capture_screenshot(monitor):
    """
    Captures a screenshot of the specified monitor region.
    """
    with mss.mss() as sct:
        sct_img = sct.grab(monitor)
        img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
        return img

def find_overlap(img1, img2, max_overlap=100):
    """
    Finds the number of overlapping rows between the bottom of img1 and the top of img2.
    Returns the number of overlapping rows.
    """
    arr1 = np.array(img1)
    arr2 = np.array(img2)

    # Ensure images have the same width and number of channels
    if arr1.shape[1] != arr2.shape[1] or arr1.shape[2] != arr2.shape[2]:
        raise ValueError("Images must have the same width and number of channels for overlap detection.")

    # Limit the maximum possible overlap
    max_possible = min(max_overlap, arr1.shape[0], arr2.shape[0])

    overlap = 0
    for i in range(1, max_possible + 1):
        if np.array_equal(arr1[-i:], arr2[:i]):
            overlap = i
    return overlap

def merge_images(images):
    """
    Merges a list of PIL Images vertically, handling overlapping regions.
    Returns the merged PIL Image.
    """
    if not images:
        return None

    merged = images[0]
    for img in images[1:]:
        overlap = find_overlap(merged, img)
        if overlap > 0:
            # Crop the new image to remove the overlapping part
            img_cropped = img.crop((0, overlap, img.width, img.height))
        else:
            img_cropped = img
        # Create a new image with combined height
        new_height = merged.height + img_cropped.height
        new_img = Image.new('RGB', (merged.width, new_height))
        new_img.paste(merged, (0, 0))
        new_img.paste(img_cropped, (0, merged.height))
        merged = new_img
    return merged

def copy_image_to_clipboard(image):
    """
    Copies a PIL Image to the clipboard.
    Supports both Windows and Linux (GNOME/X11).
    """
    if OS_NAME == 'Windows':
        try:
            output = BytesIO()
            image.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]  # BMP file header is 14 bytes
            output.close()

            win32clipboard.OpenClipboard() # type: ignore
            win32clipboard.EmptyClipboard() # type: ignore
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data) # type: ignore
            win32clipboard.CloseClipboard() # type: ignore
        except Exception as e:
            print(f"Failed to copy image to clipboard: {e}")
    elif OS_NAME == 'Linux':
        try:
            # Save image to a temporary PNG file
            temp_file_name = "/tmp/screenshot_merger.png"
            with open(temp_file_name, "wb") as temp_file:
                image.save(temp_file, format="PNG")
                bash_cmd = f"xclip -selection clipboard -t image/png -i {temp_file_name}"
                p = subprocess.Popen(bash_cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p.communicate(temp_file.read())
        except FileNotFoundError:
            print("xclip is not installed. Please install it using your package manager (e.g., sudo apt-get install xclip).")
        except Exception as e:
            print(f"Failed to copy image to clipboard: {e}")
    else:
        print("Unsupported OS for clipboard operations.")

def main():
    global selection, captured_images, screenshot_event, exit_event

    print("Select the region to capture.")
    selection = select_region()
    if not selection:
        print("No region selected. Exiting.")
        sys.exit(0)

    print(f"Selected region: {selection}")

    # Start keyboard listener in a separate thread
    listener_thread = Thread(target=listen_keyboard, daemon=True)
    listener_thread.start()

    print("\nInstructions:")
    print(" - Press Enter to capture a screenshot of the selected region.")
    print(" - Scroll the underlying content between captures.")
    print(" - Press Escape to finish capturing and merge images.\n")

    while not exit_event:
        if screenshot_event:
            img = capture_screenshot(selection)
            captured_images.append(img)
            print(f"Captured image {len(captured_images)}")
            screenshot_event = False
        time.sleep(0.1)  # Prevent busy waiting

    if not captured_images:
        print("No screenshots captured. Exiting.")
        sys.exit(0)

    print("\nMerging images...")
    try:
        merged_image = merge_images(captured_images)
    except ValueError as ve:
        print(f"Error during merging: {ve}")
        sys.exit(1)

    if merged_image:
        print("Copying merged image to clipboard...")
        copy_image_to_clipboard(merged_image)
        print("Merged image copied to clipboard successfully.")
    else:
        print("No images to merge.")

if __name__ == "__main__":
    main()
