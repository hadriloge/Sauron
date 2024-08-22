import asyncio
import cv2
import json
import numpy as np
import os
import psutil
import time
import torch
from mss import mss
from PIL import Image
from torchvision.transforms import Compose, Resize, ToTensor, Normalize
from win32 import win32gui, win32process

class DepthEstimator:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = torch.hub.load("intel-isl/MiDaS", "MiDaS_small").to(self.device).eval()
        self.transform = Compose([
            Resize((384, 384)),
            ToTensor(),
            Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    async def estimate_depth(self, img):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        input_batch = self.transform(Image.fromarray(img_rgb)).unsqueeze(0).to(self.device)
        with torch.no_grad():
            prediction = self.model(input_batch)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=img.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()
        return prediction.cpu().numpy()

class CameraEstimator:
    async def estimate_camera_params(self, img):
        height, width = img.shape[:2]
        return {
            "focal_length": width,
            "principal_point": (width // 2, height // 2),
            "image_size": (width, height)
        }

class WindowCapture:
    def __init__(self, config_file='config.json'):
        self.load_config(config_file)
        self.templates = self.load_templates()
        self.depth_estimator = DepthEstimator()
        self.camera_estimator = CameraEstimator()
        self.sct = mss()
        self.previous_frame = None

    def load_config(self, config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        self.target_window = config.get('target_window', 'chrome.exe')
        self.capture_interval = config.get('capture_interval', 0.1)  # Reduced for real-time
        self.template_dir = config.get('template_dir', '.venv/templates')
        self.confidence_threshold = config.get('confidence_threshold', 0.8)

    def load_templates(self):
        templates = []
        for filename in os.listdir(self.template_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                template_path = os.path.join(self.template_dir, filename)
                template = cv2.imread(template_path, 0)
                if template is not None:
                    templates.append((filename, template))
        return templates

    async def capture_window(self):
        target_window = self.get_target_window()
        if target_window:
            left, top, right, bottom = win32gui.GetWindowRect(target_window)
            width, height = right - left, bottom - top
            monitor = {"top": top, "left": left, "width": width, "height": height}
            screenshot = self.sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            return img, left, top
        return None, None, None

    async def process_screenshot(self, img, window_left, window_top):
        timestamp = time.time()
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        img_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        results = {
            "timestamp": timestamp,
            "health_bars": await self.check_health_bars(img_cv),
            "template_matches": await self.match_templates(img_gray, window_left, window_top),
            "change_significance": await self.calculate_change(img_gray),
            "depth_map": await self.depth_estimator.estimate_depth(img_cv),
            "camera_params": await self.camera_estimator.estimate_camera_params(img_cv)
        }

        self.previous_frame = img_gray
        return results

    async def check_health_bars(self, img_cv):
        health_bars = [
            {"name": "Thirst", "position": (1087, 687)},
            {"name": "Hunger", "position": (1118, 683)},
            {"name": "Temperature", "position": (1149, 698)},
            {"name": "Blood", "position": (1185, 697)},
            {"name": "Health", "position": (1202, 687)},
        ]

        results = {}
        for bar in health_bars:
            x, y = bar["position"]
            color = img_cv[y, x]
            
            if np.all(color == [0, 0, 0]):
                state = "DEAD"
            elif np.all(color >= [170, 170, 170]):
                state = "White (Best)"
            elif np.all((color >= [0, 180, 180]) & (color <= [100, 255, 255])):
                state = "Yellow (Okay)"
            elif np.all((color >= [0, 0, 150]) & (color <= [100, 100, 255])):
                state = "Red (Critical)"
            else:
                state = "Unknown"
            
            results[bar['name']] = state
        
        return results

    async def match_templates(self, img_gray, window_left, window_top):
        matches = {}
        for template_name, template in self.templates:
            match_result = await self.match_template(img_gray, template)
            if match_result:
                startX, startY, endX, endY, scale, confidence = match_result
                print(f"Template: {template_name}, Confidence: {confidence:.4f}, "
                      f"Location: ({startX}, {startY}) to ({endX}, {endY})")

                if confidence >= self.confidence_threshold:
                    matches[template_name] = {
                        "scale": scale,
                        "confidence": confidence,
                        "relative_position": ((startX, startY), (endX, endY)),
                        "absolute_position": ((window_left + startX, window_top + startY), 
                                              (window_left + endX, window_top + endY))
                    }
        return matches

    async def match_template(self, img_gray, template):
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

    async def calculate_change(self, img_gray):
        if self.previous_frame is not None:
            frame_diff = cv2.absdiff(self.previous_frame, img_gray)
            _, thresh = cv2.threshold(frame_diff, 30, 255, cv2.THRESH_BINARY)
            return (np.sum(thresh) / 255) / (thresh.shape[0] * thresh.shape[1]) * 100
        return 0

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

    async def run(self):
        while True:
            img, left, top = await self.capture_window()
            if img is not None:
                results = await self.process_screenshot(img, left, top)
                print(f"\nProcessed screenshot at {results['timestamp']}")
                print(f"Health Bars: {results['health_bars']}")
                print(f"Template Matches: {results['template_matches']}")
                print(f"Change Significance: {results['change_significance']:.2f}%")
                depth_map = results['depth_map']
                print(f"Depth: min={depth_map.min():.2f}, max={depth_map.max():.2f}, "
                      f"mean={depth_map.mean():.2f}")
            await asyncio.sleep(self.capture_interval)

async def main():
    window_capture = WindowCapture()
    await window_capture.run()

if __name__ == '__main__':
    asyncio.run(main())
