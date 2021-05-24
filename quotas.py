from isi_sdk_8_2_2 import QuotaApi, rest
from config import config
from isi import isi_api

import sqlite3
import os


db_connection = sqlite3.connect(config.quotas_db_file)
db = db_connection.cursor()
db.execute("DROP TABLE IF EXISTS quotas;")
db.execute("""
CREATE TABLE quotas
	(type text, path text, advisory int, hard int, soft int, exceeded int, grace int, inodes int, usage int, efficiency real, name text);
""")

quota_api = QuotaApi(isi_api)

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
		try:
			cur['name'] = str(os.stat(quota.path).st_gid)
		except FileNotFoundError:
			cur['name'] = str(99)
	keys = ','.join(cur.keys())
	values = ','.join('"' + str(x) + '"' for x in cur.values())
	insert_sql = f"INSERT INTO quotas ({keys}) VALUES ({values});"
	db.execute(insert_sql)

db_connection.commit()
db_connection.close()
