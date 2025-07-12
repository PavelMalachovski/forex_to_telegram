import os
import sys
import time
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def setup_enhanced_logging():
    """Setup enhanced logging with detailed formatting."""
    # Use environment variable or relative path
    log_dir = Path(os.getenv('LOG_DIR', project_root / 'logs'))
    log_dir.mkdir(exist_ok=True)
    
    # Create formatter with more details
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_dir / 'enhanced_app.log')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Suppress noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return root_logger

def main():
    """Enhanced main function to test path fixes."""
    # Setup logging first
    logger = setup_enhanced_logging()
    logger.info("=== Enhanced Forex Bot Starting (Path Fix Test) ===")
    
    try:
        # Test that paths work correctly
        logger.info(f"Project root: {project_root}")
        logger.info(f"Log directory: {Path(os.getenv('LOG_DIR', project_root / 'logs'))}")
        
        # Test importing existing modules
        try:
            from app.config import Config
            logger.info("✅ Successfully imported Config")
        except ImportError as e:
            logger.warning(f"⚠️  Could not import Config: {e}")
        
        try:
            from app.services.notification_service import NotificationService
            logger.info("✅ Successfully imported NotificationService")
        except ImportError as e:
            logger.warning(f"⚠️  Could not import NotificationService: {e}")
        
        try:
            from app.database.connection import get_db, init_database
            logger.info("✅ Successfully imported database connection functions")
        except ImportError as e:
            logger.warning(f"⚠️  Could not import database connection: {e}")
        
        logger.info("=== Enhanced path fix test completed successfully ===")
        return 0
        
    except Exception as e:
        logger.error(f"Critical error in main: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
