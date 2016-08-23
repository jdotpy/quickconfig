from io import open
import argparse
import json
import sys
import os 
import re
from pprint import pprint
try:
    # Python 3
    from configparser import ConfigParser
    from io import StringIO
    base_string = str
except ImportError:
    # Python 2
    from ConfigParser import ConfigParser
    from StringIO import StringIO
    base_string = basestring

try:
    import yaml
except ImportError:
    yaml = None

class EnvironmentVariable():
    def __init__(self, key):
        self.path = os.getenv(key, None)

class CommandArgument():
    source = sys.argv[1:]

    def __init__(self, key):
        parser = argparse.ArgumentParser()
        parser.add_argument('--' + key, help='QuickConfig Configuration File', default=None)
        args, _remaining = parser.parse_known_args(self.source)
        self.path = getattr(args, key, None)

class MissingConfigFileError(IOError):
    pass

class InvalidConfigError(ValueError):
    pass

class RequiredConfigurationError(ValueError):
    pass

class ExtractionFailed(KeyError):
    pass

class Extractor():
    def __init__(self, *sources, **kwargs):
        self.sources = sources
        self.delimiter = kwargs.pop('delimiter', '.')

    def extract(self, path, default=None):
        if isinstance(path, (list, tuple)):
            attrs = path
        else:
            attrs = path.split(self.delimiter)

        for source in reversed(self.sources):
            value = source
            try:
                for attr in attrs:
                    if isinstance(value, (list, tuple)):
                        try:
                            attr = int(attr)
                        except:
                            raise ExtractionFailed()
                    try:
                        value = value.__getitem__(attr)
                    except (KeyError, IndexError, ValueError, AttributeError):
                        raise ExtractionFailed()
                return value
            except ExtractionFailed:
                continue
        if isinstance(default, BaseException):
            raise default
        elif type(default) == type and issubclass(default, BaseException):
            raise default('path not found: ' + '.'.join(attrs))
        else:
            return default

def extract(sources, path, default=None, **options):
    return Extractor(sources, **options).extract(path, default=default)

class Configuration():
    Env = EnvironmentVariable
    Arg = CommandArgument

    def __init__(self, *sources, **options):
        self.sources = []
        self.loaded_sources = []
        self.replace = options.get('replace', False)
        self.require = options.get('require', 0)
        self.silent_on_missing = options.get('silent_on_missing', True)
        self.silent_on_invalid = options.get('silent_on_invalid', False)
        for source in sources:
            self.load_source(source)

        # Support boolean require values that imply 1
        if not isinstance(self.require, int):
            if self.require:
                self.require = 1
            else:
                self.require = 0
        if self.require > len(self.loaded_sources):
            if self.require == 1:
                message = 'At least one configuration source is required.'
            else:
                message = 'At least %d configuration sources are required but only %d are found.' % (self.require, len(self.loaded_sources))
            print('\nConfiguration sources:')
            for source in self.sources:
                print('\t' + source['origin'])
            raise RequiredConfigurationError(message)

    def load_source(self, path, destination='', encoding='utf-8', replace=False):
        if isinstance(path, dict):
            source_info = {
                'origin': path,
                'location': 'Dynamic Data Dictionary',
                'type': None,
                'contents': None,
                'loaded': True,
                'message': 'Success',
                'data': path,
                'destination': destination
            }
        else:
            origin = path
            if isinstance(path, (self.Env, self.Arg)):
                path = path.path
            
            ext = self._get_file_type(path)
            contents = self._get_file_contents(path, encoding)
            if contents is None and not self.silent_on_missing:
                raise MissingConfigFileError('Missing configuration file: ' + origin)

            if contents is None:
                data = None
                message = 'No file contents to parse'
            else:
                data, message = self._parse_contents(contents, ext)
                if data is None and not self.silent_on_invalid:
                    raise InvalidConfigError(origin + ' has invalid configuration: ' + message)

            loaded = data is not None
            source_info = {
                'origin': origin,
                'location': path,
                'type': ext,
                'contents': contents,
                'loaded': loaded,
                'message': message,
                'data': data,
                'destination': destination
            }
            if '--configdebug' in sys.argv:
                pprint('ConfigTest. Added the following config source:')
                pprint(source_info)    
        self.sources.append(source_info)
        self._create_extractor()
        self.loaded_sources = [source for source in self.sources if source['loaded']]
        self.any_loaded = len(self.loaded_sources) > 0 
        self.loaded = len(self.loaded_sources)

    def _create_extractor(self):
        all_source_structs = []
        for source in self.sources:
            destination = source['destination']
            if destination:
                source_data = {destination: source['data']}
            else:
                source_data = source['data']
            all_source_structs.append(source_data)
        self.extractor = Extractor(*all_source_structs)

    def _parse_contents(self, contents, file_type):
        if contents is None:
            return None, 'No content to parse'
        if file_type == 'json':
            try:
                return json.loads(contents), 'Success'
            except ValueError as e:
                return None, str(e)
        elif file_type == 'yaml':
            if yaml is None:
                raise ImportError('A yaml config file was specified but yaml isnt available!')
            try:
                return yaml.load(contents), 'Success'
            except ValueError as e:
                return None, str(e)
        elif file_type == 'ini':
            try:
                buf = StringIO(contents)
                config = ConfigParser()
                if hasattr(config, 'read_file'):
                    config.read_file(buf)
                else:
                    config.readfp(buf)
                data = {'defaults': dict(config.defaults())}
                for section in config.sections():
                    data[section] = dict(config.items(section))
                return data, 'Success'
            except Exception as e:
                return None, str(e)
        else:
            raise ValueError('Invalid config extension: ' + file_type)

    def _get_file_type(self, path):
        if path is None or not isinstance(path, base_string):
            return None
        path, ext = os.path.splitext(path)
        ext = ext[1:] # Remove leading dot
        return ext

    def _get_file_contents(self, path, encoding='utf-8'):
        if not path:
            return None
        path = os.path.expanduser(path)
        try:
            f = open(path, encoding=encoding)
            contents = f.read()
            f.close()
            return contents
        except IOError:
            return None

    def get(self, *args, **kwargs):
        return self.extractor.extract(*args, **kwargs)
