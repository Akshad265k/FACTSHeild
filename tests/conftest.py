"""pytest configuration — ensure project root is on sys.path."""
import sys
from pathlib import Path

# Add project root so imports like "from core.normalization import ..." work
sys.path.insert(0, str(Path(__file__).parent.parent))
