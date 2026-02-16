import logging
import sys
import os
import copy
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Create logs directory if not exists
if not os.path.exists("logs"):
    os.makedirs("logs")

class NetBotFormatter(logging.Formatter):
    """
    Custom formatter with color support and stage-specific icons.
    """
    
    LEVEL_COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    STAGE_ICONS = {
        'A': '🐦 [A]', # Collector (using generic bird as default, but network icon takes precedence if present)
        # Actually user wants: [Network] [Stage]
        # So we just use [A], [B], etc. logic
        'A': '[A]',
        'B': '[B]',
        'C': '[C]',
        'D': '[D]',
    }

    NETWORK_ICONS = {
        'Twitter': '🐦',
        'X': '🐦',
        'Instagram': '📸',
        'Threads': '🧵',
        'Dev.to': '📝',
        'System': '🌀',
    }
    
    STATUS_ICONS = {
        'SYSTEM': '🌀',
        'DISCOVERY': '🔍',
        'FILTER': '⚖️',
        'BRAIN': '🧠',
        'FINANCE': '💸',
        'ERROR': '❌',
        'SUCCESS': '✅',
        'WARN': '⚠️',
    }

    def __init__(self, fmt=None, datefmt=None, style='%', use_colors=True):
        super().__init__(fmt, datefmt, style)
        self.use_colors = use_colors

    def format(self, record):
        # Create a copy so we don't mutate the original record for other handlers
        record = copy.copy(record)
        
        # 1. Determine Network Icon
        network = getattr(record, 'network', None)
        prefix_parts = []
        
        if network:
            icon = self.NETWORK_ICONS.get(network, '')
            if icon:
                prefix_parts.append(f"{icon} [{network}]")
            else:
                prefix_parts.append(f"[{network}]")
        
        # 2. Determine Stage Icon/Prefix
        stage = getattr(record, 'stage', None)
        if stage:
            stage_display = self.STAGE_ICONS.get(stage, f"[{stage}]")
            prefix_parts.append(stage_display)
        
        # 3. Determine Status Code Icon (if applicable)
        status_code = getattr(record, 'status_code', None)
        if status_code:
            icon = self.STATUS_ICONS.get(status_code, '')
            parts = f"{icon} [{status_code}]" if icon else f"[{status_code}]"
            # If we already have network/stage, maybe status code is supplementary?
            # User example: 🌀 [ORCHESTRATOR]
            # My example: 🌀 [SYSTEM]
            prefix_parts.append(parts)

        # Construct the prefix string
        prefix = " ".join(prefix_parts)
        if prefix:
            prefix = f"{prefix} "
            
        # 4. Handle indentation for Multi-line messages (Scenario: Stage C)
        original_msg = record.msg
        if isinstance(original_msg, str) and '\n' in original_msg:
             lines = original_msg.split('\n')
             header = lines[0]
             body = lines[1:]
             # Indent body lines with a visual tree structure
             # Use a fixed indentation or dynamic based on header length? Fixed is safer.
             # User suggested "                   └─ "
             indent = " " * 25 # Approximate generic indent
             indented_body = [f"{indent}└─ {line.strip()}" for line in body]
             record.msg = header + "\n" + "\n".join(indented_body)
        
        # Prepend prefix to the message
        record.msg = f"{prefix}{record.msg}"
        
        # Format the full record (timestamp, level, message)
        formatted_msg = super().format(record)
        
        # 5. Apply Colors (Console Only)
        if self.use_colors:
            color = self.LEVEL_COLORS.get(record.levelno, Fore.WHITE)
            levelname = record.levelname
            # Replace the LEVELNAME part with colored version
            # Note: This is a simple replacement. If levelname appears in message it might be replaced too.
            # Safer to format separately or assume standard format.
            # Standard format: '%(asctime)s - %(levelname)s - %(message)s'
            # We can replace " - LEVEL -" with " - COLOR LEVEL RESET -"
            formatted_msg = formatted_msg.replace(f" - {levelname} - ", f" - {color}{levelname}{Style.RESET_ALL} - ")
            
        return formatted_msg

class NetBotLoggerAdapter(logging.LoggerAdapter):
    """
    Adapter that injects 'network', 'stage', or 'status_code' into log records.
    """
    def process(self, msg, kwargs):
        # Merge extra from adapter with extra from call
        extra = self.extra.copy() if self.extra else {}
        
        # Move custom kwargs to extra so Logger doesn't complain
        for key in ['stage', 'network', 'status_code']:
            if key in kwargs:
                extra[key] = kwargs.pop(key)
        
        if 'extra' in kwargs:
            extra.update(kwargs['extra'])
        kwargs['extra'] = extra
        return msg, kwargs

def setup_logger(name: str = "netbot", log_file: str = "logs/app.log", level=logging.INFO):
    """Setup logger with dual handlers (Color Console + Plain File)"""
    
    # Custom format string
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 1. Console Handler (Color)
    console_formatter = NetBotFormatter(fmt=log_format, datefmt=date_format, use_colors=True)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    
    # 2. File Handler (Plain)
    file_formatter = NetBotFormatter(fmt=log_format, datefmt=date_format, use_colors=False)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(file_formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding handlers multiple times
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    # CRITICAL: Prevent propagation to root logger
    logger.propagate = False
        
    return logger

# Global logger instance
logger = setup_logger()

# Silence noisy third-party libraries
SILENCED_LIBRARIES = [
    "httpx", "httpcore", "openai", "urllib3", "playwright", "phi", "agno"
]
for lib in SILENCED_LIBRARIES:
    logging.getLogger(lib).setLevel(logging.WARNING)
