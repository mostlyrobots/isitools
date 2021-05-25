#!/usr/bin/env python3

import sqlite3
import os
import pwd
from datetime import timedelta, datetime
from time import ctime

db_file = '/share/quotas.db'


USERNAME = pwd.getpwuid(os.getuid())[0]


class QuotaReport():

	def __init__(self, spacing, pre='\n\n', end='\n'):
		# The eventual output string to print
		self.output = pre
		self.spacing = spacing
		self.summary = ''
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

	def add_summary_line(self, line, end='\n'):
		self.summary += str(line) + end

	def print(self):
		print(self.output + self.summary + self.end)


class Quota():
	def __init__(self, quota):
		if quota['type'] == 'user':
			self.type = 'user'
			self.filesystem = None
			self.fileset = quota['path'].split('/')[3]
		elif quota['type'] == 'directory':
			self.type = 'group'
			self.filesystem = quota['path'].split('/')[3]
			self.fileset = quota['path'].split('/')[-1]
		else:
			self.type = 'other'
		self.usage = self.hum_sz(quota['usage'])
		self.soft = self.hum_sz(quota['soft'])
		self.hard = self.hum_sz(quota['hard'])
		self.inodes = quota['inodes']
		self.percent_free = round(quota['usage'] / quota['soft'] * 100)
		self.grace_lapsed = False
		if quota['exceeded'] is not None:
			if quota['grace'] is not None:
				grace = timedelta(seconds=int(quota['grace']))
			else:
				grace = 0
			exceeded = datetime.fromtimestamp(int(quota['exceeded']))
			grace_ending = exceeded + grace
			grace_left = grace_ending - datetime.now()
			if grace_left.days > 1:
				self.grace = str(grace_left.days) + ' days'
			elif grace_left.seconds < 0:
				self.grace = 'elaspsed'
				self.grace_lapsed = True
			else:
				self.grace = str(grace_left.hours) + ' hours'
		else:
			self.grace = 'none'

	def hum_sz(self, num, suffix='B'):
		if num is None:
			return 0
		for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
			if abs(num) < 1024.0:
				return "%3.2f%s%s" % (num, unit, suffix)
			num /= 1024.0
		return "%.1f%s%s" % (num, 'Yi', suffix)


def quota_factory(cursor, row):
	d = {}
	for idx, col in enumerate(cursor.description):
		if type(row[idx]) == str and row[idx] == 'None':
			d[col[0]] = None
		else:
			d[col[0]] = row[idx]
	return Quota(d)


db_mtime = ctime(os.stat(db_file).st_ctime)

db_connection = sqlite3.connect(db_file)
db = db_connection.cursor()
db.row_factory = quota_factory

# Get the list of groups (ints) and then convert to strs
usergroups = [str(group) for group in os.getgrouplist(USERNAME, 0)]

# produce a dictionary instead of a list
db.execute(f"SELECT * from quotas where name='{USERNAME}' OR name IN ({','.join(usergroups)}) ORDER BY type DESC, path")
quotas = db.fetchall()
names = [column[0] for column in db.description]

report = QuotaReport(spacing=[30, 17, 11, 11, 11, 6, 9])

report.add_tabular(total_line=True)
report.add_tabular('fileset', 'type', 'used', 'quota', 'limit', '%FULL', 'grace')
report.add_tabular(sum_line=True)

last_filesystem = ''

for q in quotas:
	if q.type == 'group':
		# the purpose of this if statement is to create the label for the next group of filesystems
		# since we know the output from the sqlite3 db is sorted we can rely on this being in order
		if q.filesystem != last_filesystem:
			last_filesystem = q.filesystem
			report.add_tabular(sum_line=True)
			report.add_line(f'>>> Capacity Filesystem: {q.filesystem} (IFS)')
			report.add_tabular(sum_line=True)

	if q.grace_lapsed:
		report.add_summary_line(f"The grace period on {q.fileset} has expired. Writing is disabled until you reduce usage.")
	report.add_tabular(q.fileset, f"blocks ({q.type})", q.usage, q.soft, q.hard, q.percent_free, q.grace)
	report.add_tabular('', f"files ({q.type})", q.inodes, 'none', 'none', '', 'none')

report.add_tabular(total_line=True)

report.print()
print(f'This information was current as of {db_mtime}.')
