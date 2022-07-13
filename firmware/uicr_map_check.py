#!/usr/bin/python3
import json
import sys

if (len(sys.argv) < 3):
	print(f"Usage: {sys.argv[0]} <cloud_file> <map_file>")
	exit(1)
cloud_file_name = sys.argv[1]
map_file_name = sys.argv[2]

board_map = json.load(open(map_file_name, 'r'))
cloud_data = json.load(open(cloud_file_name, 'r'))
#except Exception as e:
#	print(f"Unable to open file: {e}")

uicr_per_hardware_version = {}
for it in board_map:
	uicr_per_hardware_version[str(it["hardwareVersion"])] = it["uicr"]

print(uicr_per_hardware_version)

uicr_not_matching = {}

uicr_in_cloud = {}

for stone in cloud_data:
	firmware_version = stone.get("firmwareVersion", None)
	product_type = stone.get("type", None)
	bootloader_version = stone.get("bootloaderVersion", None)
	hardware_version = stone.get("hardwareVersion", None)
	if hardware_version is not None:
		hardware_version = hardware_version[0:11]
	stone_id = stone.get("id", None)
	sphere_id = stone.get("sphereId", None)

	uicr = None
	if "uicr" in stone:
		uicr = stone["uicr"]
		# uicr = {}
		# uicr["board"] = stone_uicr["board"]
		# uicr["hardwareMajor"] = stone_uicr["hardwareMajor"]
		# uicr["hardwareMinor"] = stone_uicr["hardwareMinor"]
		# uicr["hardwarePatch"] = stone_uicr["hardwarePatch"]
		# uicr["reserved1"] = stone_uicr["reserved1"]
		# uicr["productType"] = stone_uicr["productType"]
		# uicr["region"] = stone_uicr["region"]
		# uicr["productFamily"] = stone_uicr["productFamily"]
		# uicr["reserved2"] = stone_uicr["reserved2"]
		# uicr["productionYear"] = stone_uicr["productionYear"]
		# uicr["productionWeek"] = stone_uicr["productionWeek"]
		# uicr["productHousing"] = stone_uicr["productHousing"]
		# uicr["reserved3"] = stone_uicr["reserved3"]

	#print(firmware_version, bootloader_version, hardware_version, uicr)
	if hardware_version is None:
		print("No hardware version")
		continue

	if hardware_version not in uicr_per_hardware_version:
		print("Unknown hardware version:", hardware_version)

		# if hardware_version.startswith("10"):
		# 	print(stone)
		continue

	if uicr is None:
		continue

	mapped_uicr = uicr_per_hardware_version[hardware_version]

	uicr_keys = sorted(mapped_uicr.keys())

	uicr_keys_set = uicr_keys.copy()
	uicr_keys_set.remove("board")

	uicr_keys_compared = uicr_keys.copy()
	uicr_keys_compared.remove("productionYear")
	uicr_keys_compared.remove("productionWeek")
	uicr_keys_compared.remove("productHousing")

	# Check if UICR is set on the crownstone.
	uicr_set = False
	for key in uicr_keys_set:
		if uicr.get(key, 255) != 255:
			uicr_set = True

	if not uicr_set:
		print("UICR not set on stone, ignore")
		continue

	# Keep up all UICRs in the cloud.
	if hardware_version not in uicr_in_cloud:
		uicr_in_cloud[hardware_version] = []
	uicr_in_cloud[hardware_version].append(uicr)

	# Compare values
	match = True
	for key in uicr_keys_compared:
		if uicr.get(key) != mapped_uicr.get(key):
			match = False

	if not match:
		print("UICR does not match:")
		print("cloud:", stone)
		for key in uicr_keys:
			print(f"{key}: cloud={uicr.get(key)} mapped={mapped_uicr.get(key)}")

		# Keep up all the non matching UICRs
		if hardware_version not in uicr_not_matching:
			uicr_not_matching[hardware_version] = []
		# Store as string, so we can easily remove duplicates
		uicr_not_matching[hardware_version].append(str(uicr))

# Remove duplicates from non matching UICRs
for key in uicr_not_matching.keys():
	uicr_not_matching[key] = list(set(uicr_not_matching[key]))

# Print all non matching UICRs
for hardware_version in uicr_not_matching.keys():
	mapped_uicr = uicr_per_hardware_version[hardware_version]
	print(f"Non matching uicr for hardware version {hardware_version}:")
	for entry in uicr_not_matching.get(hardware_version):
		cloud = json.loads(entry.replace("'", '"'))
		for key in sorted(uicr_per_hardware_version[hardware_version].keys()):
			if cloud.get(key) != mapped_uicr.get(key):
				print(f"    {key}: cloud={cloud.get(key)} mapped={mapped_uicr.get(key)}")
		print("")

	# 	print(f"    cloud={entry}")
	# print(f"    mapped={mapped_uicr}")
	# for key in sorted(uicr_per_hardware_version[hardware_version].keys()):
	# 	print(f"    {key}: cloud={uicr_not_matching.get(key)} mapped={mapped_uicr.get(key)}")

print("All UICR combinations found in the cloud (by hardware version):")
for hardware_version in uicr_in_cloud:
	# Remove duplicates
	unique = []
	for entry in uicr_in_cloud[hardware_version]:
		if entry not in unique:
			unique.append(entry)
	uicr_in_cloud[hardware_version] = unique

	mapped_uicr = uicr_per_hardware_version[hardware_version]
	uicr_keys = sorted(mapped_uicr.keys())

	print("")
	print(hardware_version)
	values = {}
	for key in uicr_keys:
		values[key] = []

	for entry in uicr_in_cloud[hardware_version]:
		for key in uicr_keys:
			values[key].append(entry.get(key))

	for key in uicr_keys:
		valuesString = ""
		for value in values[key]:
			valuesString += f"{str(value):5} "
		print(f"    {key:20}: {valuesString}")
