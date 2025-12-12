#!/usr/bin/env python3
"""
Quick test script for web rendering
Run to verify rendering pipeline works before full deployment
"""

import sys
from pathlib import Path
from web_renderer import WebRenderer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_render():
    """Test rendering the calendar webpage"""
    
    logger.info("Testing calendar webpage rendering...")
    logger.info(f"Web root: {Path.cwd()}")
    
    renderer = WebRenderer(web_root=Path.cwd(), port=8000, timeout=30)
    
    try:
        # Start HTTP server
        logger.info("Starting HTTP server...")
        renderer.start_server()
        
        # Test rendering without optimization
        logger.info("\n1. Testing basic render...")
        output1 = renderer.render_to_png('/tmp/test_basic.png')
        logger.info(f"✓ Basic render successful: {output1}")
        
        # Test rendering with optimization
        logger.info("\n2. Testing optimized render (for e-ink)...")
        output2 = renderer.render_and_optimize('/tmp/test_optimized.png')
        logger.info(f"✓ Optimized render successful: {output2}")
        
        logger.info("\n✓ All rendering tests passed!")
        logger.info(f"\nCheck the renders:")
        logger.info(f"  Basic: /tmp/test_basic.png")
        logger.info(f"  Optimized: /tmp/test_optimized.png")
        
        return 0
    
    except Exception as e:
        logger.error(f"✗ Render test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        renderer.cleanup()


if __name__ == '__main__':
    sys.exit(test_render())
