from colordef import ColorDefinition

class ColorMap(object):
    def __init__(self, metastore):
        self.metastore = metastore
        self.colordefs = {}
    def find_color_desc(self, color_id):
        return self.metastore.find_color_desc(color_id)
    def resolve_color_desc(self, color_desc):
        return self.metastore.resolve_color_desc(color_desc)
    def get_color_def(self, color_id_or_desc):
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
                raise Exception("color id not found")
        cd = ColorDefinition.from_color_desc(color_id, color_desc)
        self.colordefs[color_id] = cd
        return cd
        
