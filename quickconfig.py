import json
import os 
import re
import argparse
from pprint import pprint
import ConfigParser

import StringIO
import sys

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

class SettingNotFound(KeyError):
    pass

class Configuration():
    Env = EnvironmentVariable
    Arg = CommandArgument

    def __init__(self, *sources, **options):
        self.sources = []
        self.replace = options.get('replace', False)
        for source in sources:
            self.load_source(source)

    def load_source(self, path, destination='', encoding='utf-8', replace=False):
        origin = path
        if isinstance(path, (self.Env, self.Arg)):
            path = path.path
        ext = self._get_file_type(path)
        contents = self._get_file_contents(path, encoding)
        data, message = self._parse_contents(contents, ext)
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
            print 'ConfigTest. Added the following config source:'
            pprint(source_info)    
        self.sources.append(source_info)

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
                buf = StringIO.StringIO(contents)
                config = ConfigParser.ConfigParser()
                config.readfp(buf)
                data = {'defaults': dict(config.defaults())}
                for section in config.sections():
                    data[section] = dict(config.items(section))
                return data, 'Success'
            except Exception:
                return None, str(e)
        else:
            raise ValueError('Invalid config extension: ' + file_type)

    def _get_file_type(self, path):
        if path is None:
            return None
        path, ext = os.path.splitext(path)
        ext = ext[1:] # Remove leading dot
        return ext

    def _get_file_contents(self, path, encoding='utf-8'):
        if not path:
            return None
        path = os.path.expanduser(path)
        try:
            with open(path, 'r') as f:
                return f.read().decode('utf-8')
        except IOError:
            return None

    def get(self, path, default=None, delimiter='.'):
        if isinstance(path, basestring):
            attrs = path.split(delimiter)
        else:
            attrs = path
        for source in reversed(self.sources):
            try:
                return self.get_from_source(attrs, source['data'])
            except SettingNotFound:
                continue
        return default

    def get_from_source(self, attrs, source_data):
        value = source_data
        for attr in attrs:
            if isinstance(value, list):
                try:
                    attr = int(attr)
                except:
                    raise SettingNotFound()
            try:
                value = value.__getitem__(attr)
            except (KeyError, IndexError, ValueError, AttributeError):
                raise SettingNotFound()
        return value
