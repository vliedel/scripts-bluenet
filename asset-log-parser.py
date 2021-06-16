#!/usr/bin/env python3

import matplotlib.pyplot as plt
import matplotlib.dates
import json
import sys
import datetime
from itertools import cycle
import numpy as np

def parse(file_name):
	# Example line:
	# {"event":"ASSET_REPORT","clientSecret":"CrownstoneBlyottMapper","data":[{"cid":41,"cm":"D6:93:69:57:A6:09","am":"60:C0:BF:28:01:0F","r":-54,"c":37,"t":1623241651536},{"cid":41,"cm":"D6:93:69:57:A6:09","am":"60:C0:BF:27:E5:67","r":-64,"c":37,"t":1623241652005}],"timestamp":1623241652230}$$
	# Unwrapped:
	# {
	# 	"event":"ASSET_REPORT",
	# 	"clientSecret":"CrownstoneBlyottMapper",
	# 	"data":[
	# 	    {
	# 	        "cid":41,
	# 	        "cm":"D6:93:69:57:A6:09",
	# 	        "am":"60:C0:BF:28:01:0F",
	# 	        "r":-54,
	# 	        "c":37,
	# 	        "t":1623241651536
	# 	    },
	# 	    {
	# 	        "cid":41,
	# 	        "cm":"D6:93:69:57:A6:09",
	# 	        "am":"60:C0:BF:27:E5:67",
	# 	        "r":-64,
	# 	        "c":37,
	# 	        "t":1623241652005
	# 	    }
	# 	],
	# 	"timestamp":1623241652230
	# }
	# $$

	plot_data = {}

	# Keep up number of assets
	assets = set()

	with open(file_name, 'r') as file:
		while True:
			line = file.readline()
			if not line:
				break
			line = line.strip()[0:-2] # Line ends with "$$\n"
			data = json.loads(line)["data"]
			for d in data:
				stone_id = d["cid"]
				asset_id = d["am"]
				if asset_id[0:5] == "FF:00":
					# asset_id = "FF:00:00:00:00:00"
					asset_id = "Simulated tag"


				assets.add(asset_id)
				if stone_id not in plot_data:
					plot_data[stone_id] = {}
				if asset_id not in plot_data[stone_id]:
					plot_data[stone_id][asset_id] = {
						"time": [],
						"rssi": [],
					}
				plot_data[stone_id][asset_id]["time"].append(d["t"])
				plot_data[stone_id][asset_id]["rssi"].append(d["r"])


	# Calculate time between scans:
	for stone_id in plot_data:
		for asset_id in plot_data[stone_id]:
			plot_data[stone_id][asset_id]["delta_time"] = np.diff(plot_data[stone_id][asset_id]["time"]) / 1000.0
			# print("time:", plot_data[stone_id][asset_id]["time"])
			# print("delta_time:", plot_data[stone_id][asset_id]["delta_time"])


	too_many_assets = len(assets) > 20
	too_many_stones = len(plot_data.keys()) > 10

	if too_many_assets:
		stones_per_figure = 18
	else:
		stones_per_figure = int(np.ceil(15 / len(assets)))


	if too_many_assets:
		i = 0
		box_data = []
		box_labels = []
		for stone_id in plot_data:
			if i == 0:
				plt.figure()
				plt.xlabel("Time between scans (s)")

			stone_data = []
			for asset_id in plot_data[stone_id]:
				stone_data.extend(plot_data[stone_id][asset_id]["delta_time"])
			print(stone_data)
			box_data.append(stone_data)
			box_labels.append(f"stone {stone_id}")
			i += 1
			if i == stones_per_figure:
				plt.boxplot(box_data, labels=box_labels, vert=False, showfliers=False)
				i = 0
				box_data = []
				box_labels = []
		if i != 0:
			plt.boxplot(box_data, labels=box_labels, vert=False, showfliers=False)
		plt.show()

	else:
		i = 0
		fig_counter = 0
		for stone_id in plot_data:
			if i == 0:
				# Start a new figure
				subplot_count = min(len(plot_data.keys()) - fig_counter * stones_per_figure, stones_per_figure)
				fig, axs = plt.subplots(nrows=subplot_count, sharex=True)
				if subplot_count == 1:
					axs = [axs]
				plt.xlabel("Time between scans (s)")

			box_data = []
			box_labels = []
			for asset_id in plot_data[stone_id]:
				box_data.append(plot_data[stone_id][asset_id]["delta_time"])
				box_labels.append(f"{asset_id}")

			axs[i].boxplot(box_data, labels=box_labels, vert=False, showfliers=False)
			axs[i].set_title(f"stone {stone_id}")
			i += 1
			if i == stones_per_figure:
				fig_counter += 1
				i = 0
		plt.show()




	x = []
	y = []
	line_styles = ['-', '--', ':']
	marker_styles = ['o', 'x', '+', 's', 'v', 'D', '2', '*']

	for stone_id in plot_data:
		plt.figure()
		plt.title(f"Scanned assets by crownstone {stone_id}")
		plt.ylabel("Time since previous scan (s)")
		plt.xlabel("Time")
		# plt.xticks(rotation=90)
		ax = plt.gca()
		xfmt = matplotlib.dates.DateFormatter('%Y-%m-%d\n%H:%M:%S')
		ax.xaxis.set_major_formatter(xfmt)
		line_style_cycler = cycle(line_styles)
		marker_style_cycler = cycle(marker_styles)

		for asset_id in plot_data[stone_id]:
			if not too_many_assets:
				x = []
				y = []
			prev_time = None
			for t in plot_data[stone_id][asset_id]["time"]:
				if prev_time is None:
					delta_time = 0
				else:
					delta_time = t - prev_time
				prev_time = t
				y.append(delta_time / 1000.0)
				x.append(datetime.datetime.fromtimestamp(t / 1000.0))

			if not too_many_assets:
				# plt.plot(x, y, next(marker_style_cycler) + next(line_style_cycler), label=f"{asset_id}")
				plt.plot(x, y, next(marker_style_cycler), label=f"{asset_id}")

		if too_many_assets:
			plt.plot(x, y, 'o')
		else:
			plt.legend()
		plt.show()

parse(sys.argv[1])
