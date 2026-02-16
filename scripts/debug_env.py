
import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"Implementation: {sys.implementation}")
print(f"Version: {sys.version}")
print("sys.path:")
for p in sys.path:
    print(f"  {p}")

try:
    import psycopg
    print(f"✅ psycopg imported: {psycopg.__version__} from {psycopg.__file__}")
except ImportError as e:
    print(f"❌ psycopg import failed: {e}")

try:
    import psycopg2
    print(f"✅ psycopg2 imported: {psycopg2.__version__} from {psycopg2.__file__}")
except ImportError as e:
    print(f"❌ psycopg2 import failed: {e}")

try:
    import feedparser
    print(f"✅ feedparser imported: {feedparser.__version__} from {feedparser.__file__}")
except ImportError as e:
    print(f"❌ feedparser import failed: {e}")

try:
    import agno
    print(f"✅ agno imported: {agno.__version__} from {agno.__file__}")
except ImportError as e:
    print(f"❌ agno import failed: {e}")
