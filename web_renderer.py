"""
Web Renderer - Headless rendering of calendar webpage to PNG
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import time
from PIL import Image
import io

logger = logging.getLogger(__name__)


class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
    """HTTP handler that suppresses logging"""
    def log_message(self, format, *args):
        pass


class WebRenderer:
    """Renders the calendar webpage to PNG image (800x480)"""
    
    RENDER_WIDTH = 800
    RENDER_HEIGHT = 480
    
    def __init__(self, web_root, port=8000, timeout=30):
        """Initialize web renderer
        
        Args:
            web_root: Path to directory containing index.html
            port: HTTP server port
            timeout: Timeout for rendering in seconds
        """
        self.web_root = Path(web_root)
        self.port = port
        self.timeout = timeout
        self.server = None
        self.server_thread = None
        self.try_playwright = True
        self.try_selenium = True
    
    def start_server(self):
        """Start local HTTP server in background thread"""
        try:
            handler = QuietHTTPRequestHandler
            os.chdir(self.web_root)
            
            self.server = HTTPServer(('127.0.0.1', self.port), handler)
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            time.sleep(0.5)  # Give server time to start
            logger.info(f"HTTP server started on port {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            return False
    
    def stop_server(self):
        """Stop local HTTP server"""
        try:
            if self.server:
                self.server.shutdown()
                logger.info("HTTP server stopped")
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
    
    def render_to_png(self, output_path=None):
        """Render webpage to PNG image
        
        Args:
            output_path: Path to save PNG. If None, uses temp file.
            
        Returns:
            Path to rendered PNG file
        """
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix='.png')
            os.close(fd)
        
        # Try Playwright first (preferred)
        if self.try_playwright:
            try:
                return self._render_with_playwright(output_path)
            except ImportError:
                logger.warning("Playwright not available, trying Selenium")
                self.try_playwright = False
            except Exception as e:
                logger.error(f"Playwright rendering failed: {e}")
                self.try_playwright = False
        
        # Fallback to Selenium
        if self.try_selenium:
            try:
                return self._render_with_selenium(output_path)
            except ImportError:
                logger.warning("Selenium not available, trying Playwright async")
                self.try_selenium = False
            except Exception as e:
                logger.error(f"Selenium rendering failed: {e}")
                self.try_selenium = False
        
        # Last resort: try async Playwright
        try:
            return asyncio.run(self._render_with_playwright_async(output_path))
        except Exception as e:
            logger.error(f"All rendering methods failed: {e}")
            raise
    
    def _render_with_playwright(self, output_path):
        """Render using Playwright (sync mode)
        
        Args:
            output_path: Path to save PNG
            
        Returns:
            Path to rendered PNG file
        """
        from playwright.sync_api import sync_playwright
        
        logger.info("Rendering with Playwright (sync)...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': self.RENDER_WIDTH, 'height': self.RENDER_HEIGHT})
            
            try:
                page.goto(f'http://127.0.0.1:{self.port}', wait_until='networkidle', timeout=self.timeout * 1000)
                time.sleep(1)  # Wait for JS to render
                page.screenshot(path=output_path)
                logger.info(f"Rendered to {output_path}")
                return output_path
            finally:
                browser.close()
    
    async def _render_with_playwright_async(self, output_path):
        """Render using Playwright (async mode)
        
        Args:
            output_path: Path to save PNG
            
        Returns:
            Path to rendered PNG file
        """
        from playwright.async_api import async_playwright
        
        logger.info("Rendering with Playwright (async)...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': self.RENDER_WIDTH, 'height': self.RENDER_HEIGHT})
            
            try:
                await page.goto(f'http://127.0.0.1:{self.port}', wait_until='networkidle', timeout=self.timeout * 1000)
                await page.wait_for_timeout(1000)
                await page.screenshot(path=output_path)
                logger.info(f"Rendered to {output_path}")
                return output_path
            finally:
                await browser.close()
    
    def _render_with_selenium(self, output_path):
        """Render using Selenium WebDriver
        
        Args:
            output_path: Path to save PNG
            
        Returns:
            Path to rendered PNG file
        """
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        
        logger.info("Rendering with Selenium...")
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument(f'--window-size={self.RENDER_WIDTH},{self.RENDER_HEIGHT}')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        
        driver = webdriver.Chrome(options=options)
        
        try:
            driver.get(f'http://127.0.0.1:{self.port}')
            
            # Wait for main content to load
            WebDriverWait(driver, self.timeout).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, 'main-container'))
            )
            
            time.sleep(1)  # Extra wait for JS rendering
            
            driver.save_screenshot(output_path)
            logger.info(f"Rendered to {output_path}")
            return output_path
        finally:
            driver.quit()
    
    def render_and_optimize(self, output_path=None):
        """Render webpage and optimize for e-ink display
        
        Args:
            output_path: Path to save optimized PNG
            
        Returns:
            Path to optimized PNG file
        """
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix='.png')
            os.close(fd)
        
        # First render to PNG
        png_path = self.render_to_png()
        
        # Optimize for e-ink
        try:
            img = Image.open(png_path)
            
            # Convert to grayscale then to black and white with dithering
            img = img.convert('L')  # Grayscale
            img = img.convert('1', dither=Image.Dither.FLOYDSTEINBERG)  # Floyd-Steinberg dithering
            
            img.save(output_path, 'PNG')
            logger.info(f"Optimized image saved to {output_path}")
            
            # Clean up temp file
            try:
                os.remove(png_path)
            except:
                pass
            
            return output_path
        except Exception as e:
            logger.error(f"Failed to optimize image: {e}")
            # Return original if optimization fails
            return png_path
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop_server()


def render_calendar_webpage(web_root=None, output_path=None, optimize=True, port=8000):
    """Convenience function to render calendar in one call
    
    Args:
        web_root: Path to web directory (defaults to current dir)
        output_path: Output PNG path (defaults to temp file)
        optimize: Whether to optimize for e-ink
        port: HTTP server port
        
    Returns:
        Path to rendered PNG
    """
    if web_root is None:
        web_root = Path.cwd()
    
    renderer = WebRenderer(web_root, port=port)
    
    try:
        renderer.start_server()
        
        if optimize:
            return renderer.render_and_optimize(output_path)
        else:
            return renderer.render_to_png(output_path)
    finally:
        renderer.cleanup()
