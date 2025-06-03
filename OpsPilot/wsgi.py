"""
WSGI config for OpsPilot project.
"""

import os
from django.core.wsgi import get_wsgi_application
from icecream import ic
from tqdm import tqdm
import sys
import time

# Configure icecream for prettier output
ic.configureOutput(prefix='🔔 Signal: ', includeContext=True)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'OpsPilot.settings')

# Get application before loading signals
application = get_wsgi_application()

# Define all signal modules to load
signal_modules = [
    'applications.dashboard.signals',
    'applications.tasks.signals',
    'applications.jobs.signals',
    'applications.inventory.signals',
    'applications.accounts.signals',
    'applications.calendar_app.signals'
]

# Create progress bar with tqdm
with tqdm(total=len(signal_modules), desc="Loading signals", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
    for module_name in signal_modules:
        try:
            # Use icecream to debug the loading process
            ic(f"Loading {module_name}")
            start_time = time.time()

            # Import the module
            __import__(module_name)

            # Calculate load time
            load_time = time.time() - start_time
            ic(f"✅ {module_name} loaded in {load_time:.3f}s")

        except Exception as e:
            # Log errors with icecream
            ic(f"❌ Error loading {module_name}: {str(e)}")

        # Update progress bar
        pbar.update(1)

# Final confirmation
ic("✨ All signal modules loaded")