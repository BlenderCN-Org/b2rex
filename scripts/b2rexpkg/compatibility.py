import sys
if sys.version_info[0] == 2:
    from .b24.baseapp import Base24Application as BaseApplication
else:
    from .app import BaseApplication
