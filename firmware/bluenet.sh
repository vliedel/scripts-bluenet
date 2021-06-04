#!/bin/bash

# Get the scripts path: the path where this file is located.
path="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

source $path/_utils.sh

#BLUENET_WORKSPACE_DIR="$path/../.."
BLUENET_WORKSPACE_DIR="/home/vliedel/dev/bluenet-workspace-cmake/bluenet"
BLUENET_BUILD_DIR="$BLUENET_WORKSPACE_DIR/build"

bluenet_logo

usage() {
	echo "Bluenet bash script"
	echo
	echo "Usage: ./bluenet.sh [args]              run script"
	echo "   or: VERBOSE=1 ./bluenet.sh [args]    run script in verbose mode"
	echo
	echo "Common usage examples:"
	echo "   Build and upload all:                ./bluenet.sh -j8 -ebu -SHFBP -t mytarget"
	echo "   Build and upload firmware only:      ./bluenet.sh -j8 -bu -FP -t mytarget"
	echo
	echo "Commands:"
	echo "   -b, --build                          cross-compile target"
	echo "   -e, --erase                          erase flash of target"
	echo "   -u, --upload                         upload binary to target"
	echo "   -d, --debug                          debug firmware"
	echo "   -c, --clean                          clean build dir"
	echo "   -R, --reset                          reset the target"
	echo "   --unit_test_host                     compile unit tests for host"
	echo "   --unit_test_nrf5                     compile unit tests for nrf5"
	echo
	echo "What to build and/or upload:"
	echo "   -F, --firmware                       include firmware"
	echo "   -B, --bootloader                     include bootloader"
	echo "   -P, --bootloader_settings            include bootloader settings page"
	echo "                                        this page should be build and uploaded together with the firmware if a bootloader is present"
	echo "   -S, --softdevice                     include softdevice"
	echo "   -H, --hardware_board_version         include hardware board version"
	echo "   -C, --combined                       build and/or upload combined binary, always includes firmware, bootloader, softdevice, and hardware version"
	echo
	echo "Extra arguments:"
	echo "   -t target, --target target           specify config target (files are generated in separate directories)"
	echo "   -j N, --jobs N                       Allow N jobs at once"
	echo "   -r, --release_build                  compile a release build"
	echo "   -y, --yes                            automatically select default option (non-interactive mode)"
	echo "   -h, --help                           show this help"
}

if [[ $# -lt 1 ]]; then
	usage
	exit $CS_ERR_ARGUMENTS
fi

getopt --test > /dev/null
if [[ $? -ne 4 ]]; then
	cs_err "Error: \"getopt --test\" failed in this environment. Please install the GNU version of getopt."
	exit $CS_ERR_GETOPT_TEST
fi

SHORT=t:j:beudcrRyhFBPSHC
LONG=target:,jobs:,build,erase,upload,debug,clean,release_build,reset,yes,help,firmware,bootloader,bootloader_settings,softdevice,hardware_version,combined,unit_test_host,unit_test_nrf5

PARSED=$(getopt --options $SHORT --longoptions $LONG --name "$0" -- "$@")
if [[ $? -ne 0 ]]; then
	exit $CS_ERR_GETOPT_PARSE
fi

eval set -- "$PARSED"


while true; do
	case "$1" in
		-b|--build)
			do_build=true
			shift 1
			;;
		-e|--erase)
			do_erase_flash=true
			shift 1
			;;
		-u|--upload)
			do_upload=true
			shift 1
			;;
		-d|--debug)
			do_debug=true
			shift 1
			;;
		-c|--clean)
			do_clean=true
			shift 1
			;;
		--unit_test_host)
			do_unit_test_host=true
			shift 1
			;;
		--unit_test_nrf5)
			do_unit_test_nrf5=true
			shift 1
			;;

		-F|--firmware)
			include_firmware=true
			shift 1
			;;
		-B|--bootloader)
			include_bootloader=true
			shift 1
			;;
		-P|--bootloader_settings)
			include_bootloader_settings=true
			shift 1
			;;
		-S|--softdevice)
			include_softdevice=true
			shift 1
			;;
		-H|--hardware_board_version)
			include_board_version=true
			shift 1
			;;
		-C|--combined)
			use_combined=true
			shift 1
			;;
		-t|--target)
			target=$2
			shift 2
			;;
		-j|--jobs)
			jobs=$2
			shift 2
			;;
		-r|--release_build)
			release_build=true
			shift 1
			;;
		-R|--reset)
			do_reset=true
			shift 1
			;;
		-y|--yes)
			autoyes=true
			shift 1
			;;
		-h|--help)
			usage
			exit 0
			shift 1
			;;

		--)
			shift
			break
			;;
		*)
			echo "Error in arguments."
			echo $2
			exit $CS_ERR_ARGUMENTS
			;;
	esac
done


# Default target
target=${target:-default}

# Default jobs
jobs=${jobs:-1}

# Load configuration files.
#cs_info "Load configuration from: ${path}/_config.sh"
#source $path/_config.sh $target

check_target_changed() {
	# old_target="$(grep "BOARD_TARGET:STRING=.*" $BLUENET_BUILD_DIR/CMakeCache.txt | sed 's/BOARD_TARGET:STRING=//')"
	# if [ "$old_target" == "$target" ]; then
	# 	cs_info "Similar target"
	# else
	# 	cs_warn "Target changed"
	# 	cd "$BLUENET_BUILD_DIR"
	#   cs_info "Running cmake"
	# 	cmake .. -DBOARD_TARGET=$target
	# 	checkError "Error running cmake"
	# 	make -j1
	# 	checkError "Error running first make"
	# fi
	cd "$BLUENET_BUILD_DIR"
	cs_info "Running cmake"
	cmake .. -DBOARD_TARGET=$target -DDOWNLOAD_JLINK=OFF -DDOWNLOAD_NRFUTIL=OFF -DDOWNLOAD_NRFJPROG=OFF -DCONFIG_DIR=config -DCMAKE_BUILD_TYPE=Debug -DFACTORY_IMAGE=
	checkError "Error running cmake"
	make -j${jobs}
	checkError "Error running first make"
}

build_firmware() {
	cs_info "build firmware"
	cd "$BLUENET_BUILD_DIR/$target"
	make -j${jobs}
	checkError "Error building firmware"
}

build_firmware_release() {
	cs_info "build release firmware"
	# ${path}/firmware.sh release $target
	# checkError "Error building firmware release"
	cs_err "TODO: build firmware release"
	exit 1
}

build_bootloader_settings() {
	cs_info "build bootloader settings"
	cd "$BLUENET_BUILD_DIR/$target"
	make -j${jobs} build_bootloader_settings
	checkError "Error building bootloader settings"
}

build_bootloader() {
	cs_info "build bootloader"
	cd "$BLUENET_BUILD_DIR/$target/bootloader"
	make -j${jobs}
	checkError "Error building bootloader"
}

build_softdevice() {
	cs_info "No need to build softdevice"
}

build_combined() {
	cs_info "build combined"
	# ${path}/combine.sh -f -b -s -h -t $target
	# checkError "Error combining to binary"
	cs_err "TODO: build combined"
	exit 1
}

build_unit_test_host() {
	cs_info "build unit test host"
	# ${path}/firmware.sh unit-test-host $target
	# checkError "Error building unit test host"
	cs_err "TODO: build unit test host"
	exit 1
}


erase_flash() {
	cs_info "erase flash"
	cd "$BLUENET_BUILD_DIR"
	make erase
	checkError "Error erasing flash"
}


upload_firmware() {
	cs_info "upload firmware"
	cd "$BLUENET_BUILD_DIR/$target"
	make write_application
	checkError "Error uploading firmware"
}

upload_bootloader_settings() {
	cs_info "upload bootloader settings"
	cd "$BLUENET_BUILD_DIR/$target"
	make write_bootloader_settings
	checkError "Error uploading bootloader settings"
}

upload_bootloader() {
	cs_info "upload bootloader"
	cd "$BLUENET_BUILD_DIR/$target/bootloader"
	make write_bootloader
	make write_bootloader_address
	checkError "Error uploading bootloader"
}

upload_softdevice() {
	cs_info "upload softdevice"
	cd "$BLUENET_BUILD_DIR"
	make write_softdevice
	make write_mbr_param_address
	checkError "Error uploading softdevice"
}

upload_combined() {
	cs_info "upload combined"
	# cs_info "Upload all at once"
	# ${path}/_upload.sh $BLUENET_BIN_DIR/combined.hex $serial_num
	# checkError "Error uploading combined binary"
	cs_err "TODO: upload combined"
	exit 1
}

upload_board_version() {
	cs_info "upload board version"
	cd "$BLUENET_BUILD_DIR/$target"
	make write_board_version
	checkError "Error uploading board version"
}

debug_firmware() {
	cs_info "debug firmware"
	# ${path}/firmware.sh debug $target
	# checkError "Error debugging firmware"
	cs_err "TODO: debug firmware"
	exit 1
}

debug_bootloader() {
	cs_info "debug bootloader"
	# ${path}/bootloader.sh debug $target
	# checkError "Error debugging bootloader"
	cs_err "TODO: debug bootloader"
	exit 1
}




clean_firmware() {
	cs_info "clean firmware"
	# ${path}/firmware.sh clean $target
	# checkError "Error cleaning up firmware"
	cs_err "TODO: clean firmware"
	exit 1
}

clean_bootloader() {
	cs_info "clean bootloader"
	# ${path}/bootloader.sh clean $target
	# checkError "Error cleaning up bootloader"
	cs_err "TODO: clean bootloader"
	exit 1
}

clean_softdevice() {
	cs_info "clean softdevice"
	# ${path}/softdevice.sh clean $target
	# checkError "Error cleaning up softdevice"
	cs_err "TODO: clean softdevice"
	exit 1
}



verify_board_version_written() {
	cs_info "verify board version"
	# ${path}/board_version.sh check $target
	# checkError "Error: no correct board version is written."
	cs_warn "TODO: verify board version"
}

reset() {
	cs_info "reset"
	cd "$BLUENET_BUILD_DIR/$target"
	make reset
	checkError "Error when resetting"
}


# Main
done_something=false

if [ $do_unit_test_nrf5 ]; then
	cs_info "Unit test NRF5: You can also just build firmware, as long as TEST_TARGET=\"nrf5\" is in the config."
	if [ "$TEST_TARGET" != "nrf5" ]; then
		cs_err "Target needs to have TEST_TARGET=\"nrf5\" in config."
		exit $CS_ERR_CONFIG
	fi
	do_build=true
	include_firmware=true
fi

if [ $do_build ]; then
	check_target_changed
	done_something=true
	done_built=false
	if [ $include_firmware ]; then
		if [ $release_build ]; then
			build_firmware_release
		else
			build_firmware
		fi
		done_built=true
	fi
	if [ $include_bootloader ]; then
		build_bootloader
		done_built=true
	fi
	if [ $include_bootloader_settings ]; then
		build_bootloader_settings
		done_built=true
	fi
	if [ $include_softdevice ]; then
		build_softdevice
		done_built=true
	fi
	if [ $use_combined ]; then
		build_combined
		done_built=true
	fi
	if [ "$done_built" != true ]; then
		cs_err "Nothing was built. Please specify what to build."
		exit $CS_ERR_NOTHING_INCLUDED
	fi
fi


if [ $do_erase_flash ]; then
	done_something=true
	erase_flash
fi


if [ $do_upload ]; then
	check_target_changed
	done_something=true
	done_upload=false
	if [ $use_combined ]; then
		if [ $include_softdevice -o $include_bootloader -o $include_firmware -o $include_board_version ]; then
			# I guess it makes sense to rebuild the combined when one of the others was included?
			build_combined
		fi
		upload_combined
#		if [ $include_bootloader ]; then
#			${path}/_writebyte.sh 0x10001014 $BOOTLOADER_START_ADDRESS
#		fi
		done_upload=true
	else
		if [ $include_softdevice ]; then
			upload_softdevice
			done_upload=true
		fi
		if [ $include_bootloader ]; then
			upload_bootloader
			done_upload=true
		fi
		# Write board version before uploading firmware, else firmware writes it.
		if [ $include_board_version ]; then
			upload_board_version
			done_upload=true
		fi
		if [ $include_firmware ]; then
			upload_firmware
			done_upload=true
		fi
		if [ $include_bootloader_settings ]; then
			upload_bootloader_settings
			done_upload=true
		fi
	fi
	verify_board_version_written
	if [ "$done_upload" != true ]; then
		cs_err "Nothing was uploaded. Please specify what to upload."
		exit $CS_ERR_NOTHING_INCLUDED
	fi
	reset
fi


if [ $do_debug ]; then
	check_target_changed
	done_something=true
	if [ $include_bootloader ]; then
		debug_bootloader
	elif [ $include_firmware ]; then
		debug_firmware
	else
		debug_firmware
	fi
fi


if [ $do_clean ]; then
	done_something=true
	done_clean=false
	if [ $include_firmware ]; then
		clean_firmware
		done_clean=true
	fi
	if [ $include_bootloader ]; then
		clean_bootloader
		done_clean=true
	fi
	if [ $include_softdevice ]; then
		clean_softdevice
		done_clean=true
	fi
	if [ "$done_clean" != true ]; then
		cs_err "Nothing was cleaned. Please specify what to clean."
		exit $CS_ERR_NOTHING_INCLUDED
	fi
fi


if [ $do_unit_test_host ]; then
	done_something=true
	build_unit_test_host
fi

if [ $do_reset ]; then
	reset
	done_something=true
fi

if [ "$done_something" != true ]; then
	cs_err "Nothing was done. Please specify a command."
	exit $CS_ERR_NO_COMMAND
fi
cs_succ "Done!"
