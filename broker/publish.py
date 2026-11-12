"""Draft pull-request publisher.

The gate does not import or call this module. No publishing route is selected,
so this interface refuses every call.
"""


class Publisher:
    def open_draft(self, receipt):
        raise NotImplementedError("publishing route is not selected")
