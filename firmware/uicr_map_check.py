#!/usr/bin/python3
import json
import sys
import re

PRINT_COMPARES = False

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

uicr_keys = sorted(uicr_per_hardware_version[str(board_map[0]["hardwareVersion"])].keys())


uicr_not_matching = {}

uicr_in_cloud = {}

unknown_hardware_versions = []

release_firmware_version_regex = re.compile("\d+\.\d+\.\d+")

#release_hardware_version_regex = re.compile("\d+[A-Z0-9]{6}")
release_hardware_version_regex = re.compile("\d{11}")

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

		if release_hardware_version_regex.match(hardware_version):
			unknown_hardware_versions.append(hardware_version)

	if uicr is None:
		continue

	# Due to a bug in the android app, the key "productionYear" was named "producitonYear" for some time.
	# Fix this here
	if "productionYear" not in uicr and "producitonYear" in uicr:
		uicr["productionYear"] = uicr["producitonYear"]

	uicr_keys_set = uicr_keys.copy()
	uicr_keys_set.remove("board")

	# Check if UICR is set on the crownstone.
	uicr_set = False
	for key in uicr_keys_set:
		if uicr.get(key, 255) != 255:
			uicr_set = True

	if not uicr_set:
		print("UICR not set on stone, ignore")
		continue

	if not release_firmware_version_regex.match(firmware_version):
		print("Non-release firmware version, ignore")
		continue

	# Keep up all UICRs in the cloud.
	if hardware_version not in uicr_in_cloud:
		uicr_in_cloud[hardware_version] = []
	uicr_in_cloud[hardware_version].append(uicr)

	# Compare UICR from cloud with mapped UICR
	if hardware_version not in uicr_per_hardware_version:
		continue
	mapped_uicr = uicr_per_hardware_version[hardware_version]

	uicr_keys_compared = uicr_keys.copy()
	uicr_keys_compared.remove("productionYear")
	uicr_keys_compared.remove("productionWeek")
	uicr_keys_compared.remove("productHousing")

	match = True
	for key in uicr_keys_compared:
		if uicr.get(key) != mapped_uicr.get(key):
			match = False

	if not match:
		if PRINT_COMPARES:
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

print("")
print("All unknown release hardware version strings:")
print(list(set(unknown_hardware_versions)))

print("Known unknown release hardware version strings:")
print("10108000400: board=1100 aka CR01R02v4")
print("10103020000: board=1007 aka ACR01B7B / ACR01B9C / ACR01B9E / ACR01B9F / ACR01B10A")
print("10103010000: board=1004 aka ACR01B1E")
print("10102010200: board=1504 aka ACR01B2F / ACR01B2G")

print("")
print("All UICR combinations found in the cloud (by hardware version):")
for hardware_version in uicr_in_cloud:
	# Remove duplicates
	unique = []
	for entry in uicr_in_cloud[hardware_version]:
		if entry not in unique:
			unique.append(entry)
	uicr_in_cloud[hardware_version] = unique

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


# Also print for the PRODUCT_NAMING.md document.
print("")
product_naming_boards = {}
for hardware_version in uicr_in_cloud:
	for entry in uicr_in_cloud[hardware_version]:
		board = entry.get("board")
		if board not in product_naming_boards:
			product_naming_boards[board] = []

		# There are still some entries without production year, that messes up the formatting.
		product_naming_boards[board].append(f'| {board:4} '
		                                    f' | {entry.get("productFamily"):1}     '
		                                    f' | {entry.get("region"):02}    '
		                                    f' | {entry.get("productType"):02}  '
		                                    f' | {entry.get("hardwareMajor"):02}   '
		                                    f' | {entry.get("hardwareMinor"):02}   '
		                                    f' | {entry.get("hardwarePatch"):02}   '
		                                    f' | {str(entry.get("productionYear")):2}  '
		                                    f' | {entry.get("productionWeek"):02}  '
		                                    f' | {entry.get("productHousing"):1}       |')

print("")
print("| Board | Family | Market | Type | Major | Minor | Patch | Year | Week | Housing |")
print("| ----- | ------ | ------ | ---- | ----- | ----- | ----- | ---- | ---- | ------- |")
for board in sorted(product_naming_boards.keys()):
	product_naming_boards[board] = list(set(product_naming_boards[board]))
	for entry in product_naming_boards[board]:
		print(entry)

