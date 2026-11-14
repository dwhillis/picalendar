# Pi Calendar Display - Setup Guide

## Installation

### 1. System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv libatlas-base-dev libjasper-dev libharfbuzz0b libwebp6 libtiff5 libopenjp2-7 libopenjp2-7-dev

# For Raspberry Pi GPIO support
sudo apt-get install -y python3-gpiozero python3-rpi.gpio

```

### 2. Python Dependencies

```bash
cd /home/pi/picalendar
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Display Hardware

Edit `display_config.py` to match your GPIO pin configuration:

```python
GPIO_PIN_RST = 17    # Reset pin
GPIO_PIN_DC = 25     # Data/Command pin
GPIO_PIN_CS = 8      # Chip Select (SPI handles this)
GPIO_PIN_BUSY = 24   # Busy status pin
```

### 4. Enable SPI

```bash
sudo raspi-config
# Navigate to: Interfacing Options > SPI > Yes
```

### 5. Install Systemd Service

```bash
sudo cp picalendar.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable picalendar.service
sudo systemctl start picalendar.service
```

## Testing

### Test Without Hardware

```python
# In display_config.py, set:
DISPLAY_ENABLED = False
```

Run the main script:
```bash
python3 main.py
```

### Test With Hardware (Simulated GPIO)

```python
# In display_config.py, set:
DISPLAY_ENABLED = True
DISPLAY_SIMULATE = True
```

### Test Display Driver

```python
from display_driver import WaveshareDisplay
from PIL import Image

# Create test image
test_img = Image.new('1', (800, 480), 1)  # White image

# Display it
with WaveshareDisplay(use_gpio=False) as display:
    display.init()
    display.display_pil_image(test_img)
```

## Configuration

### Update Interval

In `display_config.py`:
```python
UPDATE_INTERVAL = 1800  # 30 minutes
```

### Timezone

```python
TIMEZONE = 'UTC'
```

### Debug Settings

Save rendered images for inspection:
```python
DEBUG_SAVE_RENDERS = True
DEBUG_RENDER_PATH = '/tmp/picalendar_renders'
```

## Monitoring

View logs:
```bash
sudo journalctl -u picalendar.service -f
```

View recent logs:
```bash
sudo journalctl -u picalendar.service --no-pager -n 50
```

## Troubleshooting

### SPI Not Working
```bash
# Check if SPI is enabled
ls -la /dev/spidev*

# Check SPI module is loaded
lsmod | grep spi
```

### GPIO Errors
```bash
# Check GPIO access
sudo usermod -a -G gpio pi

# Relogin or reboot for group changes to take effect
```

### Display Not Updating
1. Check logs: `sudo journalctl -u picalendar.service -f`
2. Test display: Run test script above
3. Check GPIO connections and power

## Performance Notes

- Initial render may take 5-10 seconds
- Subsequent renders use cached HTTP assets
- E-ink display refresh takes 2-3 seconds
- Default 30-minute interval balances battery life with freshness
- Set `UPDATE_INTERVAL = 300` (5 minutes) for testing

## GPIO Pinout Reference

Raspberry Pi 5:
```
GPIO 17  → RST (Reset)
GPIO 25  → DC (Data/Command)
GPIO 8   → CS (Chip Select - handled by SPI)
GPIO 24  → BUSY (Busy status)
GPIO 10  → SPI MOSI
GPIO 9   → SPI MISO
GPIO 11  → SPI CLK
GND      → GND
3V3      → VCC (power)
```

Verify with: `gpio readall` (requires wiringpi)

## Hardware Connections

Waveshare 7.3" Display to Raspberry Pi 5:
```
Display VCC    → Pi 3V3
Display GND    → Pi GND
Display CLK    → Pi GPIO 11 (SPI CLK)
Display MOSI   → Pi GPIO 10 (SPI MOSI)
Display MISO   → Pi GPIO 9  (SPI MISO)
Display CS     → Pi GPIO 8  (or 3V3)
Display DC     → Pi GPIO 25
Display RST    → Pi GPIO 17
Display BUSY   → Pi GPIO 24
```
