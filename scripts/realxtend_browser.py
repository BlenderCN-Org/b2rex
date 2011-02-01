#!BPY

"""
Name: 'RealXtend Mesh Browser'
Blender: 249
Group: 'Import'
Tooltip: 'Exports the current scene to RealXtend server'
"""

__author__ = ['Pablo Martin']
__version__ = '0.8'
__url__ = ['B2rex Sim, http://sim.lorea.org',
           'B2rex forum, https://sim.lorea.org/pg/groups/5/b2rex/',
	   'B2rex repo, http://github.com/caedesvvv/b2rex']
__bpydoc__ = "Please see the external documentation that comes with the script."


import b2rexpkg
from b2rexpkg.browserapp import RealxtendBrowserApplication

if __name__ == "__main__":
    application = RealxtendBrowserApplication()
    application.go()

