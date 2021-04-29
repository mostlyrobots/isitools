import sqlite3
import os
import pwd
from datetime import timedelta, datetime


def get_username():
    return pwd.getpwuid(os.getuid())[0]


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def sz(num, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.2f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


db_file = 'instance/quotas.db'

db_connection = sqlite3.connect(db_file)

db = db_connection.cursor()

# produce a dictionary instead of a list
db.row_factory = dict_factory
db.execute(f"SELECT * from quotas where name='{get_username()}' ORDER BY type")
quotas = db.fetchall()
names = [column[0] for column in db.description]


def lquota(*args):
	output = ''
	spacing = [9, 11, 11, 11, 17, 17]
	for arg in args:
		width = spacing.pop()
		if type(arg) == 'int':
			output += str(arg)[:width - 1].rjust(width - 1) + ' '
		else:
			output += str(arg)[:width - 1].ljust(width - 1) + ' '
	return output + '\n'


warn_grace = False
warn_soft = False
warn_hard = False

o = "\n\n" + ("-" * 75) + '\n'
o += lquota('fileset', 'type', 'used', 'quota', 'limit', 'grace')
o += lquota(*['-'*20] * 6)
for q in quotas:
	if q['type'] == 'directory':
		qtype = 'group'
	elif q['type'] == 'user':
		qtype = 'user'
	else:
		qtype = 'other'
	path = q['path'].split('/')[3]
	if q['grace'] != 'None':
		grace = timedelta(seconds=int(q['grace']))
	if q['exceeded'] != 'None':
		exceeded = datetime.fromtimestamp(int(q['exceeded']))
		grace_ends = exceeded + grace
		grace_left = grace_ends - datetime.now()
		if grace_left.days > 1:
			grace_left_str = str(grace_left.days) + ' days'
		elif grace_left.seconds < 0:
			grace_left_str = 'elaspsed'
			grace_elapsed = True
		else:
			grace_left_str = str(grace_left.hours) + ' hours'
	else:
		grace_left_str = 'none'
	if q['hard'] < q['usage']:
		warn_hard = 'Exceeding your hard limit is preventing you from writing.\n'
	elif q['hard'] / q['usage'] > .9:
		warn_hard = 'You have exceeded your soft limit, you must remove files before your grace expires or you will not be able to write.\n'
		warn_hard = 'You are near your hard limit which may prevent you from writing.\n'
	elif q['soft'] / q['usage'] > .9:
		warn_soft = 'You are near your soft limit which may prevent you from writing.\n'
	o += lquota(path, f"blocks ({qtype})", sz(q['usage']), sz(q['soft']), sz(q['hard']), grace_left_str)
	o += lquota('', f"files ({qtype})", q['inodes'], 'none', 'none', 'none')

if warn_hard:
	o += "You have less than 10% available space until you reach your hard limit."
if warn_grace:
	o += "The grace period on one of the directories you use has elasped.\n"
	o += "This means that you can no longer write files to this location.\n"

print(o)

LINUX_QUOTA = """
---------------------------------------------------------------------------
fileset          type                   used      quota      limit    grace
---------------- ---------------- ---------- ---------- ---------- --------
home             blocks (user)         0.00K     30.00G     35.00G     none
                 files  (user)            18     300000    1000000     none
scratch          blocks (user)         0.00K    100.00G      5.00T     none
                 files  (user)             1   10000000   20000000     none
---------------- ---------------- ---------- ---------- ---------- --------
>>> Capacity Filesystem: project2 (GPFS)
---------------- ---------------- ---------- ---------- ---------- --------
jpbeck           blocks (group)        0.00K    500.00G    550.00G     none
                 files  (group)            1     575000     632500     none
---------------------------------------------------------------------------
"""
