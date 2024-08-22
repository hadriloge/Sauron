import time
from concurrent.futures import ThreadPoolExecutor

from capture_utils import Config, TemplateManager, WindowManager, ScreenshotManager, ImageProcessor, Logger, ImageSaver

class WindowCapture:
    def __init__(self, config_file='config.json'):
        self.config = Config(config_file)
        self.template_manager = TemplateManager(self.config.template_dir)
        self.window_manager = WindowManager(self.config.target_window)
        self.screenshot_manager = ScreenshotManager()
        self.image_processor = ImageProcessor(self.config.confidence_threshold)
        self.logger = Logger('match_log.txt')
        self.image_saver = ImageSaver()
        self.executor = ThreadPoolExecutor(max_workers=4)

    def capture_and_process(self):
        target_window = self.window_manager.get_target_window()
        if target_window:
            img, window_position = self.screenshot_manager.capture_window(target_window)
            self.executor.submit(self.process_image, img, window_position)

    def process_image(self, img, window_position):
        timestamp, processed_img, log_entries = self.image_processor.process_image(img, window_position, self.template_manager.templates)
        self.logger.write_log(timestamp, log_entries)
        self.image_saver.save_processed_image(timestamp, processed_img)

    def run(self):
        while True:
            self.capture_and_process()
            time.sleep(self.config.capture_interval)

if __name__ == '__main__':
    window_capture = WindowCapture()
    window_capture.run()