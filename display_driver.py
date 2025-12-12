"""
Waveshare 7.3" E-Ink Display Driver
Supports SPI communication and GPIO control for Raspberry Pi 5
"""

import spidev
import gpiozero
import time
from gpiozero import GPIO, RPi
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class WaveshareDisplay:
    """Driver for Waveshare 7.3" e-ink display (800x480)"""
    
    # Display configuration
    WIDTH = 800
    HEIGHT = 480
    
    # GPIO pins (adjust for your wiring)
    PIN_RST = 17    # Reset
    PIN_DC = 25     # Data/Command
    PIN_CS = 8      # Chip Select (handled by SPI)
    PIN_BUSY = 24   # Busy status
    
    # SPI configuration
    SPI_BUS = 0
    SPI_DEVICE = 0
    SPI_SPEED = 4000000  # 4 MHz
    
    # E-ink display commands
    CMD_RESET = 0x12
    CMD_POWER_ON = 0x04
    CMD_POWER_OFF = 0x02
    CMD_WRITE_RAM = 0x24
    CMD_DISPLAY_UPDATE = 0x20
    CMD_READ_STATUS = 0x71
    
    def __init__(self, use_gpio=True):
        """Initialize display driver.
        
        Args:
            use_gpio: If True, use GPIO for control. If False, simulate for testing.
        """
        self.use_gpio = use_gpio
        self.spi = None
        self.gpio_reset = None
        self.gpio_dc = None
        self.gpio_busy = None
        self.image_buffer = None
        
        if use_gpio:
            self._init_gpio()
        
        self._init_spi()
        logger.info("Display driver initialized")
    
    def _init_gpio(self):
        """Initialize GPIO pins"""
        try:
            GPIO.setmode(RPi.BCM)
            
            self.gpio_reset = gpiozero.DigitalOutputDevice(
                self.PIN_RST, initial=True, active_high=True
            )
            self.gpio_dc = gpiozero.DigitalOutputDevice(
                self.PIN_DC, initial=False, active_high=True
            )
            self.gpio_busy = gpiozero.DigitalInputDevice(
                self.PIN_BUSY, pull_up=True
            )
            
            logger.info("GPIO pins initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GPIO: {e}")
            raise
    
    def _init_spi(self):
        """Initialize SPI communication"""
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(self.SPI_BUS, self.SPI_DEVICE)
            self.spi.max_speed_hz = self.SPI_SPEED
            self.spi.mode = 0
            self.spi.bits_per_word = 8
            self.spi.lsb_first = False
            
            logger.info(f"SPI initialized at {self.SPI_SPEED/1e6:.1f} MHz")
        except Exception as e:
            logger.error(f"Failed to initialize SPI: {e}")
            raise
    
    def _wait_busy(self, timeout=30):
        """Wait for display to finish busy state
        
        Args:
            timeout: Maximum seconds to wait
        """
        if not self.use_gpio:
            return
        
        start = time.time()
        while self.gpio_busy.is_active:
            if time.time() - start > timeout:
                logger.warning("Display busy timeout")
                return
            time.sleep(0.1)
    
    def _reset(self):
        """Reset display"""
        if not self.use_gpio:
            return
        
        self.gpio_reset.on()
        time.sleep(0.01)
        self.gpio_reset.off()
        time.sleep(0.1)
        self.gpio_reset.on()
        time.sleep(0.1)
        logger.debug("Display reset")
    
    def _write_command(self, cmd):
        """Write command byte to display
        
        Args:
            cmd: Command byte
        """
        if self.use_gpio:
            self.gpio_dc.off()  # DC=0 for command
        
        self.spi.writebytes([cmd])
        time.sleep(0.001)
    
    def _write_data(self, data):
        """Write data bytes to display
        
        Args:
            data: List of bytes or bytes object
        """
        if self.use_gpio:
            self.gpio_dc.on()  # DC=1 for data
        
        if isinstance(data, bytes):
            self.spi.writebytes(list(data))
        else:
            self.spi.writebytes(data)
        time.sleep(0.001)
    
    def init(self):
        """Initialize display and prepare for image updates"""
        logger.info("Initializing display...")
        
        self._reset()
        self._wait_busy()
        
        # Power on sequence
        self._write_command(0x01)  # Power setting
        self._write_data([0x07, 0x07, 0x3f, 0x3f])
        
        self._write_command(0x04)  # Power on
        self._wait_busy()
        
        # Panel configuration
        self._write_command(0x00)  # Panel setting
        self._write_data([0x1f, 0x0d])
        
        # Resolution setting
        self._write_command(0x61)  # Set resolution
        self._write_data([0x03, 0x20, 0x01, 0xe0])  # 800x480
        
        # Gate driving voltage
        self._write_command(0x05)  # Gate driving voltage
        self._write_data([0x0a])
        
        # Frame rate control
        self._write_command(0x3a)  # Frame rate
        self._write_data([0x50])
        
        logger.info("Display initialized successfully")
    
    def display_image(self, image_path):
        """Display image on e-ink display
        
        Args:
            image_path: Path to PNG image (800x480)
        """
        try:
            # Load and validate image
            img = Image.open(image_path)
            img = img.convert('1')  # Convert to black and white
            
            if img.size != (self.WIDTH, self.HEIGHT):
                logger.warning(f"Resizing image from {img.size} to {self.WIDTH}x{self.HEIGHT}")
                img = img.resize((self.WIDTH, self.HEIGHT), Image.Resampling.LANCZOS)
            
            self._display_image(img)
            logger.info(f"Image displayed: {image_path}")
            
        except Exception as e:
            logger.error(f"Failed to display image: {e}")
            raise
    
    def display_pil_image(self, img):
        """Display PIL Image object on e-ink display
        
        Args:
            img: PIL Image object (will be converted to 1-bit)
        """
        try:
            img = img.convert('1')  # Convert to black and white
            
            if img.size != (self.WIDTH, self.HEIGHT):
                logger.warning(f"Resizing image from {img.size} to {self.WIDTH}x{self.HEIGHT}")
                img = img.resize((self.WIDTH, self.HEIGHT), Image.Resampling.LANCZOS)
            
            self._display_image(img)
            logger.info("Image displayed")
            
        except Exception as e:
            logger.error(f"Failed to display image: {e}")
            raise
    
    def _display_image(self, img):
        """Internal method to write image to display
        
        Args:
            img: PIL Image (1-bit mode)
        """
        # Convert image to byte array
        pixels = list(img.getdata())
        
        # Pack bits: 8 pixels per byte, MSB first
        byte_array = []
        for i in range(0, len(pixels), 8):
            byte = 0
            for j in range(8):
                if i + j < len(pixels):
                    # Invert: 0=white, 1=black for e-ink
                    bit = 0 if pixels[i + j] else 1
                    byte = (byte << 1) | bit
            byte_array.append(byte)
        
        # Write to display RAM
        self._write_command(0x10)  # Data Entry Mode
        self._write_data([0x03])   # X inc, Y inc
        
        self._write_command(0x00)  # Start X address
        self._write_data([0x00])
        
        self._write_command(0x01)  # Start Y address
        self._write_data([0x00, 0x00])
        
        self._write_command(0x24)  # Write RAM
        self._write_data(byte_array)
        
        # Trigger display refresh
        self._write_command(0x20)  # Display Update
        self._wait_busy()
        
        logger.debug(f"Sent {len(byte_array)} bytes to display")
    
    def power_off(self):
        """Turn off display power"""
        try:
            self._write_command(0x02)  # Power off
            self._wait_busy()
            logger.info("Display powered off")
        except Exception as e:
            logger.error(f"Failed to power off: {e}")
    
    def clear(self):
        """Clear display (white screen)"""
        try:
            white_img = Image.new('1', (self.WIDTH, self.HEIGHT), 1)
            self._display_image(white_img)
            logger.info("Display cleared")
        except Exception as e:
            logger.error(f"Failed to clear display: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.spi:
                self.spi.close()
            if self.use_gpio:
                if self.gpio_reset:
                    self.gpio_reset.close()
                if self.gpio_dc:
                    self.gpio_dc.close()
                if self.gpio_busy:
                    self.gpio_busy.close()
            logger.info("Display driver cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
