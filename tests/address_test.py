import unittest

from address import Address, TestnetAddress, InvalidAddressError, b2a_base58

class TestAddressGeneration(unittest.TestCase):

    def setUp(self):
        self.keys = (
            "1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj",
            "5Kb8kLf9zgWQnogidDA76MzPL6TsZZY36hWXMssSzNydYXYB9KF")
        self.testnet_keys = (
            "n4ogjNUzm6cWSe1yuQMibAVtxX1dHzvSBz",
            "93CJwPyxPQ7K7fHNHW89acERb7BEVs9JFcgjTLCBv8VfRaaUU17",
            )

    def test_invalid_address(self):
        """Invalid addresses should raise an exception
        """
        invalid_pub = "2222222222222222222222222222222222"
        invalid_priv = "666666666666666666666666666666666666666666666666666"
        with self.assertRaises(InvalidAddressError):
            Address(self.keys[0], invalid_priv)
        with self.assertRaises(InvalidAddressError):
            Address(invalid_pub, self.keys[1])

    def test_valid_address(self):
        """Test the address generation goes through:
        from https://en.bitcoin.it/wiki/Private_key
        5Kb8kLf9zgWQnogidDA76MzPL6TsZZY36hWXMssSzNydYXYB9KF
        maps to 1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj
        """
        address = Address(*self.keys)
        self.assertTrue(address)

    def test_raw_privkey(self):
        address = Address(*self.keys)
        self.assertEqual(
            address.rawPrivkey().encode('hex'),
            "e9873d79c6d87dc0fb6a5778633389f4453213303da61f20bd67fc233aa33262")
        
    def test_raw_pubkey(self):
        address = Address(*self.keys)
        self.assertEqual(
            address.rawPubkey().encode('hex'),
            "7ac00f979ff0df2fdcb65761dc8f9ef8b37142db")

    def test_ecdsa_key(self):
        address = Address(*self.keys)
        ecdsa_key = address.ecdsaPrivkey()
        address2 = Address.fromPrivkey(ecdsa_key)
        self.assertEqual(address.privkey, address2.privkey)

    def test_address_generation(self):
        test_key = 'a' * 32
        address = Address.new(test_key)
        self.assertEqual(address.privkey,
            "5JZB2s2RCtRUunKiqMbb6rAj3Z7TkJwa8zknL1cfTFpWoQArd6n")
        self.assertEqual(address.rawPrivkey(), test_key)
        self.assertTrue(Address.new())

    def test_master_key_address_generation(self):
        test_master_key = '0' * 32
        color_string = '0'
        index = 0
        address = Address.fromMasterKey(test_master_key, color_string, index)
        self.assertEqual(
            address.privkey,
            '5KjWca2NdTm5DMdPC1WBzEtaZ86wVL1Sd7FNnKBvF6H782HgABK')

    def test_from_object(self):
        address = Address(*self.keys)
        data = {'pubkey':self.keys[0], 'privkey':self.keys[1]}
        address2 = Address.fromObj(data)
        self.assertEqual(address.privkey, address2.privkey)

    def test_raw_to_address(self):
        address = Address(*self.keys)
        self.assertEqual(
            address.pubkey,
            Address.rawPubkeyToAddress(address.rawPubkey()))

    def test_json_data(self):
        address = Address(*self.keys)
        self.assertEqual(
            address.getJSONData(),
            {'pubkey':self.keys[0], 'privkey':self.keys[1]})

    def test_testnet(self):
        invalid_pub = "2222222222222222222222222222222222"
        invalid_priv = "666666666666666666666666666666666666666666666666666"
        with self.assertRaises(InvalidAddressError):
            TestnetAddress(self.testnet_keys[0], invalid_priv)
        with self.assertRaises(InvalidAddressError):
            TestnetAddress(invalid_pub, self.testnet_keys[1])
        address = TestnetAddress(*self.testnet_keys)
        self.assertTrue(address)


if __name__ == '__main__':
    unittest.main()
