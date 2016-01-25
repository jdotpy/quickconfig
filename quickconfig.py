import json
import os 
try:
    import yaml
except ImportError:
    yaml = None

class EnvironmentVariable():
    def __init__(self, key):
        self.path = os.getenv(key, None)

class SettingNotFound(KeyError):
    pass

class Configuration():
    Env = EnvironmentVariable

    def __init__(self, *sources, **options):
        self.sources = []
        self.replace = options.get('replace', False)
        for source in sources:
            self.load_source(source)

    def load_source(self, path, destination='', encoding='utf-8', replace=False):
        origin = path
        if isinstance(path, self.Env):
            path = path.path
        ext = self._get_file_type(path)
        contents = self._get_file_contents(path, encoding)
        data, message = self._parse_contents(contents, ext)
        loaded = data is not None
        self.sources.append({
            'origin': origin,
            'location': path,
            'type': ext,
            'contents': contents,
            'loaded': loaded,
            'message': message,
            'data': settings,
            'destination': destination
        })

    def _parse_contents(self, contents, file_type):
        if contents is None:
            return None
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
        else:
            raise ValueError('Invalid config extension: ' + file_type)

    def _get_file_type(self, path):
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
        except KeyboardInterrupt:
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
            except (KeyError, IndexError, ValueError):
                raise SettingNotFound()
        return value
