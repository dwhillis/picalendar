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
from croniter import croniter

from display_driver import WaveshareDisplay
from direct_renderer import DirectRenderer
from web_server import start_server
import display_config as config
import calendar_config
import chore_wheel


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
            # Initialize renderer
            logger.info("Using direct buffer renderer")
            self.renderer = DirectRenderer()
            
            # Initialize display (if enabled)
            if config.DISPLAY_ENABLED:
                self.display = WaveshareDisplay(
                    use_gpio=not config.DISPLAY_SIMULATE,
                    flip_display=config.DISPLAY_FLIP
                )
                self.display.init()
                
                if config.CLEAR_ON_STARTUP:
                    logger.info("Clearing display on startup...")
                    self.display.clear()
            
            # Start web management server
            start_server(manager=self)

            logger.info("Initialization complete")
            return True
        
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _render_image(self):
        """Render calendar to a PIL Image (and optionally save latest preview PNG)."""
        logger.info("Rendering calendar...")

        for attempt in range(config.MAX_RENDER_RETRIES):
            try:
                img = self.renderer.render()

                if config.DEBUG_SAVE_RENDERS:
                    render_dir = Path(config.DEBUG_RENDER_PATH)
                    render_dir.mkdir(parents=True, exist_ok=True)
                    output_path = render_dir / "calendar_latest.png"
                    img.save(output_path, "PNG")
                    self.last_render_path = str(output_path)
                    logger.info(f"Render saved: {output_path}")

                return img

            except Exception as e:
                if attempt < config.MAX_RENDER_RETRIES - 1:
                    logger.warning(f"Render attempt {attempt + 1} failed: {e}")
                    time.sleep(config.RETRY_DELAY)
                else:
                    logger.error(f"Failed to render calendar: {e}")
                    logger.error(traceback.format_exc())
                    return None

    def render_calendar(self):
        """Render calendar to PNG and return its path."""
        img = self._render_image()
        if img is None:
            return None

        if not self.last_render_path:
            render_dir = Path(config.DEBUG_RENDER_PATH)
            render_dir.mkdir(parents=True, exist_ok=True)
            output_path = render_dir / "calendar_latest.png"
            img.save(output_path, "PNG")
            self.last_render_path = str(output_path)

        return self.last_render_path
    
    def update_display(self):
        """Render and update display"""
        if not config.DISPLAY_ENABLED:
            logger.info("Display disabled, skipping update")
            return True
        
        img = self._render_image()
        if img is None:
            logger.error("Render failed, not updating display")
            if config.CLEAR_ON_ERROR and self.display:
                try:
                    self.display.clear()
                except Exception as e:
                    logger.error(f"Failed to clear display: {e}")
            return False
        
        # Display image directly from memory buffer with retries
        for attempt in range(config.MAX_DISPLAY_RETRIES):
            try:
                logger.info(f"Updating display (attempt {attempt + 1}/{config.MAX_DISPLAY_RETRIES})...")
                self.display.display_pil_image(img)
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
    
    def _get_next_scheduled_time(self):
        """Calculate the next scheduled update time from cron expressions"""
        now = datetime.now()
        next_times = []
        
        for cron_expr in config.UPDATE_SCHEDULE:
            try:
                cron = croniter(cron_expr, now)
                next_times.append(cron.get_next(datetime))
            except Exception as e:
                logger.warning(f"Invalid cron expression '{cron_expr}': {e}")
        
        if not next_times:
            logger.error("No valid cron schedules configured, defaulting to 1 hour")
            return datetime.fromtimestamp(time.time() + 3600)
        
        return min(next_times)

    def _get_next_chore_rotation_time(self):
        """Calculate the next chore wheel rotation time"""
        cron_expr = getattr(config, 'CHORE_WHEEL_SCHEDULE', None)
        if not cron_expr:
            return None
        try:
            return croniter(cron_expr, datetime.now()).get_next(datetime)
        except Exception as e:
            logger.warning(f"Invalid chore wheel cron expression '{cron_expr}': {e}")
            return None
    
    def run(self):
        """Main event loop"""
        if not self.initialize():
            logger.error("Failed to initialize, exiting")
            return 1
        
        # Initial update after startup delay
        logger.info(f"Waiting {config.STARTUP_DELAY}s before first update...")
        time.sleep(config.STARTUP_DELAY)
        
        # Perform initial update at startup
        try:
            logger.info("Performing startup update...")
            self.update_display()
        except Exception as e:
            logger.error(f"Startup update failed: {e}")
            logger.error(traceback.format_exc())
        
        try:
            next_chore_rotation = self._get_next_chore_rotation_time()
            if next_chore_rotation:
                logger.info(f"Next chore wheel rotation: {next_chore_rotation.strftime('%Y-%m-%d %H:%M:%S')}")

            while self.running:
                next_update = self._get_next_scheduled_time()
                sleep_time = max((next_update - datetime.now()).total_seconds(), 1)

                if next_chore_rotation:
                    chore_sleep = max((next_chore_rotation - datetime.now()).total_seconds(), 1)
                    sleep_time = min(sleep_time, chore_sleep)

                logger.info(f"Next update scheduled for {next_update.strftime('%Y-%m-%d %H:%M:%S')} (in {sleep_time:.0f}s)")
                
                sleep_end = time.time() + sleep_time
                while self.running and time.time() < sleep_end:
                    time.sleep(min(1.0, sleep_end - time.time()))
                
                if not self.running:
                    break

                if next_chore_rotation and datetime.now() >= next_chore_rotation:
                    logger.info("Rotating chore wheel (scheduled)")
                    chore_wheel.rotate_forward()
                    next_chore_rotation = self._get_next_chore_rotation_time()
                    if next_chore_rotation:
                        logger.info(f"Next chore wheel rotation: {next_chore_rotation.strftime('%Y-%m-%d %H:%M:%S')}")

                if datetime.now() >= next_update:
                    try:
                        self.update_display()
                    except Exception as e:
                        logger.error(f"Update cycle failed: {e}")
                        logger.error(traceback.format_exc())
        
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
            if self.renderer and hasattr(self.renderer, 'cleanup'):
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
