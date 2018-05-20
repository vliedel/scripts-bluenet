#!/usr/bin/python3

import RPi.GPIO as GPIO
import os
import time, datetime

# Adds a shutdown button
# Connect a button with a 1k resistor in series between GND and the pin.

# Pin to use for button
PIN_BUTTON = 36 # PCM/GPIO 16

# Pin to use for LED
# Make sure to have a resistor of at least 330 Ohm in series with the LED.
PIN_LED = 32 # PCM/GPIO 12 or PWM0

# Use board numbering
# This refers to the pin numbers on the P1 header of the Raspberry Pi board.
# The advantage of using this numbering system is that your hardware will always work, regardless of the board revision of the RPi.
# You will not need to rewire your connector or change your code.
GPIO.setmode(GPIO.BOARD)

# Setup button pin with 10k pull up.
GPIO.setup(PIN_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Setup led pin as output
GPIO.setup(PIN_LED, GPIO.OUT)

timestampDown = datetime.datetime.now()
timestampUp = datetime.datetime.now()

def onButtonDown():
	global timestampDown
	timestampDown = datetime.datetime.now()
	print("debounce down")

def onButtonUp():
	global timestampUp
	global timestampDown
	timestampUp = datetime.datetime.now()
	print("debounce up")
	timePressed = timestampUp - timestampDown
	if (timePressed.total_seconds() > 2.0):
		print("shutdown")
		#os.system("sudo shutdown -h now")

		# Turn led off
		GPIO.output(PIN_LED, GPIO.LOW)

		GPIO.cleanup()
		exit(0)

try:
	# Turn led on
	GPIO.output(PIN_LED, GPIO.HIGH)

	GPIO.add_event_detect(PIN_BUTTON, GPIO.FALLING, callback=onButtonDown, bouncetime=200)
	GPIO.add_event_detect(PIN_BUTTON, GPIO.RISING, callback=onButtonDown, bouncetime=200)

	while True:
		channel = GPIO.wait_for_edge(PIN_BUTTON, GPIO.FALLING)
		print("down")
		channel = GPIO.wait_for_edge(PIN_BUTTON, GPIO.RISING)
		print("up")

	# while True:
	# 	# Wait for input to fall to low value
	# 	channel = GPIO.wait_for_edge(PIN_BUTTON, GPIO.FALLING)
	# 	timestampDown = datetime.datetime.now()
	#
	# 	channel = GPIO.wait_for_edge(PIN_BUTTON, GPIO.RISING)
	# 	timestampUp = datetime.datetime.now()
	#
	# 	timePressed = timestampUp - timestampDown
	# 	if (timePressed.total_seconds() > 2.0):
	# 		#os.system("sudo shutdown -h now")
	#
	# 		# Turn led off
	# 		GPIO.output(PIN_LED, GPIO.LOW)
	#
	# 		break
except:
	pass

GPIO.cleanup()
