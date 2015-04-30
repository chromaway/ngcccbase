

import re
import json
from decimal import Decimal


class InvalidInput(Exception): pass


class SchemeNotFound(InvalidInput):
    def __init__(scheme):
        super(SchemeNotFound, self).__init__("Scheme '%s' not found!" % scheme)


def asset(model, _moniker):
    _moniker = moniker(_moniker)
    adm = model.get_asset_definition_manager()
    asset = adm.get_asset_by_moniker(_moniker)
    if not asset:
      raise AssetNotFound(_moniker)
    return asset


def decimal(decimal):
    return Decimal(decimal)


def quantity(quantity): # asset unknown
    quantity = decimal(quantity)
    if quantity < Decimal("0"):
        raise InvalidInput("Quantity must be > 0!")
    return quantity


def amount(asset, amount):
    amount = asset.parse_value(amount)
    if amount < 0:
        raise InvalidInput("Amount must be > 0!")
    return amount


def unit(unit):
    return int(unit)


def scheme(scheme):
    if scheme not in ['obc', 'epobc']:
        raise SchemeNotFound(scheme)
    return scheme


def integer(number):
    return int(number)


def flag(flag):
    return bool(flag)


def moniker(moniker):
    # limit charset for now
    if not re.match("^[a-zA-Z0-9_-]+$", moniker):
        raise InvalidInput("Moniker may only contain chars a-zA-Z0-9_-")
    return moniker


def cfgkey(key):
    # limit charset for now
    for subkey in key.split('.'):
        if not re.match("^[a-zA-Z0-9_-]+$", subkey):
            raise InvalidInput("Invalid key!")
    return key


def cfgvalue(value):
    # limit basic string and ints for now
    if not re.match("^[a-zA-Z0-9_-]+$", value):
        raise InvalidInput("Invalid value!")
    return value


def colordesc(colordesc):
    if not re.match("^(epobc|obc):[0-9a-f]+:[0-9]+:[0-9]+$", colordesc):
        raise InvalidInput("Invalid color description!")
    return colordesc


def jsonasset(data):
    data = json.loads(data)
    monikers = [moniker(m) for m in data['monikers']]
    color_set = [colordesc(cd) for cd in data['color_set']]
    _unit = unit(data['unit'])
    return { 'monikers' : monikers, 'color_set' : color_set, 'unit' : _unit }


def coloraddress(model, asset, coloraddress):

    # asset must match address asset id
    adm = model.get_asset_definition_manager()
    address_asset, btcaddress = adm.get_asset_and_address(coloraddress)
    if asset != address_asset:
        raise InvalidInput("Address and asset don't match!")

    # check if valid btcaddress
    if not model.validate_address(btcaddress):
        raise InvalidInput("Address not valid!")

    return coloraddress


def sendmanyjson(model, data):
    sendmany_entries = []
    for entry in json.loads(data):
        _asset = asset(model, entry['moniker'])
        quantity = _asset.quantity(entry['quantity'])
        _coloraddress = coloraddress(model, _asset, entry['coloraddress'])
        sendmany_entries.append((_asset, _coloraddress, quantity))
    return sendmany_entries


