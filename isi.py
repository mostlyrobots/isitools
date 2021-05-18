import urllib3

from isi_sdk_8_2_2 import ApiClient, ProtocolsApi, Configuration, QuotaApi, rest
import yaml

import sqlite3

# Suppress certificate warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

config = Configuration()
with open('instance/isi.yml', "r") as yamlfile:
	c = yaml.safe_load(yamlfile)
	config.username = c['username']
	config.password = c['password']
	config.verify_ssl = c['verify_ssl']
	config.host = f"https://{c['host']}:8080"
	config.db_file = c['db_file']

db_connection = sqlite3.connect(config.db_file)
db = db_connection.cursor()
db.execute("DROP TABLE IF EXISTS quotas;")
db.execute("""
CREATE TABLE quotas
	(type text, path text, advisory int, hard int, soft int, exceeded int, grace int, inodes int, usage int, efficiency real, name text);
""")
api_client = ApiClient(config)
# protocols_api = ProtocolsApi(api_client)
quota_api = QuotaApi(api_client)

try:
	quotas = quota_api.list_quota_quotas(resolve_names=True).quotas
except rest.ApiException as err:
	print(f"Api Exception: {err}")

for quota in quotas:
	cur = {
		'type': quota.type,
		'path': quota.path,
		'advisory': quota.thresholds.advisory,
		'hard': quota.thresholds.hard,
		'soft': quota.thresholds.soft,
		'exceeded': quota.thresholds.soft_last_exceeded,
		'grace': quota.thresholds.soft_grace,
		'inodes': quota.usage.inodes,
		'usage': quota.usage.to_dict()[quota.thresholds_on[:-4]],
		'efficiency': quota.efficiency_ratio
	}
	if quota.type == "user" and quota.persona.name is not None:
		cur['name'] = quota.persona.name.split('\\')[-1]
	elif quota.type == "directory":
		cur['name'] = 'tbd'
	keys = ','.join(cur.keys())
	values = ','.join('"' + str(x) + '"' for x in cur.values())
	insert_sql = f"INSERT INTO quotas ({keys}) VALUES ({values});"
	db.execute(insert_sql)

db_connection.commit()
db_connection.close()
