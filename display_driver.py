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
            # Set PLL frame rate to Fast mode (0x07) for ~2x faster B&W refresh
            self.epd.send_command(0x30)
            self.epd.send_data(0x07)
            logger.info("Display initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize display: {e}")
            raise
    
    def _pack_bw_buffer(self, img: Image.Image) -> bytes:
        """Fast 1-bit B&W to 4-bit-per-pixel packed buffer for Waveshare 7.3" EPD.

        Avoids RGB conversion, 7-color palette quantization, and slow Python loops.
        Maps pixel > 128 to White (0x1) and <= 128 to Black (0x0), packed 2 pixels/byte.
        """
        if img.mode != 'L':
            img = img.convert('L')

        # Threshold to 0 (black) and 1 (white) using NumPy
        arr = (np.asarray(img, dtype=np.uint8) > 128).astype(np.uint8)
        flat = arr.ravel()
        packed = (flat[0::2] << 4) | flat[1::2]
        return packed.tobytes()

    def _prepare_image(self, img: Image.Image) -> Image.Image:
        """Normalize dimensions and orientation for the display."""
        if img.mode not in ('L', '1'):
            img = img.convert('L')

        if self.flip_display:
            img = img.rotate(180)

        if img.size != (self.WIDTH, self.HEIGHT):
            if img.size == (self.HEIGHT, self.WIDTH):
                img = img.rotate(90, expand=True)
            else:
                logger.warning(f"Resizing image from {img.size} to {self.WIDTH}x{self.HEIGHT}")
                img_np = np.array(img.convert('L'))
                img_resized = cv2.resize(img_np, (self.WIDTH, self.HEIGHT), interpolation=cv2.INTER_AREA)
                img = Image.fromarray(img_resized, mode='L')

        return img

    def display_image(self, image_path):
        """Display image on e-ink display
        
        Args:
            image_path: Path to PNG/image file (800x480 or higher DPI renderings)
        """
        if not self.use_gpio:
            logger.info(f"Display image (simulation): {image_path}")
            return
        
        try:
            with Image.open(image_path) as img:
                self.display_pil_image(img)
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
            img = self._prepare_image(img)
            buf = self._pack_bw_buffer(img)
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
            white_buf = b'\x11' * (self.WIDTH * self.HEIGHT // 2)
            self.epd.display(white_buf)
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
