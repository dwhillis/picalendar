"""
Waveshare 7.3" E-Ink Display Driver
Wraps waveshare_epd library for consistent API
"""

import sys
import os
import logging
from datetime import datetime
from PIL import Image
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class WaveshareDisplay:
    """Driver for Waveshare 7.3" e-ink display (800x480)"""
    
    WIDTH = 800
    HEIGHT = 480
    
    def __init__(self, use_gpio=True, flip_display=False):
        """Initialize display driver.
        
        Args:
            use_gpio: If True, use GPIO for control. If False, simulate for testing.
            flip_display: If True, rotate image 180 degrees before displaying.
        """
        self.use_gpio = use_gpio
        self.flip_display = flip_display
        self.epd = None
        self.image_buffer = None
        
        if use_gpio:
            self._init_display()
        else:
            logger.info("Display simulation mode enabled")
        
        if flip_display:
            logger.info("Display flip enabled (180° rotation)")
    
    def _init_display(self):
        """Initialize the actual display hardware"""
        try:
            # Add waveshare_epd to path
            libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'waveshare_epd')
            if libdir not in sys.path:
                sys.path.insert(0, libdir)
            
            from waveshare_epd import epd7in3e
            
            self.epd = epd7in3e.EPD()
            logger.info("Display driver initialized")
        except Exception as e:
            logger.error(f"Failed to initialize display: {e}")
            raise
    
    def init(self):
        """Initialize display and prepare for image updates"""
        if not self.use_gpio:
            logger.info("Display init (simulation)")
            return
        
        try:
            logger.info("Initializing display...")
            self.epd.init()
            logger.info("Display initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize display: {e}")
            raise
    
    def display_image(self, image_path):
        """Display image on e-ink display
        
        Args:
            image_path: Path to PNG/image file (800x480 or higher DPI renderings)
        """
        if not self.use_gpio:
            logger.info(f"Display image (simulation): {image_path}")
            return
        
        try:
            # Load and validate image
            img = Image.open(image_path)
            
            # Ensure RGB for proper color quantization
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Flip image 180 degrees if enabled
            if self.flip_display:
                img = img.rotate(180)
            
            if img.size != (self.WIDTH, self.HEIGHT):
                logger.warning(f"Resizing image from {img.size} to {self.WIDTH}x{self.HEIGHT}")
                # Convert PIL Image to numpy array for OpenCV
                img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                # Use cubic interpolation for high-quality downscaling
                img_cv = cv2.resize(img_cv, (self.WIDTH, self.HEIGHT), interpolation=cv2.INTER_AREA)
                # Convert back to PIL Image
                img = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
            
            # Save copy for debugging
            debug_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'renders')
            os.makedirs(debug_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            debug_path = os.path.join(debug_dir, f'display_debug_{timestamp}.png')
            img.save(debug_path)
            logger.debug(f"Debug image saved: {debug_path}")
            
            # Get buffer from epd library's getbuffer method
            buf = self.epd.getbuffer(img)
            
            # Display the buffer
            self.epd.display(buf)
            logger.info(f"Image displayed: {image_path}")
            
        except Exception as e:
            logger.error(f"Failed to display image: {e}")
            raise
    
    def display_pil_image(self, img):
        """Display PIL Image object on e-ink display
        
        Args:
            img: PIL Image object
        """
        if not self.use_gpio:
            logger.info("Display PIL image (simulation)")
            return
        
        try:
            # Ensure RGB for proper color quantization
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Flip image 180 degrees if enabled
            if self.flip_display:
                img = img.rotate(180)
            
            if img.size != (self.WIDTH, self.HEIGHT):
                logger.warning(f"Resizing image from {img.size} to {self.WIDTH}x{self.HEIGHT}")
                # Convert PIL Image to numpy array for OpenCV
                img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                # Use cubic interpolation for high-quality downscaling
                img_cv = cv2.resize(img_cv, (self.WIDTH, self.HEIGHT), interpolation=cv2.INTER_CUBIC)
                # Convert back to PIL Image
                img = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
            
            # Get buffer from epd library's getbuffer method
            buf = self.epd.getbuffer(img)
            
            # Display the buffer
            self.epd.display(buf)
            logger.info("Image displayed")
            
        except Exception as e:
            logger.error(f"Failed to display image: {e}")
            raise
    
    def power_off(self):
        """Turn off display power"""
        if not self.use_gpio:
            logger.info("Display power off (simulation)")
            return
        
        try:
            self.epd.sleep()
            logger.info("Display powered off")
        except Exception as e:
            logger.error(f"Failed to power off: {e}")
    
    def clear(self):
        """Clear display (white screen)"""
        if not self.use_gpio:
            logger.info("Display clear (simulation)")
            return
        
        try:
            self.epd.Clear()
            logger.info("Display cleared")
        except Exception as e:
            logger.error(f"Failed to clear display: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.use_gpio and self.epd:
                # The waveshare_epd library handles cleanup internally
                pass
            logger.info("Display driver cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
