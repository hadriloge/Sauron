## CAPTURE_UTILS.PY

import psutil
from win32 import win32gui, win32process
from mss import mss
from PIL import Image
import numpy as np
import os
import cv2
from collections import deque
import queue
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Dict
from contextlib import contextmanager


## UTILS
class Config:
    def __init__(self, config_file='config.json'):
        self.load_config(config_file)

    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        self.target_window = config.get('target_window', 'chrome.exe')
        self.capture_interval = config.get('capture_interval', 4)
        self.template_dir = config.get('template_dir', '.venv/templates')
        self.confidence_threshold = config.get('confidence_threshold', 0.8)

@dataclass
class Template:
    name: str
    image: np.ndarray
    category: str
    value: int
    
# LOAD TEMPLATES AND METADATA
class TemplateManager:
    def __init__(self, template_dir: str, metadata_file: str = 'templates_metadata.json'):
        self.template_dir = template_dir
        self.metadata_file = metadata_file
        self.templates: List[Template] = self.load_templates()

    def load_templates(self) -> List[Template]:
        if not os.path.exists(self.template_dir):
            raise ValueError(f"Template directory not found: {self.template_dir}")
        
        metadata = self.load_metadata()
        templates = []

        for filename in os.listdir(self.template_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                template_path = os.path.join(self.template_dir, filename)
                template_image = cv2.imread(template_path, 0)
                if template_image is not None:
                    template_info = metadata.get(filename, {})
                    templates.append(Template(
                        name=filename,
                        image=template_image,
                        category=template_info.get('category', 'uncategorized'),
                        value=template_info.get('value', 0),
                    ))
                else:
                    print(f"Warning: Could not load template {filename}")
        
        if not templates:
            raise ValueError("No valid template images found in the templates directory.")
        
        return templates

    def load_metadata(self) -> Dict:
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Metadata file {self.metadata_file} not found. Using default values.")
            return {}
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {self.metadata_file}. Using default values.")
            return {}

## GET WINDOW
class WindowManager:
    def __init__(self, target_window):
        self.target_window = target_window

    def get_target_window(self):
        def enum_windows_callback(hwnd, target_windows):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    process = psutil.Process(pid)
                    if process.name().lower() == self.target_window.lower():
                        target_windows.append(hwnd)
                except psutil.NoSuchProcess:
                    pass
            return True

        target_windows = []
        win32gui.EnumWindows(enum_windows_callback, target_windows)
        
        return target_windows[0] if target_windows else None

# INITIAL SCREENSHOT
class ScreenshotManager:
    def __init__(self, max_screenshots=5):
        self.max_screenshots = max_screenshots
        self.screenshot_queue = deque(maxlen=max_screenshots)
        os.makedirs('screenshots', exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.thread_local = threading.local()
        self.deletion_queue = queue.Queue()
        self.cleanup_thread = threading.Thread(target=self.cleanup_old_screenshots, daemon=True)
        self.cleanup_thread.start()

    @contextmanager
    def get_mss(self):
        if not hasattr(self.thread_local, 'sct'):
            self.thread_local.sct = mss()
        yield self.thread_local.sct

    def capture_window(self, hwnd):
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width, height = right - left, bottom - top

        monitor = {"top": top, "left": left, "width": width, "height": height}
        
        with self.get_mss() as sct:
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        
        timestamp = int(time.time())
        screenshot_path = os.path.join('screenshots', f'screenshot_{timestamp}.png')
        
        # Save the screenshot asynchronously
        self.executor.submit(self.save_screenshot, img, screenshot_path)
        
        self.manage_screenshot_queue(timestamp)
        
        return img, (left, top)

    def save_screenshot(self, img, path):
        with open(path, 'wb') as f:
            img.save(f, format='PNG', optimize=True)

    def manage_screenshot_queue(self, timestamp):
        self.screenshot_queue.append(timestamp)
        if len(self.screenshot_queue) == self.max_screenshots:
            old_timestamp = self.screenshot_queue[0]
            old_file = os.path.join('screenshots', f'screenshot_{old_timestamp}.png')
            self.deletion_queue.put(old_file)

    def cleanup_old_screenshots(self):
        while True:
            try:
                file_to_delete = self.deletion_queue.get(timeout=1)
                self.delete_file_with_retry(file_to_delete)
            except queue.Empty:
                continue

    def delete_file_with_retry(self, file_path, max_attempts=5, delay=1):
        for attempt in range(max_attempts):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                break
            except PermissionError:
                if attempt < max_attempts - 1:
                    time.sleep(delay)
                else:
                    print(f"Failed to delete {file_path} after {max_attempts} attempts")

    def __del__(self):
        self.executor.shutdown(wait=True)
        # Wait for the cleanup thread to finish
        self.deletion_queue.put(None)  # Signal to stop the cleanup thread
        self.cleanup_thread.join(timeout=5)


## LOGGER 
class Logger:
    def __init__(self, log_file):
        self.log_file = log_file

    def write_log(self, timestamp, log_entries):
        log_content = f"Timestamp: {timestamp}\n" + "\n".join(log_entries) + "\n" + "-" * 50 + "\n"
        with open(self.log_file, 'a') as f:
            f.write(log_content)
            print(f"{timestamp} Log written.")


# SAVE IMAGES FOR DEBUG (CAN REMOVE BUT GOOD DEBUG)
class ImageSaver:
    def __init__(self, max_saved_images=5):
        self.max_saved_images = max_saved_images
        self.processed_queue = deque(maxlen=max_saved_images)

    def save_processed_image(self, timestamp, img_cv):
        os.makedirs('processed', exist_ok=True)
        cv2.imwrite(f'processed/processed_{timestamp}.png', img_cv)
        
        self.processed_queue.append(timestamp)
        if len(self.processed_queue) == self.max_saved_images:
            old_timestamp = self.processed_queue[0]
            old_file = f'processed/processed_{old_timestamp}.png'
            if os.path.exists(old_file):
                os.remove(old_file)
