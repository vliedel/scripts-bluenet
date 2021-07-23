import yaml
from typing import List


class CrownstoneConfig:
	def __init__(self):
		self.address: str = ""
		self.id: int = 150
		self.mesh_device_key: str = "mesh_device_key1"
		self.ibeacon_major: int = 1234
		self.ibeacon_minor: int = 5678
		self.igbt_broken: bool = False

class KeyConfig:
	def __init__(self):
		self.admin = "adminKeyForCrown"
		self.member = "memberKeyForHome"
		self.basic = "basicKeyForOther"
		self.service_data = "MyServiceDataKey"
		self.localization = "aLocalizationKey"
		self.mesh_app = "MyGoodMeshAppKey"
		self.mesh_net = "MyGoodMeshNetKey"

class SphereConfig:
	def __init__(self):
		self.id: int = 123
		self.ibeacon_uuid: str = "1843423e-e175-4af0-a2e4-31e32f729a8a"

class TestConfig:
	def __init__(self):
		self.tests: List[str] = None
		self.crownstones: List[CrownstoneConfig] = []
		self.sphere = SphereConfig()
		self.keys = KeyConfig()

def load_config(config_file) -> TestConfig:
	config = TestConfig()
	with open(config_file, 'r') as f:
		yaml_config = yaml.load(f)

	cs_id = 150
	for cs in yaml_config["crownstones"]:
		cs_id += 1
		crownstone_config = CrownstoneConfig()
		crownstone_config.address = cs["mac_address"]
		crownstone_config.id = cs_id
		crownstone_config.ibeacon_minor = 4567 + cs_id
		crownstone_config.igbt_broken = cs["igbt_broken"]


		config.crownstones.append(crownstone_config)

	if "keys" in yaml_config:
		if "admin" in yaml_config["keys"]:
			config.keys.admin = yaml_config["keys"]["admin"]
		if "member" in yaml_config["keys"]:
			config.keys.member = yaml_config["keys"]["member"]
		if "basic" in yaml_config["keys"]:
			config.keys.basic = yaml_config["keys"]["basic"]
		if "service_data" in yaml_config["keys"]:
			config.keys.service_data = yaml_config["keys"]["service_data"]
		if "localization" in yaml_config["keys"]:
			config.keys.localization = yaml_config["keys"]["localization"]
		if "mesh_app" in yaml_config["keys"]:
			config.keys.mesh_app = yaml_config["keys"]["mesh_app"]
		if "mesh_net" in yaml_config["keys"]:
			config.keys.mesh_net = yaml_config["keys"]["mesh_net"]


	if "sphere_id" in yaml_config:
		config.sphere.id = yaml_config["sphere_id"]

	if "ibeacon_uuid" in yaml_config:
		config.sphere.ibeacon_uuid = yaml_config["ibeacon_uuid"]

	if "tests" in yaml_config:
		config.tests = yaml_config["tests"]

	return config
