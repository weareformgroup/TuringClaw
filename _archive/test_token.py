import sys
sys.path.insert(0, "gui")
from providers import token_tracker
print(token_tracker.get_usage())
