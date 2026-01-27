# appengine_config.py
try:
    from google.appengine.ext import vendor
except Exception:
    vendor = None

# Add any libraries installed in the "lib" folder (GAE legacy).
if vendor:
    vendor.add('lib')