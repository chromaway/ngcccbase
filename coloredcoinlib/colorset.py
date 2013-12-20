import hashlib
import json

from pycoin.encoding import b2a_base58


def deterministic_json_dumps(obj):
    """TODO: make it even more deterministic!"""
    return json.dumps(obj, separators=(',', ':'), sort_keys=True)


class ColorSet(object):
    """A set of colors which belong to certain a asset.
    It can be used to filter addresses and UTXOs
    """
    def __init__(self, colormap, color_desc_list):
        """Creates a new color set given a color map <colormap>
        and color descriptions <color_desc_list>
        """
        self.color_desc_list = color_desc_list
        self.color_id_set = set()
        for color_desc in color_desc_list:
            color_id = colormap.resolve_color_desc(color_desc)
            self.color_id_set.add(color_id)

    def __repr__(self):
        return self.color_desc_list.__repr__()

    def uncolored_only(self):
        return self.color_id_set == set([0])

    def get_data(self):
        """Returns a list of strings that describe the colors.
        e.g. ["obc:f0bd5...a5:0:128649"]
        """
        return self.color_desc_list

    def get_hash_string(self):
        """Returns a deterministic string for this color set.
        Useful for creating deterministic addresses for a given color.
        """
        json = deterministic_json_dumps(sorted(self.color_desc_list))
        return hashlib.sha256(json).hexdigest()

    def get_earliest(self):
        """Returns the color description of the earliest color to
        show in the blockchain. If there's a tie and two are issued
        in the same block, go with the one that has a smaller txhash
        """
        all_descs = self.get_data()
        if not len(all_descs):
            return "\x00\x00\x00\x00"
        best = all_descs[0]
        best_components = best.split(':')
        for desc in all_descs[1:]:
            components = desc.split(':')
            if int(components[3]) < int(best_components[3]):
                best = desc
            elif int(components[3]) == int(best_components[3]):
                if cmp(components[1], best_components[1]) == -1:
                    best = desc
        return best

    def get_color_hash(self):
        """Returns the hash used in color addresses.
        """
        return b2a_base58(self.get_hash_string().decode('hex')[:10])

    def has_color_id(self, color_id):
        """Returns boolean of whether color <color_id> is associated
        with this color set.
        """
        return (color_id in self.color_id_set)

    def intersects(self, other):
        """Given another color set <other>, returns whether
        they share a color in common.
        """
        return len(self.color_id_set & other.color_id_set) > 0

    def equals(self, other):
        """Given another color set <other>, returns whether
        they are the exact same color set.
        """
        return self.color_id_set == other.color_id_set

    @classmethod
    def from_color_ids(cls, colormap, color_ids):
        """Given a colormap <colormap> and a list of colors <color_ids>
        return a ColorSet object.
        """
        color_desc_list = [colormap.find_color_desc(color_id)
                           for color_id in color_ids]
        return cls(colormap, color_desc_list)
