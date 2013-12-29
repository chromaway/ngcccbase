from colordef import ColorDefinition, UNCOLORED_MARKER
from txspec import InvalidColorIdError


class ColorMap(object):
    """ Manages and obtains color definitions """
    def __init__(self, metastore):
        self.metastore = metastore
        self.colordefs = {}

    def find_color_desc(self, color_id):
        if color_id == 0:
            return ""
        else:
            return self.metastore.find_color_desc(color_id)

    def resolve_color_desc(self, color_desc, auto_add=True):
        if color_desc == "":
            return 0
        else:
            return self.metastore.resolve_color_desc(color_desc, auto_add)

    def get_color_def(self, color_id_or_desc):
        """ Finds a color definition given an id or description """
        if color_id_or_desc == 0 or color_id_or_desc == '':
            return UNCOLORED_MARKER
        color_id = color_id_or_desc
        color_desc = None
        if not isinstance(color_id, (int, long)):
            color_desc = color_id_or_desc
            color_id = self.resolve_color_desc(color_id_or_desc)
        if color_id in self.colordefs:
            return self.colordefs[color_id]
        if not color_desc:
            color_desc = self.find_color_desc(color_id)
            if not color_desc:
                raise InvalidColorIdError("color id not found")
        cd = ColorDefinition.from_color_desc(
            color_id, color_desc)
        self.colordefs[color_id] = cd
        return cd
