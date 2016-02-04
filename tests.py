from unittest import TestCase
import os
import mock
import copy

from quickconfig import Configuration, SettingNotFound

class TestTools(TestCase):
    def test_env_var(self):
        test_key = 'FOOBAR'
        test_value = 'XI'

        old = os.environ.get('foo', None)
        os.environ[test_key] = test_value
        self.assertEqual(test_value, Configuration.Env(test_key).path)

        if old is not None:
            os.environ[test_key] = old

    def test_sys_arg(self):
        old = Configuration.Arg.source
        
        test_path = '/path/to/example.json'
        test_arg_name = 'config'
        Configuration.Arg.source = ['--' + test_arg_name, test_path]
        arg = Configuration.Arg('config')
        self.assertEqual(arg.path, test_path)

        Configuration.Arg.source = old


class TestInternal(TestCase):
    def test_file_type(self):
        test_path = '/path/to/some/foo.bar.json'
        conf = Configuration()
        t = conf._get_file_type(test_path)
        self.assertEqual(t, 'json')

    def test_file_contents(self):
        test_path = '/path/to/some/foo.bar.json'
        test_value = 'foooooooo'
        conf = Configuration()

        self.assertEqual(conf._get_file_contents(None), None)
        self.assertEqual(conf._get_file_contents(''), None)


    def test_parse_contents(self):
        conf = Configuration()

        JSON_TEST = ('{"key1": "value1"}', {'key1': 'value1'})
        YAML_TEST = ('key1: value1', {'key1': 'value1'})
        INI_TEST = ('[Section]\nkey1 = value1', {'Section': {'key1': 'value1'}, 'defaults': {}})

        
        json_value, _ = conf._parse_contents(JSON_TEST[0], 'json')
        self.assertEqual(json_value, JSON_TEST[1])

        yaml_value, _ = conf._parse_contents(YAML_TEST[0], 'yaml')
        self.assertEqual(yaml_value, YAML_TEST[1])

        ini_value, _ = conf._parse_contents(INI_TEST[0], 'ini')
        self.assertEqual(ini_value, INI_TEST[1])

        # Make sure it doesn't support invalid extensions ;)
        with self.assertRaises(ValueError):
            conf._parse_contents('foobar', 'xml')

        # Make sure a parse error returns None
        with mock.patch('json.loads') as m:
            m.side_effect = ValueError
            value, message = conf._parse_contents(JSON_TEST[0], 'json')
            self.assertEqual(value, None)


class TestGet(TestCase):
    TEST_STRUCTURE = {'key1': {'key2': 'foo', 'key21': ['a', 'b'], 'key3.5': 'bar'}}

    def setUp(self):
        self.conf = Configuration()

    def test_get_from_source(self):
        self.assertEqual(
            self.conf.get_from_source(['key1'], self.TEST_STRUCTURE), 
            self.TEST_STRUCTURE['key1']
        )
        self.assertEqual(
            self.conf.get_from_source(['key1', 'key2'], self.TEST_STRUCTURE),
            self.TEST_STRUCTURE['key1']['key2']
        )
        self.assertEqual(
            self.conf.get_from_source(['key1','key21', '0'], self.TEST_STRUCTURE),
            self.TEST_STRUCTURE['key1']['key21'][0]
        )
        with self.assertRaises(SettingNotFound):
            self.conf.get_from_source(['BAD_KEY'], self.TEST_STRUCTURE)
        with self.assertRaises(SettingNotFound):
            self.conf.get_from_source(['key1', 'BAD_KEY'], self.TEST_STRUCTURE)
        with self.assertRaises(SettingNotFound):
            self.conf.get_from_source(['key1','key21', '2'], self.TEST_STRUCTURE)

    def test_get(self):
        conf = Configuration()
        conf.sources = [{'data': self.TEST_STRUCTURE}]
        conf.get_from_source = mock.Mock()

        conf.get(['key1', 'key2'])
        conf.get_from_source.assert_called_once_with(['key1', 'key2'], self.TEST_STRUCTURE)
        conf.get_from_source.reset_mock()

        conf.get('key1.key2')
        conf.get_from_source.assert_called_once_with(['key1', 'key2'], self.TEST_STRUCTURE)
        conf.get_from_source.reset_mock()
        
        conf.get('key1|key2.5', delimiter='|')
        conf.get_from_source.assert_called_once_with(['key1', 'key2.5'], self.TEST_STRUCTURE)
        conf.get_from_source.reset_mock()


    def test_get_order(self):
        conf = Configuration()
        conf.sources = [{'data': self.TEST_STRUCTURE}]
        conf.get_from_source = mock.Mock()

        # Add a second almost identical source
        TEST_STRUCTURE_2 = copy.deepcopy(self.TEST_STRUCTURE)
        TEST_STRUCTURE_2['Z'] = 'In There'
        self.assertFalse(TEST_STRUCTURE_2 is self.TEST_STRUCTURE)
        conf.sources.append({'data': TEST_STRUCTURE_2})

        # With a bad key, all should be called, check the order
        conf.get_from_source.side_effect = SettingNotFound
        conf.get('key1')
        conf.get_from_source.assert_has_calls([
            mock.call(['key1'], TEST_STRUCTURE_2),
            mock.call(['key1'], self.TEST_STRUCTURE)
        ], any_order=False)
        conf.get_from_source.reset_mock()

        # With a good key, it should stop when it finds it
        conf.get_from_source.side_effect = None
        conf.get('Z')
        conf.get_from_source.assert_called_once_with(['Z'], TEST_STRUCTURE_2)

    def test_default_fallback(self):
        conf = Configuration()
        conf.sources = [{'data': self.TEST_STRUCTURE}]
        conf.get_from_source = mock.Mock()
        conf.get_from_source.side_effect = SettingNotFound
        test_default = 'stuffzors'

        value = conf.get('key1.key2')
        self.assertEqual(value, None)

        value = conf.get('key1.key2', default=test_default)
        self.assertEqual(value, test_default)


class TestLoadSources(TestCase):
    def test_load_source(self):
        conf = Configuration()

        test_origin = '/tmp/test/path.json'
        test_file_type = 'json'
        test_contents = 'test contents'
        test_parsed = {'foo': 'bar'}

        conf._get_file_type = mock.Mock(return_value=test_file_type)
        conf._get_file_contents = mock.Mock(return_value=test_contents)
        conf._parse_contents = mock.Mock(return_value=(test_parsed, None))

        conf.load_source(test_origin)

        self.assertEqual(len(conf.sources), 1)
        built_source = conf.sources[0]
        self.assertEqual(built_source['origin'], test_origin)
        self.assertEqual(built_source['location'], test_origin)
        self.assertEqual(built_source['type'], test_file_type)
        self.assertEqual(built_source['contents'], test_contents)
        self.assertEqual(built_source['data'], test_parsed)
