
usage
-----

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

## How to test the software
 
* Clone/download project.
* Create new virtualenv
* Install requirements
	pip install -r requirements.txt
	./run_tests.sh
 
## Known issues

None, atm.
 
## Getting help

Kevin Markesbery <Kevin.Markesbery@ge.com>
