#!/usr/bin/env python3
"""
Main application orchestrator for e-ink calendar display
Manages rendering and display updates on Raspberry Pi 5
"""

import signal
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
import traceback

from display_driver import WaveshareDisplay
from web_renderer import WebRenderer
import display_config as config


# Setup logging
def setup_logging():
    """Configure logging to file and console"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format=log_format,
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.FileHandler(config.LOG_FILE) if config.LOG_FILE else logging.NullHandler()
        ]
    )
    
    return logging.getLogger(__name__)


logger = setup_logging()


class CalendarDisplayManager:
    """Manages the calendar display system"""
    
    def __init__(self):
        self.running = True
        self.display = None
        self.renderer = None
        self.last_render_path = None
        self.last_update_time = 0
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        """Handle termination signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def initialize(self):
        """Initialize all components"""
        logger.info("=" * 60)
        logger.info("Calendar Display Manager starting...")
        logger.info("=" * 60)
        
        try:
            # Initialize web renderer
            self.renderer = WebRenderer(
                web_root=config.WEB_ROOT,
                port=config.HTTP_PORT,
                timeout=config.RENDER_TIMEOUT
            )
            self.renderer.start_server()
            
            # Initialize display (if enabled)
            if config.DISPLAY_ENABLED:
                self.display = WaveshareDisplay(use_gpio=not config.DISPLAY_SIMULATE)
                self.display.init()
                
                if config.CLEAR_ON_STARTUP:
                    logger.info("Clearing display on startup...")
                    self.display.clear()
            
            logger.info("Initialization complete")
            return True
        
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def render_calendar(self):
        """Render calendar to PNG"""
        logger.info("Rendering calendar...")
        
        try:
            # Create output path
            output_path = None
            if config.DEBUG_SAVE_RENDERS:
                Path(config.DEBUG_RENDER_PATH).mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = f"{config.DEBUG_RENDER_PATH}/calendar_{timestamp}.png"
            
            # Render with retries
            for attempt in range(config.MAX_RENDER_RETRIES):
                try:
                    if config.RENDER_OPTIMIZE:
                        png_path = self.renderer.render_and_optimize(output_path)
                    else:
                        png_path = self.renderer.render_to_png(output_path)
                    
                    logger.info(f"Render successful: {png_path}")
                    self.last_render_path = png_path
                    return png_path
                
                except Exception as e:
                    if attempt < config.MAX_RENDER_RETRIES - 1:
                        logger.warning(f"Render attempt {attempt + 1} failed: {e}")
                        time.sleep(config.RETRY_DELAY)
                    else:
                        raise
        
        except Exception as e:
            logger.error(f"Failed to render calendar: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def update_display(self):
        """Render and update display"""
        if not config.DISPLAY_ENABLED:
            logger.info("Display disabled, skipping update")
            return True
        
        png_path = self.render_calendar()
        if not png_path:
            logger.error("Render failed, not updating display")
            if config.CLEAR_ON_ERROR and self.display:
                try:
                    self.display.clear()
                except Exception as e:
                    logger.error(f"Failed to clear display: {e}")
            return False
        
        # Display image with retries
        for attempt in range(config.MAX_DISPLAY_RETRIES):
            try:
                logger.info(f"Updating display (attempt {attempt + 1}/{config.MAX_DISPLAY_RETRIES})...")
                self.display.display_image(png_path)
                logger.info("Display update successful")
                self.last_update_time = time.time()
                return True
            
            except Exception as e:
                if attempt < config.MAX_DISPLAY_RETRIES - 1:
                    logger.warning(f"Display update attempt {attempt + 1} failed: {e}")
                    time.sleep(config.RETRY_DELAY)
                else:
                    logger.error(f"Display update failed after {config.MAX_DISPLAY_RETRIES} attempts: {e}")
                    if config.CLEAR_ON_ERROR:
                        try:
                            self.display.clear()
                        except:
                            pass
                    return False
    
    def run(self):
        """Main event loop"""
        if not self.initialize():
            logger.error("Failed to initialize, exiting")
            return 1
        
        # Initial update after startup delay
        logger.info(f"Waiting {config.STARTUP_DELAY}s before first update...")
        time.sleep(config.STARTUP_DELAY)
        
        try:
            while self.running:
                current_time = time.time()
                
                # Perform update
                try:
                    self.update_display()
                except Exception as e:
                    logger.error(f"Update cycle failed: {e}")
                    logger.error(traceback.format_exc())
                
                # Wait for next update
                if self.running:
                    sleep_time = max(config.UPDATE_INTERVAL - (time.time() - current_time), 1)
                    next_update = datetime.fromtimestamp(time.time() + sleep_time)
                    logger.info(f"Next update scheduled for {next_update.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Sleep with periodic checks for shutdown
                    for _ in range(int(sleep_time * 10)):
                        if not self.running:
                            break
                        time.sleep(0.1)
        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            logger.error(traceback.format_exc())
            return 1
        
        finally:
            self.shutdown()
        
        return 0
    
    def shutdown(self):
        """Cleanup and shutdown"""
        logger.info("Shutting down...")
        
        try:
            if self.renderer:
                self.renderer.cleanup()
            
            if self.display:
                if config.POWER_OFF_ON_SHUTDOWN:
                    self.display.power_off()
                self.display.cleanup()
            
            logger.info("Shutdown complete")
        
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def main():
    """Entry point"""
    manager = CalendarDisplayManager()
    return manager.run()


if __name__ == '__main__':
    sys.exit(main())
