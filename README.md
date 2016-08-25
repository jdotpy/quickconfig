# QuickConfig
 
**Description**: 

This package provides a way to quickly configure your python applications
from serveral file sources and types and then gives you a consistent way
to access them with error handling. 

  - **Technology stack**: Python 2.7
  - **Status**: Beta
 
## Dependencies

-Python 2.7
 
## Installation

Coming soon.
 
## Usage

	from quickconfig import Configuration

	config = Configuration(Configuration.Env('MYCONFIG'), '/etc/myconfig.json', '~/etc/.myconfig')
	port = config.get('server.port', 25)

	# You can control when/if the configuration raises an exception

	# To raise an exception when any configuration file is missing
	config = Configuration('/etc/myconfig.json', silent_on_missing=False)

	# To silence exceptions for invalid configuration files (problems parsing)
	config = Configuration('/etc/myconfig.json', silent_on_invalid=True)

	# To require at least one configuration source be loaded succesfully
	config = Configuration('/etc/myconfig.json', '/etc/myconfig-2.json', require=True)

	# To require a minimum number of configuration sources be loaded
	config = Configuration('/etc/myconfig.json', '/etc/myconfig-2.json', require=2)

## How to test the software
 
* Clone/download project.
* Create new virtualenv
* Install requirements
	pip install -r requirements.txt
	./run_tests.sh
 
## Known issues

* No support for python 3 :( 
 
## Getting help

https://github.com/jdotpy/quickconfig
