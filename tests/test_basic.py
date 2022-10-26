from unittest import TestCase
from asterisk.manager import Manager
from itertools import combinations


class TestBasic(TestCase):
    def test_action_id(self):
        """ ensure that no two actionIDs are the same, even if they come
        from separate manager instances.  Otherwise you risk aliasing
        events if you, for example, subscribe to all events while
        originating two different phone calls in different processes. """

        manager1 = Manager()
        manager2 = Manager()
        actionIDs = [
            manager1.get_actionID(),
            manager1.get_actionID(),
            manager2.get_actionID(),
            manager2.get_actionID(),
        ]
        for a, b in combinations(actionIDs, 2):
            self.assertNotEqual(a, b)
