from coloredcoinlib import ColorSet, IncompatibleTypesError, InvalidValueError
from coloredcoinlib.comparable import ComparableMixin


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

    def has_color_id(self, color_id):
        return self.get_color_set().has_color_id(color_id)

    def get_color_set(self):
        """Returns the list of colors for this asset.
        """
        return self.color_set

    def get_colorvalue(self, utxo):
        """ return colorvalue for a given utxo"""
        if utxo.colorvalues:
            for cv in utxo.colorvalues:
                if self.has_color_id(cv.get_color_id()):
                    return cv
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


class AssetValue(object):
    def __init__(self, **kwargs):
        self.asset = kwargs.pop('asset')

    def get_kwargs(self):
        kwargs = {}
        kwargs['asset'] = self.get_asset()
        return kwargs

    def clone(self):
        kwargs = self.get_kwargs()
        return self.__class__(**kwargs)

    def check_compatibility(self, other):
        if self.get_color_set() != other.get_color_set():
            raise IncompatibleTypesError        

    def get_asset(self):
        return self.asset

    def get_color_set(self):
        return self.asset.get_color_set()


class AdditiveAssetValue(AssetValue, ComparableMixin):
    def __init__(self, **kwargs):
        super(AdditiveAssetValue, self).__init__(**kwargs)
        self.value = kwargs.pop('value')
        if not isinstance(self.value, int):
            raise InvalidValueError('not an int')

    def get_kwargs(self):
        kwargs = super(AdditiveAssetValue, self).get_kwargs()
        kwargs['value'] = self.get_value()
        return kwargs

    def get_value(self):
        return self.value

    def __add__(self, other):
        if isinstance(other, int) and other == 0:
            return self
        self.check_compatibility(other)
        kwargs = self.get_kwargs()
        kwargs['value'] = self.get_value() + other.get_value()
        return self.__class__(**kwargs)

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        if isinstance(other, int) and other == 0:
            return self
        self.check_compatibility(other)
        kwargs = self.get_kwargs()
        kwargs['value'] = self.get_value() - other.get_value()
        return self.__class__(**kwargs)

    def __iadd__(self, other):
        self.check_compatibility(other)
        self.value += other.value
        return self

    def __lt__(self, other):
        self.check_compatibility(other)
        return self.get_value() < other.get_value()

    def __eq__(self, other):
        if self.get_color_set() != other.get_color_set():
            return False
        else:
            return self.get_value() == other.get_value()

    def __gt__(self, other):
        if isinstance(other, int) and other == 0:
            return self.get_value() > 0
        return other < self

    def __repr__(self):
        return "Asset Value: %s" % (self.get_value())

    @classmethod
    def sum(cls, items):
        return reduce(lambda x,y:x + y, items)


class AssetTarget(object):
    def __init__(self, address, assetvalue):
        self.address = address
        self.assetvalue = assetvalue

    def get_asset(self):
        return self.assetvalue.get_asset()

    def get_color_set(self):
        return self.assetvalue.get_color_set()

    def get_address(self):
        return self.address

    def get_value(self):
        return self.assetvalue.get_value()

    def __repr__(self):
        return "%s: %s" % (self.get_address(), self.assetvalue)

    @classmethod
    def sum(cls, targets):
        if len(targets) == 0:
            return 0
        c = targets[0].assetvalue.__class__
        return c.sum([t.assetvalue for t in targets])


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
