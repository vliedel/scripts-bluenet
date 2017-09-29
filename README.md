# scripts-bluenet
Some scripts and data for bluenet.

## Power data
File names include the type of hardware, and the mac address. Then there are several keywords used:
NW | Means the load was N Watt.
setup | Means that the data starts with the crownstone in setup mode, then gets setuped, then goes boots in normal mode.
phone | Means a phone was held close to the crownstone, in order to see the interference. Usually only waves above some threshold were captured. 
no-diff | Means the ADC was in single ended mode instead of differential mode.
zero-ref | Means the zero ref pin was sampled instead of the current sense pin.
gnd | Means some unused pin, with pull down, was sampled instead of the current sense pin.
every N ms | Means every N ms a wave was captured.
