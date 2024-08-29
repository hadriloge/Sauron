# CAPTURE_PROCESSOR.PY

import numpy as np
import cv2
import json
import time
from concurrent.futures import ThreadPoolExecutor



## MAIN PROCESSOR
class ImageProcessor:
    def __init__(self, confidence_threshold, pixel_checks_file='pixel_checks.json'):
        self.confidence_threshold = confidence_threshold
        self.pixel_checks = self.load_pixel_checks(pixel_checks_file)

        self.previous_frame = None
        
        #self.dqn_image = None

        self.executor = ThreadPoolExecutor(max_workers=8)

    def load_pixel_checks(self, file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data['pixel_checks']
    
## COLORS
    def check_pixels(self, img_cv):
        results = []
        for check in self.pixel_checks:
            x, y = check["position"]
            color = img_cv[y, x]
            
            ranges = np.array([check["range"] for check in check["checks"]])
            lower_bounds = ranges[:, 0]
            upper_bounds = ranges[:, 1]
            
            # Vectorized comparison
            matches = np.all((color >= lower_bounds) & (color <= upper_bounds), axis=1)
            
            if np.any(matches):
                state = check["checks"][np.where(matches)[0][0]]["state"]
            elif np.all(color == [0, 0, 0]):
                state = "DEAD"
            else:
                state = "Unknown"
            
            results.append(f"{check['name']}: {state}\n")

        return results


# MAIN FLOW
    def process_image(self, img, window_position, templates):
        timestamp = time.time()
        log_entries = []

# CONVERT FROM RGB TO BGR
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

# CREATE DQN VERSION
        #self.dqn_image = cv2.resize(img_cv, (480, 270)) Resize for DQN
        # 3 * 270 * 480 = 388,800 values

            #self.dqn_image = cv2.cvtColor(self.dqn_image, cv2.COLOR_BGR2RGB)  # Convert to RGB
            #self.dqn_image = self.dqn_image.astype(np.float32) / 255.0  # Normalize to [0, 1]
            #self.dqn_image = np.transpose(self.dqn_image, (2, 0, 1))  # Change to (channels, height, width)

        # Add modular pixel checking here
        pixel_check_results = self.check_pixels(img_cv)
        log_entries.extend(pixel_check_results)

# CREATE GRAYSCALED
        img_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Template matching
        template_results = self.match_templates(img_gray, templates)
        for result in template_results:
            log_entries.extend(self.process_template_result(result, window_position, img_cv))
        
        # Change detection
        change_log = self.detect_changes(img_gray)
        if change_log:
            log_entries.append(change_log)

        return timestamp, img_cv, log_entries

## SECONDARIES
    def match_templates(self, img_gray, templates):
        results = []
        for template in templates:
            match_result = self.match_template(img_gray, template.image)
            if match_result:
                results.append((template, *match_result))
        return results
    
    def process_template_result(self, result, window_position, img_cv):
        template, startX, startY, endX, endY, scale, confidence = result
        abs_startX, abs_startY = window_position[0] + startX, window_position[1] + startY
        abs_endX, abs_endY = window_position[0] + endX, window_position[1] + endY
        
        log_entries = []
        if confidence >= self.confidence_threshold:
            cv2.rectangle(img_cv, (startX, startY), (endX, endY), (0, 255, 0), 1)
            log_entries.append(
                f"Conf: {confidence:.4f}\n"
                f"HC: {template.name} Scale: {scale:.2f}\n"
                f"Category: {template.category}\n"
                f"Value: {template.value}\n"
                f"Pos: ({startX}, {startY}):({endX}, {endY})\n"
                f"Abs: ({abs_startX}, {abs_startY}):({abs_endX}, {abs_endY})"
            )
            print(f"High confidence detected: {template.name} (Confidence: {confidence:.4f})")
        else:
            cv2.rectangle(img_cv, (startX, startY), (endX, endY), (0, 0, 255), 1)
            log_entries.append(
                f"Conf: {confidence:.4f}\n"
                f"LC: {template.name} Scale: {scale:.2f}\n"
                f"Category: {template.category}\n"
                f"Value: {template.value}\n"
                f"Pos: ({startX}, {startY}):({endX}, {endY})\n"
                f"Abs: ({abs_startX}, {abs_startY}):({abs_endX}, {abs_endY})\n"
            )
        
        return log_entries
    
## GRAYSCALE 
    def detect_changes(self, img_gray):
        if self.previous_frame is not None:
            if self.previous_frame.shape != img_gray.shape:
                self.previous_frame = cv2.resize(self.previous_frame, (img_gray.shape[1], img_gray.shape[0]))
            
            frame_diff = cv2.absdiff(self.previous_frame, img_gray)
            change_percentage = np.mean(frame_diff) / 255 * 100
            self.previous_frame = img_gray
            return f"CS: {change_percentage:.2f}%"
        
        self.previous_frame = img_gray
        return None

    def match_template(self, img_gray, template):
        h, w = template.shape[:2]
        found = None
        for scale in np.linspace(0.3, 1.0, 3)[::-1]:
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


    


