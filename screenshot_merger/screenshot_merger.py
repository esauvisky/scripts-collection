#!/usr/bin/env python3
import re
import shlex
import sys
import time
import argparse  # Added for command-line arguments
from threading import Thread
from PIL import Image, ImageTk
import numpy as np
import mss
from pynput import keyboard
import platform
import subprocess
from io import BytesIO
import os
from loguru import logger
import tkinter as tk  # Added for displaying images

def setup_logging(log_lvl="DEBUG", options={}):
    file = options.get("file", False)
    function = options.get("function", False)
    process = options.get("process", False)
    thread = options.get("thread", False)

    log_fmt = (u"<n><d><level>{time:HH:mm:ss.SSS} | " +
               f"{'{file:>15.15}' if file else ''}" +
               f"{'{function:>15.15}' if function else ''}" +
               f"{':{line:<4} | ' if file or function else ''}" +
               f"{'{process.name:>12.12} | ' if process else ''}" +
               f"{'{thread.name:<11.11} | ' if thread else ''}" +
               u"{level:1.1} | </level></d></n><level>{message}</level>")

    logger.configure(
        handlers=[{
            "sink": lambda x: print(x, end=""),
            "level": log_lvl,
            "format": log_fmt,
            "colorize": True,
            "backtrace": True,
            "diagnose": True
        }],
        levels=[
            {"name": "TRACE", "color": "<white><dim>"},
            {"name": "DEBUG", "color": "<cyan><dim>"},
            {"name": "INFO", "color": "<white>"}
        ]
    )  # type: ignore # yapf: disable

setup_logging("DEBUG", {"function": True, "thread": True})

# Check Operating System
OS_NAME = platform.system()

# Conditional imports based on OS
if OS_NAME == 'Windows':
    try:
        import win32clipboard  # type: ignore
    except ImportError:
        logger.error("pywin32 is not installed. Please install it using 'pip install pywin32'")
        sys.exit(1)

class RegionSelector:
    @staticmethod
    def select_region():
        if OS_NAME == 'Windows':
            return RegionSelector._select_region_windows()
        elif OS_NAME == 'Linux':
            # Verify if DISPLAY is set to ensure X11 session
            if os.environ.get('DISPLAY') is None:
                logger.error("DISPLAY environment variable not set. Ensure you are running an X11 session.")
                sys.exit(1)
            return RegionSelector._select_region_linux()
        else:
            logger.error(f"Unsupported Operating System: {OS_NAME}")
            sys.exit(1)

    @staticmethod
    def _select_region_windows():
        import tkinter as tk

        root = tk.Tk()
        root.attributes('-fullscreen', True)
        root.attributes('-alpha', 0.3)  # Transparency
        root.attributes('-topmost', True)
        root.config(cursor="cross")

        start_x = start_y = end_x = end_y = 0
        selection = None

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
            nonlocal start_x, start_y, end_x, end_y, selection
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

    @staticmethod
    def _select_region_linux():
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
            logger.error(f"Error selecting region with xrectsel: {e}")
            sys.exit(1)
        except FileNotFoundError:
            logger.error("xrectsel is not installed. Please install it using your package manager (e.g., sudo apt-get install xrectsel).")
            sys.exit(1)
        except Exception as e:
            logger.exception(f"Unexpected error during region selection: {e}")

            sys.exit(1)

class ScreenshotCapture:
    @staticmethod
    def capture_screenshot(monitor):
        with mss.mss() as sct:
            sct_img = sct.grab(monitor)
            img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
            return img

def merge_images(merged_image, new_image):
    # Try to find overlap in both directions
    overlap = _find_overlap(merged_image, new_image)
    logger.debug(f"Detected overlap: {overlap}")

    # Early return if there's no overlap
    if overlap == 0:
        logger.info("No overlap detected between images.")
        return None

    # Determine the cropping coordinates based on overlap direction
    if overlap == new_image.height or overlap == -new_image.height:
        # Full overlap
        logger.info("Fully overlapping image. Skipping.")
        return merged_image

    if overlap > 0:
        # New image overlaps at the bottom of the merged image
        crop_box_new = (0, overlap, new_image.width, new_image.height)
        paste_position = (0, merged_image.height)
        merge_direction = "below"
    else:
        # New image overlaps at the top of the merged image
        crop_box_new = (0, 0, new_image.width, new_image.height + overlap)
        paste_position = (0, new_image.height + overlap)
        merge_direction = "above"

    # Crop the overlapping part
    img_cropped = new_image.crop(crop_box_new)
    logger.debug(f"Cropped new image with box: {crop_box_new}")

    # Calculate new dimensions
    new_height = merged_image.height + img_cropped.height
    new_img = Image.new('RGB', (merged_image.width, new_height))
    logger.debug(f"Created new image with size: {new_img.size}")

    # Paste the images onto the new image
    if overlap > 0:
        new_img.paste(merged_image, (0, 0))
        new_img.paste(img_cropped, paste_position)
    else:
        new_img.paste(img_cropped, (0, 0))
        new_img.paste(merged_image, paste_position)

    logger.info(f"Merged new image {merge_direction} the existing merged image.")
    return new_img

import numpy as np

def _find_overlap(base, new):
    arr_base = np.array(base)
    arr_new = np.array(new)

    # Ensure images have the same width and number of channels
    if arr_base.shape[1] != arr_new.shape[1] or arr_base.shape[2] != arr_new.shape[2]:
        raise ValueError("Images must have the same width and number of channels for overlap detection.")

    # Positive overlap: new image is below base image
    for base_row_idx in range(arr_base.shape[0] - 1, -1, -1):
        if np.array_equal(arr_base[base_row_idx], arr_new[0]):
            match_length = 1
            # Potential overlap found, check further
            for n_idx, b_idx in enumerate(range(base_row_idx + 1, arr_base.shape[0])):
                if n_idx + 1 < arr_new.shape[0] and np.array_equal(arr_base[b_idx], arr_new[n_idx + 1]):
                    match_length += 1
                else:
                    match_length = 0
                    break
            if match_length > 0:
                return match_length  # Positive value indicating overlap length

    # Negative overlap: new image is above base image
    for base_row_idx in range(0, arr_base.shape[0]):
        if np.array_equal(arr_base[base_row_idx], arr_new[arr_new.shape[0] - 1]):
            match_length = 1
            # Potential overlap found, check further
            for n_idx, b_idx in enumerate(range(base_row_idx - 1, -1, -1)):
                if n_idx + 1 < arr_new.shape[0] and np.array_equal(arr_base[b_idx], arr_new[arr_new.shape[0] - n_idx - 2]):
                    match_length += 1
                else:
                    match_length = 0
                    break
            if match_length > 0:
                return -match_length  # Negative value indicating overlap length in a different direction

    # No overlap found
    return 0

class ClipboardManager:
    @staticmethod
    def copy_image_to_clipboard(image):
        if OS_NAME == 'Windows':
            ClipboardManager._copy_image_to_clipboard_windows(image)
        elif OS_NAME == 'Linux':
            ClipboardManager._copy_image_to_clipboard_linux(image)
        else:
            logger.error("Unsupported OS for clipboard operations.")

    @staticmethod
    def _copy_image_to_clipboard_windows(image):
        try:
            output = BytesIO()
            image.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]  # BMP file header is 14 bytes
            output.close()

            win32clipboard.OpenClipboard()  # type: ignore
            win32clipboard.EmptyClipboard()  # type: ignore
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)  # type: ignore
            win32clipboard.CloseClipboard()  # type: ignore
        except Exception as e:
            logger.exception(f"Failed to copy image to clipboard: {e}")

    @staticmethod
    def _copy_image_to_clipboard_linux(image):
        try:
            # Save image to a temporary PNG file
            temp_file_name = "/tmp/screenshot_merger.png"
            with open(temp_file_name, "wb") as temp_file:
                image.save(temp_file)
            bash_cmd = f"xclip -selection clipboard -t image/png -i {temp_file_name}"
            subprocess.run(shlex.split(bash_cmd))
        except FileNotFoundError:
            logger.error("xclip is not installed. Please install it using your package manager (e.g., sudo apt-get install xclip).")
        except Exception as e:
            logger.exception(f"Failed to copy image to clipboard: {e}")

class KeyboardListener:
    def __init__(self):
        self.screenshot_event = False
        self.exit_event = False

    def start(self):
        listener_thread = Thread(target=self._listen_keyboard, daemon=True)
        listener_thread.start()

    def _listen_keyboard(self):
        with keyboard.Listener(on_press=self._on_press) as listener:  # type: ignore
            listener.join()

    def _on_press(self, key):
        try:
            if key == keyboard.Key.enter:
                self.screenshot_event = True
            elif key == keyboard.Key.esc:
                self.exit_event = True
                return False  # Stop listener
        except AttributeError:
            pass

# Function to display images in debug mode
def display_images(new_image, merged_image):
    root = tk.Tk()
    root.title("Debug Images")

    # Create frames for layout
    frame_new = tk.Frame(root)
    frame_new.pack(side="left", padx=10, pady=10)

    frame_merged = tk.Frame(root)
    frame_merged.pack(side="right", padx=10, pady=10)

    # New Captured Image
    new_image_tk = ImageTk.PhotoImage(new_image)
    new_image_label = tk.Label(frame_new, image=new_image_tk)
    new_image_label.pack()
    new_image_title = tk.Label(frame_new, text="New Captured Image")
    new_image_title.pack()

    # Merged Image
    if merged_image is not None:
        merged_image_tk = ImageTk.PhotoImage(merged_image)
        merged_image_label = tk.Label(frame_merged, image=merged_image_tk)
        merged_image_label.pack()
        merged_image_title = tk.Label(frame_merged, text="Current Merged Image")
        merged_image_title.pack()

    # Keep a reference to the images to prevent garbage collection
    root.mainloop()

def main():
    parser = argparse.ArgumentParser(description='Screenshot merger.')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode to display images during merging.')
    args = parser.parse_args()

    debug_mode = args.debug

    logger.info("Select the region to capture.")
    region_selector = RegionSelector()
    selection = region_selector.select_region()
    if not selection:
        logger.error("No region selected. Exiting.")
        sys.exit(0)

    logger.info(f"Selected region: {selection}")

    keyboard_listener = KeyboardListener()
    keyboard_listener.start()

    logger.info("\nInstructions:\n"
                " - Press Enter to capture a screenshot of the selected region.\n"
                " - Scroll the underlying content between captures.\n"
                " - Press Escape to finish capturing and merge images.\n")

    merged_image = None
    unmerged_images = []
    screenshot_capture = ScreenshotCapture()

    while not keyboard_listener.exit_event:
        if keyboard_listener.screenshot_event:
            img = screenshot_capture.capture_screenshot(selection)
            print(f"Captured image.")
            # Try to merge the new image with the merged image
            new_merged = image_merger.merge_images(merged_image, img)
            if new_merged is not None:
                merged_image = new_merged
                print("Successfully merged with existing image.")
                # After merging, check if any unmerged images can now be merged
                unmerged_images_copy = unmerged_images.copy()
                for unmerged_img in unmerged_images_copy:
                    new_merged = image_merger.merge_images(merged_image, unmerged_img)
                    if new_merged is not None:
                        merged_image = new_merged
                        unmerged_images.remove(unmerged_img)
                        print("Merged an unmerged image.")
            else:
                # No overlap, store it for later
                unmerged_images.append(img)
                print("No overlap found. Stored for later merging.")
            keyboard_listener.screenshot_event = False
        time.sleep(0.1)  # Prevent busy waiting

    if merged_image is None:
        logger.error("No screenshots captured. Exiting.")
        sys.exit(0)

    logger.info("\nCopying merged image to clipboard...")
    clipboard_manager = ClipboardManager()
    clipboard_manager.copy_image_to_clipboard(merged_image)
    logger.info("Merged image copied to clipboard successfully.")

if __name__ == "__main__":
    main()
