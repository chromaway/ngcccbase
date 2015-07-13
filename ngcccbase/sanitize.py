

import re
import csv
from decimal import Decimal
from ngcccbase.address import coloraddress_to_bitcoinaddress
from pycoin.key import validate

base58set = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')


class InvalidInput(Exception):
    pass


class AssetNotFound(InvalidInput):

    def __init__(self, moniker):
        super(AssetNotFound, self).__init__("Asset '%s' not found!" % moniker)


class SchemeNotFound(InvalidInput):

    def __init__(self, scheme):
        super(SchemeNotFound, self).__init__("Scheme '%s' not found!" % scheme)


def asset(model, _moniker):
    _moniker = moniker(_moniker)
    adm = model.get_asset_definition_manager()
    asset = adm.get_asset_by_moniker(_moniker)
    if not asset:
        raise AssetNotFound(_moniker)
    return asset


def decimal(decimal):
    decimal = unicode_string(decimal)
    return Decimal(decimal)


def quantity(q):  # asset unknown
    q = decimal(q)
    if q < Decimal("0"):
        raise InvalidInput("Quantity must be > 0!")
    return q


def assetamount(asset, amount):
    amount = quantity(amount)
    if not asset.validate_value(amount):
        raise InvalidInput("Amount not a multiple of asset unit!")
    amount = asset.parse_value(amount)
    if amount < 0:
        raise InvalidInput("Amount must be > 0!")
    return amount


def unit(u):
    u = int(u)
    if u <= 0:
        raise InvalidInput("unit must be > 0!")
    return u


def scheme(s):
    if s not in [u'obc', u'epobc']:
        raise SchemeNotFound(s)
    return s


def integer(number):
    return int(number)


def positiveinteger(number):
    number = int(number)
    if number < 0:
        raise InvalidInput("Integer may not be < 0!")
    return number


def flag(flag):
    return bool(flag)


def unicode_string(s):
    return unicode(s)


def moniker(moniker):
    moniker = unicode_string(moniker)
    # limit charset for now
    if not re.match("^[a-zA-Z0-9_-]+$", moniker):
        raise InvalidInput("Moniker may only contain chars a-zA-Z0-9_-")
    return moniker


def cfgkey(key):
    # limit charset for now
    key = unicode_string(key)
    for subkey in key.split('.'):
        if not re.match("^[a-zA-Z0-9_-]+$", subkey):
            raise InvalidInput("Invalid key!")
    return key


def cfgvalue(value):
    return value  # any json serializable object


def txid(txid):
    txid = unicode_string(txid)
    if not re.match("^[0-9a-f]+$", txid):  # TODO better validation
        raise InvalidInput("Invalid txid!")
    return txid


def rawtx(rawtx):
    rawtx = unicode_string(rawtx)
    if not re.match("^[0-9a-f]+$", rawtx):  # TODO better validation
        raise InvalidInput("Invalid rawtx!")
    return rawtx


def colordesc(colordesc):
    colordesc = unicode_string(colordesc)
    if not re.match("^(epobc|obc):[0-9a-f]+:[0-9]+:[0-9]+$", colordesc):
        raise InvalidInput("Invalid color description!")
    return colordesc


def jsonasset(data):
    monikers = [moniker(m) for m in data['monikers']]
    color_set = [colordesc(cd) for cd in data['color_set']]
    _unit = unit(data['unit'])
    return {'monikers': monikers, 'color_set': color_set, 'unit': _unit}


def coloraddress(model, asset, coloraddress):
    coloraddress = unicode_string(coloraddress)

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
    for entry in data:
        _asset = asset(model, entry['moniker'])
        _amount = assetamount(_asset, entry['amount'])
        _coloraddress = coloraddress(model, _asset, entry['coloraddress'])
        _address = coloraddress_to_bitcoinaddress(_coloraddress)
        sendmany_entries.append((_asset, _address, _amount))
    return sendmany_entries


def sendmanycsv(model, path):
    path = unicode_string(path)
    entries = []
    with open(path, 'rb') as csvfile:
        for index, csvvalues in enumerate(csv.reader(csvfile)):
            entries.append(_sanitize_csv_input(model, csvvalues, index + 1))
    return entries


def _sanitize_csv_input(model, csvvalues, row):
    if len(csvvalues) != 3:  # must have three entries
        msg = ("CSV entry must have three values 'moniker,address,amount'. "
               "Row %s has %s values!")
        raise InvalidInput(msg % (row, len(csvvalues)))
    _moniker, _coloraddress, _amount = csvvalues
    _asset = asset(model, _moniker)
    _coloraddress = coloraddress(model, _asset, _coloraddress)
    _amount = assetamount(_asset, _amount)
    _address = coloraddress_to_bitcoinaddress(_coloraddress)
    return _asset, _address, _amount


def utxos(utxos):
    def reformat(utxo):
        return {
            'txid': txid(utxo['txid']),
            'outindex': positiveinteger(utxo['outindex'])
        }
    return map(reformat, utxos)


def targets(model, targets):
    def reformat(target):
        _asset = asset(model, target["moniker"])
        _amount = assetamount(_asset, target["amount"])
        _address = coloraddress(model, _asset, target["coloraddress"])
        return {
            "asset": _asset,
            "amount": _amount,
            "coloraddress": _address
        }
    return map(reformat, targets)


def bitcoin_address(address):
    address_set = set(address)
    return address_set.issubset(base58set)


def wif(testnet, wif):
    netcode = 'XTN' if testnet else 'BTC'
    if not validate.is_wif_valid(wif, allowable_netcodes=[netcode]):
        raise InvalidInput("Invalid wif!")
    return wif


def wifs(testnet, wifs):
    return map(lambda w: wif(testnet, w), wifs)
