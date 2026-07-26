import os
import sys

# Ensure listener directory is in python path and set as current working directory
listener_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "listener"))
os.chdir(listener_dir)
if listener_dir not in sys.path:
    sys.path.insert(0, listener_dir)

# Import and execute main listener module
if __name__ == "__main__":
    import asyncio
    import listener
    asyncio.run(listener.main())
