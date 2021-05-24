import sqlite3
import os
import pwd
from datetime import timedelta, datetime


def get_username():
    return pwd.getpwuid(os.getuid())[0]


def dict_factory(cursor, row):
	d = {}
	for idx, col in enumerate(cursor.description):
		if type(row[idx]) == str and row[idx] == 'None':
			d[col[0]] = None
		else:
			d[col[0]] = row[idx]
	return d


def sz(num, suffix='B'):
	if num is None:
		return 0
	for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
		if abs(num) < 1024.0:
			return "%3.2f%s%s" % (num, unit, suffix)
		num /= 1024.0
	return "%.1f%s%s" % (num, 'Yi', suffix)


db_file = '/ifs/harbor/share/quotas.db'

db_connection = sqlite3.connect(db_file)

db = db_connection.cursor()

# Get the list of groups (ints) and then convert to strs
usergroups = [str(group) for group in os.getgrouplist(get_username(), 0)]

# produce a dictionary instead of a list
db.row_factory = dict_factory
db.execute(f"SELECT * from quotas where name='{get_username()}' OR name IN ({','.join(usergroups)}) ORDER BY type DESC, path")
quotas = db.fetchall()
names = [column[0] for column in db.description]


class QuotaReport():
	def __init__(self, spacing, pre='\n\n', end='\n'):
		# The eventual output string to print
		self.output = pre
		self.spacing = spacing
		self.end = end

	def add_tabular(self, *args, total_line=False, sum_line=False, end='\n'):
		if total_line is True:
			self.output += ("-" * (sum(self.spacing) - 1)) + end
			return()
		if sum_line is True:
			args = ['-'*80] * len(self.spacing)
		for arg, width in zip(args, self.spacing):
			if type(arg) == 'int':
				self.output += str(arg)[:width - 1].rjust(width - 1) + ' '
			else:
				self.output += str(arg)[:width - 1].ljust(width - 1) + ' '
		self.output += end

	def add_line(self, line, end='\n'):
		self.output += str(line) + end

	def print(self):
		print(self.output + self.end)


report = QuotaReport(spacing=[30, 17, 11, 11, 11, 6, 9])


warn_grace = False
warn_soft = False
warn_hard = False

report.add_tabular(total_line=True)
report.add_tabular('fileset', 'type', 'used', 'quota', 'limit', '%FULL', 'grace')
report.add_tabular(sum_line=True)

filesystem = str()
for q in quotas:
	path = q['path'].split('/')[3]

	if q['type'] == 'directory':
		qtype = 'group'
		if path != filesystem:
			filesystem = path
			report.add_tabular(sum_line=True)
			report.add_line(f'>>> Capacity Filesystem: {filesystem} (IFS)')
			report.add_tabular(sum_line=True)
		path = q['path'].split('/')[-1]

	elif q['type'] == 'user':
		qtype = 'user'
	else:
		qtype = 'other'

	if q['grace'] is not None:
		grace = timedelta(seconds=int(q['grace']))

	if q['exceeded'] is not None:
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

	if q['usage'] is not None:
		if q['hard'] is not None:
			if q['hard'] < q['usage']:
				warn_hard = 'Exceeding your hard limit is preventing you from writing.\n'
			elif q['usage'] / q['hard'] > .9:
				warn_hard = 'You have exceeded your soft limit, you must remove files before your grace expires or you will not be able to write.\n'
				warn_hard += 'You are near your hard limit which may prevent you from writing.'
			elif q['soft'] is not None and q['usage'] / q['soft'] > .9:
				warn_soft = 'You are near your soft limit which may prevent you from writing.\n'

	print(q['soft'], q['usage'], type(q['soft']))
	report.add_tabular(path, f"blocks ({qtype})", sz(q['usage']), sz(q['soft']), sz(q['hard']), round(q['usage'] / q['soft'] * 100), grace_left_str)
	report.add_tabular('', f"files ({qtype})", q['inodes'], 'none', 'none', '', 'none')

report.add_tabular(total_line=True)

if warn_hard:
	report.add_line(warn_hard)

if warn_grace:
	report.add_line("The grace period on one of the directories you use has elasped.\nThis means that you can no longer write files to this location.\n")

report.print()
