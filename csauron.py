# CSAURON.PY RUNNER

import time
from concurrent.futures import ThreadPoolExecutor
import threading
import queue
import keyboard
import traceback
import numpy as np

from capture_utils import Config, TemplateManager, WindowManager, ScreenshotManager, Logger, ImageSaver
from capture_processor import ImageProcessor


class WindowCapture:
    def __init__(self, config_file='config.json'):
        self.config = Config(config_file)
        self.initialize_components()
        self.setup_execution_environment()

    def initialize_components(self):
        self.template_manager = TemplateManager(self.config.template_dir)
        self.window_manager = WindowManager(self.config.target_window)
        self.screenshot_manager = ScreenshotManager()
        self.image_processor = ImageProcessor(self.config.confidence_threshold)
        self.logger = Logger('match_log.txt')
        self.image_saver = ImageSaver()


    def setup_execution_environment(self):
        self.processing_queue = queue.Queue(maxsize=5)
        self.running = False
        self.paused = False
        self.last_capture_time = 0
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.stop_key = 'l'
        self.pause_key = 'p'

    def handle_exception(self, error_message):
        print(f"Error: {error_message}")
        print(traceback.format_exc())

    def capture_and_process_loop(self):
        while self.running:
            if not self.paused:
                try:
                    current_time = time.time()
                    if current_time - self.last_capture_time >= self.config.capture_interval:
                        self.capture_and_enqueue()
                        self.last_capture_time = current_time
                    
                    try:
                        img, window_position = self.processing_queue.get(timeout=0.01)
                        self.executor.submit(self.process_image, img, window_position)
                    except queue.Empty:
                        pass
                except Exception:
                    print("Error in capture and process loop:")
                    print(traceback.format_exc())
            else:
                time.sleep(0.01)  # Sleep briefly when paused to reduce CPU usage

    def capture_and_enqueue(self):
        try:
            target_window = self.window_manager.get_target_window()
            if target_window:
                img, window_position = self.screenshot_manager.capture_window(target_window)
                try:
                    self.processing_queue.put_nowait((img, window_position))
                except queue.Full:
                    print("Processing queue is full. Skipping this frame.")
            else:
                print("Target window not found.")
        except Exception:
            print("Error in capture_and_enqueue:")
            print(traceback.format_exc())

    def process_image(self, img, window_position):
        try:
            timestamp, processed_img, log_entries = self.image_processor.process_image(img, window_position, self.template_manager.templates)
            self.logger.write_log(timestamp, log_entries)
            self.image_saver.save_processed_image(timestamp, processed_img)
            if not isinstance(img, np.ndarray):
                img = np.array(img)
            
        except Exception:
            print("Error in process_image:")
            print(traceback.format_exc())
    
# RUNNER UTILS

    def stop_capture(self):
        print(f"Stop key '{self.stop_key}' pressed. Stopping capture...")
        self.running = False

    def toggle_pause(self):
        self.paused = not self.paused
        status = "paused" if self.paused else "resumed"
        print(f"Capture {status}.")

# MAIN LOOP
    def run(self):
        self.running = True
        print(f"Waiting 3 seconds before starting... Switch to window.")
        print(f"Press '{self.stop_key}' to stop the capture.")
        print(f"Press '{self.pause_key}' to pause/resume the capture.")
        time.sleep(3)

        capture_thread = threading.Thread(target=self.capture_and_process_loop)
        capture_thread.start()

        # Set up the keyboard listeners
        keyboard.on_press_key(self.stop_key, lambda _: self.stop_capture())
        keyboard.on_press_key(self.pause_key, lambda _: self.toggle_pause())

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_capture()
        except Exception:
            print("Unexpected error in main loop:")
            print(traceback.format_exc())
        finally:
            self.running = False
            capture_thread.join()
            self.executor.shutdown(wait=True)
            print("Capture stopped.")

if __name__ == '__main__':
    try:
        window_capture = WindowCapture()
        window_capture.run()
    except Exception:
        print("Fatal error:")
        print(traceback.format_exc())
