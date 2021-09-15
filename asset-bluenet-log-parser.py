#!/usr/bin/env python3
import re

import matplotlib.pyplot as plt
import matplotlib.dates
import json
import sys
import datetime
from itertools import cycle
import numpy as np

def parse(file_name):
	# Example line: [2021-06-28 13:42:03.142532] asset mac=60:c0:bf:27:e5:67 scanned by id=96
	timestampFormat = "%Y-%m-%d %H:%M:%S.%f"
	patternAssetLine = re.compile("\[([^\]]+)\] asset mac=(\S+) scanned by id=(\d+)")

	plot_data = {}

	stones = set()
	assets = set()

	with open(file_name, 'r') as file:
		while True:
			line = file.readline()
			if not line:
				break

			match = patternAssetLine.match(line)
			if not match:
				continue
			timestamp = datetime.datetime.strptime(match.group(1), timestampFormat).timestamp()
			asset_id = match.group(2)
			stone_id = int(match.group(3))

			if asset_id[0:5] == "FF:00":
				# asset_id = "FF:00:00:00:00:00"
				asset_id = "Simulated tag"

			stones.add(stone_id)
			assets.add(asset_id)
			if stone_id not in plot_data:
				plot_data[stone_id] = {}
			if asset_id not in plot_data[stone_id]:
				plot_data[stone_id][asset_id] = {
					"time": [],
					"rssi": [],
				}
			plot_data[stone_id][asset_id]["time"].append(timestamp)
			plot_data[stone_id][asset_id]["rssi"].append(0)

		# Calculate time between scans
		outlier_delta_time = 3600
		print("------------------------- Warning -------------------------")
		print(f"Removing outliers: any time between scans above {outlier_delta_time}")
		print("-----------------------------------------------------------")
		for stone_id in plot_data:
			for asset_id in plot_data[stone_id]:
				plot_data[stone_id][asset_id]["delta_time"] = np.diff(plot_data[stone_id][asset_id]["time"])
				# print("time:", plot_data[stone_id][asset_id]["time"])
				# print("delta_time:", plot_data[stone_id][asset_id]["delta_time"])

				# Remove outliers
				plot_data[stone_id][asset_id]["delta_time"] = np.minimum(plot_data[stone_id][asset_id]["delta_time"],
				                                                         3600)

		# Sort the stones and assets, for nicer plotting
		stones = sorted(stones)
		assets = sorted(assets)

		too_many_assets = len(assets) > 50
		too_many_stones = len(plot_data.keys()) > 10

		if too_many_assets:
			stones_per_figure = 20
		else:
			stones_per_figure = 2 * int(np.ceil(18 / len(assets)))

		if too_many_assets:
			i = 0
			box_data = []
			box_labels = []
			for stone_id in stones:
				if i == 0:
					plt.figure()
					plt.xlabel("Time between scans (s)")

				stone_data = []
				for asset_id in sorted(plot_data[stone_id].keys()):
					stone_data.extend(plot_data[stone_id][asset_id]["delta_time"])
				# print(stone_data)
				box_data.append(stone_data)
				box_labels.append(f"stone {stone_id}")
				i += 1
				if i == stones_per_figure:
					plt.boxplot(box_data, labels=box_labels, vert=False, showfliers=True)
					i = 0
					box_data = []
					box_labels = []
			if i != 0:
				plt.boxplot(box_data, labels=box_labels, vert=False, showfliers=True)
			plt.show()

		else:
			i = 0
			j = 0
			xlim = ()
			fig_counter = 0
			for stone_id in stones:
				if i == 0 and j == 0:
					# Start a new figure
					# subplot_row_count = min(len(plot_data.keys()) - fig_counter * stones_per_figure, stones_per_figure)
					subplot_row_count = int(stones_per_figure / 2)
					fig, axs = plt.subplots(nrows=subplot_row_count, ncols=2, sharex=True)
					if fig_counter != 0:
						plt.xlim(xlim)

					if subplot_row_count == 1:
						axs = [axs]
					for col in range(0, 2):
						axs[subplot_row_count - 1][col].set_xlabel("Time between scans (s)")

				box_data = []
				box_labels = []
				for asset_id in sorted(plot_data[stone_id].keys()):
					box_data.append(plot_data[stone_id][asset_id]["delta_time"])
					box_labels.append(f"{asset_id}")

				axs[i][j].boxplot(box_data, labels=box_labels, vert=False, showfliers=True)
				axs[i][j].set_title(f"stone {stone_id}")
				i += 1
				if i == subplot_row_count:
					i = 0
					j += 1
					if j == 2:
						j = 0
						if fig_counter == 0:
							xlim = plt.xlim()
						fig_counter += 1
			plt.show()

		x = []
		y = []
		line_styles = ['-', '--', ':']
		marker_styles = ['o', 'x', '+', 's', 'v', 'D', '2', '*']

		for stone_id in stones:
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

			for asset_id in sorted(plot_data[stone_id].keys()):
				if not too_many_assets:
					x = []
					y = []
				for t in plot_data[stone_id][asset_id]["time"][1:]:
					x.append(datetime.datetime.fromtimestamp(t))
				y.extend(plot_data[stone_id][asset_id]["delta_time"])

				if not too_many_assets:
					# plt.plot(x, y, next(marker_style_cycler) + next(line_style_cycler), label=f"{asset_id}")
					plt.plot(x, y, next(marker_style_cycler), label=f"{asset_id}")

			if too_many_assets:
				plt.plot(x, y, 'o')
			else:
				plt.legend()
			plt.show()


parse(sys.argv[1])
