import sys
import psutil
from win32 import win32gui, win32process
import time
from mss import mss
from PIL import Image
import numpy as np
import os
import cv2
from collections import deque
import json
from concurrent.futures import ThreadPoolExecutor

class WindowCapture:
    def __init__(self, config_file='config.json'):
        self.load_config(config_file)
        self.screenshot_queue = deque(maxlen=10)
        self.processed_queue = deque(maxlen=10)
        self.templates = self.load_templates()
        self.log_file = 'match_log.txt'
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.previous_frame = None

    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        self.target_window = config.get('target_window', 'chrome.exe')
        self.capture_interval = config.get('capture_interval', 4)
        self.template_dir = config.get('template_dir', '.venv/templates')
        self.confidence_threshold = config.get('confidence_threshold', 0.8)

    def load_templates(self):
        if not os.path.exists(self.template_dir):
            raise ValueError(f"Template directory not found: {self.template_dir}")
        
        templates = []
        for filename in os.listdir(self.template_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                template_path = os.path.join(self.template_dir, filename)
                template = cv2.imread(template_path, 0)
                if template is not None:
                    templates.append((filename, template))
                else:
                    print(f"Warning: Could not load template {filename}")
        
        if not templates:
            raise ValueError("No valid template images found in the templates directory.")
        
        return templates

    def capture_window(self):
        target_window = self.get_target_window()
        if target_window:
            left, top, right, bottom = win32gui.GetWindowRect(target_window)
            width, height = right - left, bottom - top
            print(f"Target window size: {width}x{height}")

            with mss() as sct:
                monitor = {"top": top, "left": left, "width": width, "height": height}
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                
                self.screenshot_queue.append(img)
                self.executor.submit(self.process_screenshot, img, left, top)

    def process_screenshot(self, img, window_left, window_top):
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        ## GET PIXEL COLOR STATES HERE AND SAVE FULL IMAGE DATA FOR ROBOT


        img_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        timestamp = time.time()
        log_entries = []
        
        # Perform template matching
        for template_name, template in self.templates:
            match_result = self.match_template(img_gray, template)
            if match_result:
                startX, startY, endX, endY, scale, confidence = match_result
                abs_startX, abs_startY = window_left + startX, window_top + startY
                abs_endX, abs_endY = window_left + endX, window_top + endY
                
                if confidence >= self.confidence_threshold:
                    cv2.rectangle(img_cv, (startX, startY), (endX, endY), (0, 255, 0), 2)
                
                    log_entries.append(
                        f"Match found for template {template_name} at scale {scale:.2f}\n"
                        f"Confidence: {confidence:.4f}\n"
                        f"Position relative to window: ({startX}, {startY}) to ({endX}, {endY})\n"
                        f"Absolute screen position: ({abs_startX}, {abs_startY}) to ({abs_endX}, {abs_endY})"
                    )
                else:
                    log_entries.append(f"Low confidence match for template {template_name}: {confidence:.4f}")
            else:
                log_entries.append(f"No match found for template {template_name}")
        
        # Perform frame differencing 
        if self.previous_frame is not None:
            frame_diff = cv2.absdiff(self.previous_frame, img_gray)
            _, thresh = cv2.threshold(frame_diff, 30, 255, cv2.THRESH_BINARY)
            
            # Calculate change significance
            change_percentage = (np.sum(thresh) / 255) / (thresh.shape[0] * thresh.shape[1]) * 100
            log_entries.append(f"Change significance: {change_percentage:.2f}%")
        
        self.previous_frame = img_gray
        
        self.write_log(timestamp, log_entries)
        self.processed_queue.append((timestamp, img_cv))
        self.save_processed_image(timestamp, img_cv)

    def match_template(self, img_gray, template):
        h, w = template.shape[:2]
        found = None
        for scale in np.linspace(0.2, 1.0, 20)[::-1]:
            resized = cv2.resize(img_gray, (int(img_gray.shape[1] * scale), int(img_gray.shape[0] * scale)))
            r = img_gray.shape[1] / float(resized.shape[1])
            
            if resized.shape[0] < h or resized.shape[1] < w:
                break
            
            res = cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)
            _, maxVal, _, maxLoc = cv2.minMaxLoc(res)
            
            if found is None or maxVal > found[0]:
                found = (maxVal, maxLoc, r)
        
        if found:
            maxVal, maxLoc, r = found
            startX, startY = int(maxLoc[0] * r), int(maxLoc[1] * r)
            endX, endY = int((maxLoc[0] + w) * r), int((maxLoc[1] + h) * r)
            return startX, startY, endX, endY, 1/r, maxVal
        return None

    def write_log(self, timestamp, log_entries):
        log_content = f"Timestamp: {timestamp}\n" + "\n".join(log_entries) + "\n" + "-" * 50 + "\n"
        with open(self.log_file, 'a') as f:
            f.write(log_content)

    def save_processed_image(self, timestamp, img_cv):
        os.makedirs('processed', exist_ok=True)
        cv2.imwrite(f'processed/processed_{timestamp}.png', img_cv)
        
        if len(self.processed_queue) == self.processed_queue.maxlen:
            old_timestamp, _ = self.processed_queue[0]
            old_file = f'processed/processed_{old_timestamp}.png'
            if os.path.exists(old_file):
                os.remove(old_file)

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

    def run(self):
        while True:
            self.capture_window()
            time.sleep(self.capture_interval)

if __name__ == '__main__':
    window_capture = WindowCapture()
    window_capture.run()