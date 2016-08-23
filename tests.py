from unittest import TestCase
import os
import copy
try:
    import mock
except ImportError:
    from unittest import mock

from quickconfig import Configuration, ExtractionFailed, Extractor, extract, MissingConfigFileError, InvalidConfigError, RequiredConfigurationError

class TestExtractor(TestCase):
    TEST_STRUCTURE = {
        'key1': {
            'key2': 'foo',
            'key21': ['a', 'b'],
            'key3.5': 'bar'
        },
        'struct1_only': True
    }
    TEST_STRUCTURE_B = {
        'key1': {
            'key2': 'zip',
            'key21': ['x', 'y', 'z'],
            'key3.5': 'ski',
            'key4': 'code'
        }
    }

    def setUp(self):
        self.ex = Extractor(self.TEST_STRUCTURE)

    def test_get_from_source(self):
        # Succesful extractions
        self.assertEqual(
            self.ex.extract(['key1']),
            self.TEST_STRUCTURE['key1']
        )
        self.assertEqual(
            self.ex.extract(['key1', 'key2']),
            self.TEST_STRUCTURE['key1']['key2']
        )
        self.assertEqual(
            self.ex.extract(['key1', 'key21', '0']),
            self.TEST_STRUCTURE['key1']['key21'][0]
        )
        self.assertEqual(
            self.ex.extract('key1.key21.0'),
            self.TEST_STRUCTURE['key1']['key21'][0]
        )
        self.assertEqual(
            self.ex.extract(['key1','key3.5']),
            self.TEST_STRUCTURE['key1']['key3.5']
        )

    def test_fallback(self):
        # Fallback to defaults
        test_default = 'foooooo'
        self.assertEqual(
            self.ex.extract(['BAD_KEY']),
            None
        )
        self.assertEqual(
            self.ex.extract(['BAD_KEY'], default=test_default),
            test_default
        )
        self.assertEqual(
            self.ex.extract(['key1', 'key21', '100']),
            None
        )
        self.assertEqual(
            self.ex.extract('foo.bar.zip.bad_key'),
            None
        )
        with self.assertRaises(KeyError):
            self.ex.extract('BAD.KEY', default=KeyError)
        with self.assertRaises(KeyError):
            self.ex.extract('BAD.KEY', default=KeyError('yooohooo'))

    def test_wrapper(self):
        self.assertEqual(
            extract(self.TEST_STRUCTURE,'key1.key2'), 
            self.TEST_STRUCTURE['key1']['key2']
        )

    def test_source_priority(self):
        ex = Extractor(self.TEST_STRUCTURE, self.TEST_STRUCTURE_B)

        # The last source should take priority over the others
        self.assertEqual(
            ex.extract('key1.key2'),
            self.TEST_STRUCTURE_B['key1']['key2']
        )

        # It should fallback to next source if last doesnt have
        self.assertEqual(
            ex.extract('struct1_only'),
            self.TEST_STRUCTURE['struct1_only']
        )
        self.assertEqual(
            ex.extract('key1.key4'),
            self.TEST_STRUCTURE_B['key1']['key4']
        )

    def test_delimiter(self):
        ex = Extractor(self.TEST_STRUCTURE, delimiter='|')

        self.assertEqual(
            ex.extract('key1|key2'),
            self.TEST_STRUCTURE['key1']['key2']
        )
        self.assertEqual(
            ex.extract('key1|key3.5'),
            self.TEST_STRUCTURE['key1']['key3.5']
        )
        # This should return the fallback as its the wrong delimiter
        self.assertEqual(
            ex.extract('key1.key2'),
            None
        )

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

class TestLoadSources(TestCase):
    test_origin = '/tmp/test/path.json'
    def test_load_source(self):
        conf = Configuration()

        test_file_type = 'json'
        test_contents = 'test contents'
        test_parsed = {'foo': 'bar'}

        conf._get_file_type = mock.Mock(return_value=test_file_type)
        conf._get_file_contents = mock.Mock(return_value=test_contents)
        conf._parse_contents = mock.Mock(return_value=(test_parsed, None))

        conf.load_source(self.test_origin)

        self.assertEqual(len(conf.sources), 1)
        built_source = conf.sources[0]
        self.assertEqual(built_source['origin'], self.test_origin)
        self.assertEqual(built_source['location'], self.test_origin)
        self.assertEqual(built_source['type'], test_file_type)
        self.assertEqual(built_source['contents'], test_contents)
        self.assertEqual(built_source['data'], test_parsed)

    def test_missing_config_file(self):
        conf = Configuration(silent_on_missing=False, silent_on_invalid=False)
        conf._get_file_contents = mock.Mock(return_value=None)
        with self.assertRaises(MissingConfigFileError):
            conf.load_source(self.test_origin)

    def test_config_file_exists(self):
        conf = Configuration(silent_on_missing=True, silent_on_invalid=True)
        conf._get_file_contents = mock.Mock(return_value=None)
        conf.load_source(self.test_origin)
        self.assertEqual(len(conf.sources), 1)

    def test_invalid_config_file(self):
        conf = Configuration(silent_on_missing=False, silent_on_invalid=False)
        conf._get_file_contents = mock.Mock(return_value='{invalid,,,:json')
        with self.assertRaises(InvalidConfigError):
            conf.load_source(self.test_origin)

    def test_required_num_sources(self):
        with mock.patch.object(Configuration, '_get_file_contents') as mock_get_contents:
            mock_get_contents.return_value = '{"a": "first file"}'
            with self.assertRaises(RequiredConfigurationError):
                conf = Configuration('foobar.json', require=2)

    def test_destination(self):
        test_structure = {'a': 1, 'b': 2}

        conf = Configuration()
        conf.load_source(test_structure, destination='sub')
        self.assertEqual(
            list(conf.extractor.sources),
            [{'sub': test_structure}]
        )

        conf = Configuration()
        conf.load_source(test_structure)
        self.assertEqual(list(conf.extractor.sources), [test_structure])

class FunctionalTests(TestCase):
    """ Mostly functional ;) """

    def test_basic(self):
        with mock.patch.object(Configuration, '_get_file_contents') as mock_get_contents:
            mock_get_contents.return_value = '{"a": "first file"}'
            conf = Configuration('/tmp/file1.json')
            mock_get_contents.return_value = 'a: "second file"'
            conf.load_source('/tmp/yaml.yaml')
            self.assertEqual(conf.get('a'), 'second file')
