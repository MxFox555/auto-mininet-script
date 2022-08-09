#!/usr/bin/python

from bs4 import BeautifulSoup
from math import sin, cos, acos, radians

# Requires package "BeautifulSoup" (pip install bs4)
# Run code with command: python3 auto-mininet.py
# Insert the .graphml file
# Use 1 or 0 (Boolean vlaues) to tell the program if you want one host attached to each switch


# Used to calculate delay betwween switches 
class CalculateDelay():
	# start_point and end_point are dicts of: {'Latitude':X, 'Longitude':X}
	def __init__(self, start_point, end_point):
		self.sp = start_point
		self.ep = end_point

	def calculate(self):
		eq_1 = self.eqn_1()
		eq_2 = self.eqn_2()
		return eq_1/eq_2 # Latency in ms

	# Find length of cables
	def eqn_1(self):
		sin_prt = sin(radians(self.ep['la'])) * sin(radians(self.sp['la']))
		cos_prt = cos(radians(self.ep['la'])) * cos(radians(self.sp['la'])) * cos(radians(self.ep['lo']) - radians(self.sp['lo']))
		dist = acos(sin_prt + cos_prt) * 6378137 # Radius of earth (m)
		return dist*1000

	# Find speed of signal
	def eqn_2(self, reflective_factor=1.52): # Reflective factor of fibre optics ~1.52
		return 3*(10**8)/reflective_factor

# Main class to create the file
class AutoMininet():
	# Set file and read the xml data
	def set_file(self, file, hosts):
		self.name = file.split(' ')[0].split('.')[0].split('/')[-1]
		self.hosts = hosts
		with open(file, 'r') as f:
			data = f.read()
		self.bs_file = BeautifulSoup(data, "xml")
		self.attr_dict = self.get_attr_map()
		print('Set file to:', file)

	# Find what each key correlates to
	def get_attr_map(self):
		attr_dict = {}
		for key in self.bs_file.find_all('key'):
			attr_dict[key['id']] = key['attr.name']
		return attr_dict

	# Get the switches in a dict format
	def make_switches(self):
		switches = self.bs_file.find_all('node')
		switches_dict = {}
		for sw in switches:
			for data in sw.find_all('data'):
				if sw['id'] not in switches_dict:
					switches_dict[sw['id']] = {}
				switches_dict[sw['id']][self.attr_dict[data['key']]] = data.get_text().replace(" ", "_")
		return switches_dict

	# Get the edges in a dict format
	def make_edges(self):
		edges = self.bs_file.find_all('edge')
		edges_dict = {}
		for ed in edges:
			for data in ed.find_all('data'):
				if ed['source']+'-'+ed['target'] not in edges_dict:
					edges_dict[ed['source']+'-'+ed['target']] = {}
				edges_dict[ed['source']+'-'+ed['target']]['source'] = ed['source']
				edges_dict[ed['source']+'-'+ed['target']]['target'] = ed['target']
				edges_dict[ed['source']+'-'+ed['target']][self.attr_dict[data['key']]] = data.get_text()
		return edges_dict

	# Make the lines of code	
	def make_code(self):
		lines = []
		lines.append('#!/usr/bin/python\n')
		lines.append('from mininet.topo import Topo\n')
		lines.append('class ' + self.name + 'Topo(Topo):\n')
		lines.append('	def __init__(self):\n')
		lines.append('		Topo.__init__(self)\n')

		# Work with the switches to get them in a python format
		sw = self.make_switches()
		hosts = []
		host_links = []
		lines.append('\n')
		lines.append('		#Add Switches\n')
		for s in sw:
			lines.append('		' + sw[s]['label'] + ' = self.addSwitch("s'+s+'")\n')
			if self.hosts:
				hosts.append('		' + sw[s]['label'] + '_Host = self.addHost("h'+s+'")\n')
				host_links.append('		' + 'self.addLink("s'+s+'", "h'+s+'" )\n')
		lines.append('\n')
		lines.append('		#Add Hosts\n')
		for h in hosts:
			lines.append(h)
		lines.append('\n')
		lines.append('		#Add Switch-Host links\n')
		for l in host_links:
			lines.append(l)

		# Work with the edges to get them in a python format
		lines.append('\n')
		lines.append('		#Add Links\n')
		ed = self.make_edges()
		for e in ed:
			# 'bw' is for Bandwidth value
			bw = 0
			try:
				# If in Gbps convert to Mbps
				if ed[e]['LinkLabel'][-4:] == 'Gbps':
					bw = str(float(ed[e]['LinkLabel'][1:-4].strip())*1000).split('.')[0]
					#print(str(float(ed[e]['LinkLabel'][1:-4].strip())*1000).split('.')[0])
				elif ed[e]['LinkLabel'][-4:] == 'Mbps':
					bw = ed[e]['LinkLabel'][1:-4].strip()
			except KeyError as ke:
				# No bandwidth noted
				bw = None

			# Calculate delay
			delay = 0
			try:
				delay_obj = CalculateDelay({
						'la':float(sw[ed[e]['source']]['Latitude']),
						'lo':float(sw[ed[e]['source']]['Longitude']),
					},
					{
						'la':float(sw[ed[e]['target']]['Latitude']),
						'lo':float(sw[ed[e]['target']]['Longitude']),
					})
				delay = delay_obj.calculate()
			except KeyError:
				delay = None
			line_str = '		self.addLink(' + sw[ed[e]['source']]['label'] + ', ' + sw[ed[e]['target']]['label']
			if bw != None:
				line_str += ', bw=' + str(bw)
			if delay != None:
				line_str += ', delay="' + str(delay) + 'ms"'
			line_str += ')\n'
			lines.append(line_str)

		lines.append('\n')
		lines.append('topos = {"' + self.name + '": (lambda: ' + self.name + 'Topo())}\n')
		self.make_file(lines, (self.name + '_mininet.py'))
		print('Done! file is in same directory as this script called', (self.name + '_mininet.py'))

	# Make the file with provided lines and name
	def make_file(self, lines, file_name):
		write_file = open(file_name, "w+")
		for ln in lines:
			write_file.write(ln)
		write_file.close()


# Entrypoint
if __name__ == '__main__':	
	am = AutoMininet()
	am.set_file(input('graphml file: '), bool(int(input('Add hosts?(1, 0): '))))
	am.make_code()
