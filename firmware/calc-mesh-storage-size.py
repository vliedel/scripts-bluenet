

fm_header_t = 4
access_model_state_data_t = 20
access_flash_subscription_list_t = 4
dsm_local_unicast_address_t = 4
dsm_flash_entry_addr_unicast_t = 4
dsm_flash_entry_addr_nonvirtual_t = 2
dsm_flash_entry_addr_virtual_t = 16
dsm_flash_entry_subnet_t = 36
dsm_flash_entry_devkey_t = 20
dsm_flash_entry_appkey_t = 36
flash_manager_metadata_t = 8
dsm_flash_entry_t = 36

WORD_SIZE = 4
#FLASH_MANAGER_DATA_PER_PAGE = PAGE_SIZE - 

ACCESS_MODEL_COUNT             = 3
ACCESS_SUBSCRIPTION_LIST_COUNT = 1
ACCESS_ELEMENT_COUNT           = 1
DSM_NONVIRTUAL_ADDR_MAX        = 3
DSM_VIRTUAL_ADDR_MAX           = 1
DSM_SUBNET_MAX                 = 1
DSM_DEVICE_MAX                 = 1
DSM_APP_MAX                    = 1 

def ALIGN_VAL(dataSize, wordSize):
	return (int(dataSize / wordSize) + (dataSize % wordSize)) * wordSize

def dsm_flash_data_size():
	DATA_SIZE =  ALIGN_VAL((fm_header_t + dsm_flash_entry_addr_unicast_t), WORD_SIZE)
	DATA_SIZE += ALIGN_VAL((fm_header_t + dsm_flash_entry_addr_nonvirtual_t), WORD_SIZE)  * DSM_NONVIRTUAL_ADDR_MAX
	DATA_SIZE += ALIGN_VAL((fm_header_t + dsm_flash_entry_addr_virtual_t), WORD_SIZE)     * DSM_VIRTUAL_ADDR_MAX
	DATA_SIZE += ALIGN_VAL((fm_header_t + dsm_flash_entry_subnet_t), WORD_SIZE)           * DSM_SUBNET_MAX
	DATA_SIZE += ALIGN_VAL((fm_header_t + dsm_flash_entry_devkey_t), WORD_SIZE)           * DSM_DEVICE_MAX
	DATA_SIZE += ALIGN_VAL((fm_header_t + dsm_flash_entry_appkey_t), WORD_SIZE)           * DSM_APP_MAX
	return DATA_SIZE

def access_flash_data_size():
	DATA_SIZE =  (ALIGN_VAL((fm_header_t + access_model_state_data_t), WORD_SIZE) * ACCESS_MODEL_COUNT)
	DATA_SIZE += (ALIGN_VAL((fm_header_t + access_flash_subscription_list_t), WORD_SIZE) * ACCESS_SUBSCRIPTION_LIST_COUNT)
	DATA_SIZE += (ALIGN_VAL((fm_header_t + 2), WORD_SIZE) * ACCESS_ELEMENT_COUNT)
	return DATA_SIZE

print("dsm data size:", dsm_flash_data_size())
print("access data size:", access_flash_data_size())

