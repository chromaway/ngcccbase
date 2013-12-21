from coloredcoinlib import ColorSet
from txcons import BasicTxSpec, SimpleOperationalTxSpec


class AssetDefinition(object):
    """Stores the definition of a particular asset, including its color set,
    it's name (moniker), and the wallet model that represents it.
    """
    def __init__(self, colormap, params):
        """Create an Asset for a color map <colormap> and configuration
        <params>. Note params has the color definitions used for this
        Asset.
        """
        self.monikers = params.get('monikers', [])
        self.color_set = ColorSet(colormap, params.get('color_set'))
        self.unit = int(params.get('unit', 1))

    def __repr__(self):
        return "%s: %s" % (self.monikers, self.color_set)

    def get_monikers(self):
        """Returns the list of monikers for this asset.
        """
        return self.monikers

    def get_color_set(self):
        """Returns the list of colors for this asset.
        """
        return self.color_set

    def get_colorvalue(self, utxo):
        """ return colorvalue for a given utxo"""
        if self.color_set.uncolored_only():
            return utxo.value
        else:
            if utxo.colorvalues:
                for cv in utxo.colorvalues:
                    if cv[0] in self.color_set.color_id_set:
                        return cv[1]
            raise Exception("cannot get colorvalue for UTXO: "
                            "no colorvalues available")

    def parse_value(self, portion):
        """Returns actual number of Satoshis for this Asset
        given the <portion> of the asset.
        """
        return int(float(portion) * self.unit)

    def format_value(self, atoms):
        """Returns a string representation of the portion of the asset.
        can involve rounding.  doesn't display insignificant zeros
        """
        return '{0:g}'.format(atoms / float(self.unit))

    def get_data(self):
        """Returns a JSON-compatible object that represents this Asset
        """
        return {
            "monikers": self.monikers,
            "color_set": self.color_set.get_data(),
            "unit": self.unit
            }


class AssetDefinitionManager(object):
    """Manager for asset definitions. Useful for interacting with
    various Assets.
    """
    def __init__(self, colormap, config):
        """Given a color map <colormap> and a configuration <config>,
        create a new asset definition manager.
        """
        self.config = config
        self.colormap = colormap
        self.asset_definitions = []
        self.lookup_by_moniker = {}
        for ad_params in config.get('asset_definitions', []):
            self.register_asset_definition(
                AssetDefinition(self.colormap, ad_params))

        # add bitcoin as a definition
        if "bitcoin" not in self.lookup_by_moniker:
            btcdef = AssetDefinition(
                self.colormap, {
                    "monikers": ["bitcoin"],
                    "color_set": [""],
                    "unit": 100000000,
                    })
            self.lookup_by_moniker["bitcoin"] = btcdef
            self.asset_definitions.append(btcdef)
            self.update_config()

    def register_asset_definition(self, assdef):
        """Given an asset definition <assdef> in JSON-compatible format,
        register the asset with the manager. Note AssetDefinition's
        get_data can be used to get this definition for persistence.
        """
        self.asset_definitions.append(assdef)
        for moniker in assdef.get_monikers():
            if moniker in self.lookup_by_moniker:
                raise Exception(
                    'more than one asset definition have same moniker')
            self.lookup_by_moniker[moniker] = assdef

    def add_asset_definition(self, params):
        """Create a new asset with given <params>.
        params needs the following:
        monikers  - list of names (e.g. ["red", "blue"])
        color_set - list of color sets
                    (e.g. ["obc:f0bd5...a5:0:128649", "obc:a..0:0:147477"])
        """
        assdef = AssetDefinition(self.colormap, params)
        self.register_asset_definition(assdef)
        self.update_config()
        return assdef

    def get_asset_by_moniker(self, moniker):
        """Given a color name <moniker>, return the actual Asset Definition
        """
        return self.lookup_by_moniker.get(moniker)

    def update_config(self):
        """Write the current asset definitions to the persistent data-store
        """
        self.config['asset_definitions'] = \
            [assdef.get_data() for assdef in self.asset_definitions]

    def get_all_assets(self):
        """Returns a list of all assets managed by this manager.
        """
        return self.asset_definitions

    def get_asset_and_address(self, color_address):
        """Given a color address <color_address> return the asset
        and bitcoin address associated with the address. If the color
        described in the address isn't managed by this object,
        throw an exception.
        """

        if color_address.find('@') == -1:
            return (self.lookup_by_moniker.get('bitcoin'), color_address)

        color_set_hash, address = color_address.split('@')
        for asset in self.get_all_assets():
            if color_set_hash == asset.get_color_set().get_color_hash():
                return (asset, address)
        raise Exception("No asset has a color set with this hash: %s"
                        % color_set_hash)
