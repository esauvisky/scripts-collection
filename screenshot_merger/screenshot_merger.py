#!/usr/bin/env python3
import re
import sys
import time
from threading import Thread
from PIL import Image
import numpy as np
import mss
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
        import win32clipboard  # type: ignore
    except ImportError:
        print("pywin32 is not installed. Please install it using 'pip install pywin32'")
        sys.exit(1)

class RegionSelector:
    @staticmethod
    def select_region():
        if OS_NAME == 'Windows':
            return RegionSelector._select_region_windows()
        elif OS_NAME == 'Linux':
            # Verify if DISPLAY is set to ensure X11 session
            if os.environ.get('DISPLAY') is None:
                print("DISPLAY environment variable not set. Ensure you are running an X11 session.")
                sys.exit(1)
            return RegionSelector._select_region_linux()
        else:
            print(f"Unsupported Operating System: {OS_NAME}")
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
            print(f"Error selecting region with xrectsel: {e}")
            sys.exit(1)
        except FileNotFoundError:
            print("xrectsel is not installed. Please install it using your package manager (e.g., sudo apt-get install xrectsel).")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error during region selection: {e}")
            sys.exit(1)

class ScreenshotCapture:
    @staticmethod
    def capture_screenshot(monitor):
        with mss.mss() as sct:
            sct_img = sct.grab(monitor)
            img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
            return img

class ImageMerger:
    @staticmethod
    def merge_images(merged_image, new_image):
        if merged_image is None:
            return new_image

        # Try to find overlap in both directions
        overlap_down = ImageMerger._find_overlap(merged_image, new_image)
        overlap_up = ImageMerger._find_overlap(new_image, merged_image)

        # Check if the images are entirely overlapping
        if ImageMerger._is_entirely_overlapping(merged_image, new_image):
            print("New screenshot entirely overlaps with the merged image. Ignoring it.")
            return merged_image

        if overlap_down > 0:
            # Merge new_image below merged_image
            img_cropped = new_image.crop((0, overlap_down, new_image.width, new_image.height))
            new_height = merged_image.height + img_cropped.height
            new_img = Image.new('RGB', (merged_image.width, new_height))
            new_img.paste(merged_image, (0, 0))
            new_img.paste(img_cropped, (0, merged_image.height))
            return new_img
        elif overlap_up > 0:
            # Merge new_image above merged_image
            img_cropped = new_image.crop((0, 0, new_image.width, new_image.height - overlap_up))
            new_height = img_cropped.height + merged_image.height
            new_img = Image.new('RGB', (merged_image.width, new_height))
            new_img.paste(img_cropped, (0, 0))
            new_img.paste(merged_image, (0, img_cropped.height))
            return new_img
        else:
            # No overlap
            return None

    @staticmethod
    def _find_overlap(img1, img2):
        arr1 = np.array(img1)
        arr2 = np.array(img2)

        # Ensure images have the same width and number of channels
        if arr1.shape[1] != arr2.shape[1] or arr1.shape[2] != arr2.shape[2]:
            raise ValueError("Images must have the same width and number of channels for overlap detection.")

        max_possible = min(arr1.shape[0], arr2.shape[0])

        # Check for overlap from bottom of img1 to top of img2
        for i in range(1, max_possible + 1):
            if np.array_equal(arr1[-i:], arr2[:i]):
                return i

        return 0

    @staticmethod
    def _is_entirely_overlapping(img1, img2):
        arr1 = np.array(img1)
        arr2 = np.array(img2)

        if arr1.shape != arr2.shape:
            return False

        return np.array_equal(arr1, arr2)

class ClipboardManager:
    @staticmethod
    def copy_image_to_clipboard(image):
        if OS_NAME == 'Windows':
            ClipboardManager._copy_image_to_clipboard_windows(image)
        elif OS_NAME == 'Linux':
            ClipboardManager._copy_image_to_clipboard_linux(image)
        else:
            print("Unsupported OS for clipboard operations.")

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
            print(f"Failed to copy image to clipboard: {e}")

    @staticmethod
    def _copy_image_to_clipboard_linux(image):
        try:
            # Save image to a temporary PNG file
            temp_file_name = "/tmp/screenshot_merger.png"
            with open(temp_file_name, "wb") as temp_file:
                image.save(temp_file, format="PNG")
            bash_cmd = f"xclip -selection clipboard -t image/png -i {temp_file_name}"
            subprocess.run(bash_cmd, shell=True)
        except FileNotFoundError:
            print("xclip is not installed. Please install it using your package manager (e.g., sudo apt-get install xclip).")
        except Exception as e:
            print(f"Failed to copy image to clipboard: {e}")

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

def main():
    print("Select the region to capture.")
    region_selector = RegionSelector()
    selection = region_selector.select_region()
    if not selection:
        print("No region selected. Exiting.")
        sys.exit(0)

    print(f"Selected region: {selection}")

    keyboard_listener = KeyboardListener()
    keyboard_listener.start()

    print("\nInstructions:")
    print(" - Press Enter to capture a screenshot of the selected region.")
    print(" - Scroll the underlying content between captures.")
    print(" - Press Escape to finish capturing and merge images.\n")

    merged_image = None
    unmerged_images = []
    image_merger = ImageMerger()
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
        print("No screenshots captured. Exiting.")
        sys.exit(0)

    print("\nCopying merged image to clipboard...")
    clipboard_manager = ClipboardManager()
    clipboard_manager.copy_image_to_clipboard(merged_image)
    print("Merged image copied to clipboard successfully.")

if __name__ == "__main__":
    main()
