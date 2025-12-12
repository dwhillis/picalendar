#!/usr/bin/env python3
"""
Test script for display hardware
Run to verify GPIO and SPI communication works
"""

import sys
import time
from PIL import Image
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_gpio_pins():
    """Test GPIO pin access (requires gpiozero)"""
    logger.info("Testing GPIO pin access...")
    
    try:
        import gpiozero
        from gpiozero import GPIO, RPi
        
        GPIO.setmode(RPi.BCM)
        
        # Test output pins
        test_pins = [17, 25, 24]  # RST, DC, BUSY
        
        for pin in test_pins:
            try:
                device = gpiozero.DigitalOutputDevice(pin)
                device.on()
                device.off()
                device.close()
                logger.info(f"  ✓ GPIO {pin} OK")
            except Exception as e:
                logger.warning(f"  ✗ GPIO {pin} failed: {e}")
        
        return True
    
    except ImportError:
        logger.warning("gpiozero not installed, skipping GPIO test")
        return False
    except Exception as e:
        logger.error(f"GPIO test failed: {e}")
        return False


def test_spi():
    """Test SPI communication"""
    logger.info("\nTesting SPI communication...")
    
    try:
        import spidev
        
        spi = spidev.SpiDev()
        spi.open(0, 0)
        spi.max_speed_hz = 4000000
        
        logger.info(f"  SPI mode: {spi.mode}")
        logger.info(f"  SPI speed: {spi.max_speed_hz/1e6:.1f} MHz")
        logger.info(f"  SPI bits per word: {spi.bits_per_word}")
        
        # Try a test write (won't hurt if no display connected)
        test_byte = [0x00]
        result = spi.xfer2(test_byte)
        logger.info(f"  ✓ SPI write test OK (returned {result[0]:02x})")
        
        spi.close()
        return True
    
    except Exception as e:
        logger.error(f"SPI test failed: {e}")
        return False


def test_display_simulation():
    """Test display driver in simulation mode"""
    logger.info("\nTesting display driver (simulation mode)...")
    
    try:
        from display_driver import WaveshareDisplay
        
        # Create test image
        test_img = Image.new('1', (800, 480), 1)
        
        # Initialize display in simulation mode
        display = WaveshareDisplay(use_gpio=False)
        display.init()
        
        logger.info("  ✓ Display initialized")
        
        # Test displaying image
        display.display_pil_image(test_img)
        logger.info("  ✓ Display image command sent")
        
        # Test clear
        display.clear()
        logger.info("  ✓ Display cleared")
        
        display.cleanup()
        logger.info("  ✓ Display driver OK")
        
        return True
    
    except Exception as e:
        logger.error(f"Display driver test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_display_with_gpio():
    """Test display driver with actual GPIO (if available)"""
    logger.info("\nTesting display driver with GPIO...")
    
    try:
        from display_driver import WaveshareDisplay
        
        # Try with real GPIO
        display = WaveshareDisplay(use_gpio=True)
        display.init()
        
        logger.info("  ✓ Display initialized with GPIO")
        
        # Test clear
        display.clear()
        logger.info("  ✓ Display cleared")
        
        display.cleanup()
        logger.info("  ✓ Display driver with GPIO OK")
        
        return True
    
    except PermissionError:
        logger.warning("  ⚠ GPIO permission denied (run with sudo for full test)")
        return False
    except Exception as e:
        logger.error(f"Display driver GPIO test failed: {e}")
        return False


def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("Display Hardware Test Suite")
    logger.info("=" * 60)
    
    results = {
        'GPIO': test_gpio_pins(),
        'SPI': test_spi(),
        'Display (Simulation)': test_display_simulation(),
        'Display (GPIO)': test_display_with_gpio(),
    }
    
    logger.info("\n" + "=" * 60)
    logger.info("Test Results:")
    logger.info("=" * 60)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL or SKIPPED"
        logger.info(f"{name:30} {status}")
    
    logger.info("\nNote: Some tests may be skipped if:")
    logger.info("  - Required packages not installed")
    logger.info("  - Running without GPIO permissions (try: sudo)")
    logger.info("  - Hardware not connected")
    
    all_passed = all(results.values())
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
