"""
Example to get list of active channels
"""
import asterisk.manager
import sys

manager = asterisk.manager.Manager()

try:
    # connect to the manager
    try:
        manager.connect('localhost')
        manager.login('user', 'secret')

        # get a status report
        response = manager.status()
        print(response)
        
        response = manager.command('core show channels concise')
        print(response.data)

        manager.logoff()
    except asterisk.manager.ManagerSocketException as e:
        print "Error connecting to the manager: %s" % e.strerror
        sys.exit(1)
    except asterisk.manager.ManagerAuthException as e:
        print "Error logging in to the manager: %s" % e.strerror
        sys.exit(1)
    except asterisk.manager.ManagerException as e:
        print "Error: %s" % e.strerror
        sys.exit(1)

finally:
    # remember to clean up
    manager.close()

