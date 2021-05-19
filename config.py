import yaml
from isi_sdk_8_2_2 import Configuration

import urllib3

# Suppress certificate warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Config():
	def __init__(self):
		self.configuration = {}

	@property
	def quotas_db_file(self):
		return(self.configuration['quotas_db_file'])

	@quotas_db_file.setter
	def quotas_db_file(self, value):
		self.configuration['quotas_db_file'] = value


# instanciate the application configuration
config = Config()

# instanciate the apiconfig
isi_config = Configuration()

# and load the two configs with stuff from the yaml file
with open('instance/isi.yml', "r") as yamlfile:
	c = yaml.safe_load(yamlfile)
	isi_config.username = c['username']
	isi_config.password = c['password']
	isi_config.verify_ssl = c['verify_ssl']
	isi_config.host = f"https://{c['host']}:8080"
	config.quotas_db_file = c['quotas_db_file']
