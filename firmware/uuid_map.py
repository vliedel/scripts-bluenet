

uuids = [
  "B0E4", "14C5", "F0AF", "BF02", "4382", "C1CA", "61A0", "9167", "E042", "589F", "27E4", "AD92", "0DCA", "4F02", "DDC3", "77EA",
  "0970", "99BA", "56AA", "FAB5", "3AE0", "B5BB", "8AE4", "F69D", "E6BC", "EC18", "CA96", "FC91", "A09C", "2A9C", "8EA4", "DBB5",
  "BC67", "63FE", "5DDE", "67B5", "10B4", "1135", "E5CF", "EB4F", "C5DF", "8F29", "1396", "D7BA", "BB0E", "F5DC", "6B07", "20F8",
  "3E6F", "6249", "A567", "85B0", "F994", "15AF", "AB5D", "83B4", "0A96", "F459", "1605", "C8E3", "7E6B", "BA47", "298F", "2B63",
  "D1DB", "35A8", "5A35", "E29E", "42B0", "466A", "1730", "18B9", "5276", "7AE9", "9E83", "DF26", "21C2", "19BB", "D0EB", "4021",
  "0458", "1A3E", "D451", "1B2E", "3D92", "885C", "89C4", "1C23", "53B7", "1D13", "12F5", "1E11", "1FBB", "CE5C", "5FF0", "712F",
  "2216", "47BE", "B47B", "238E", "2412", "26FE", "2502", "8B79", "D811", "2EE0", "2831", "2D94", "9770", "8C3B", "A9D8", "9AF2",
  "2FBB", "30A2", "313A", "E48F", "4ADF", "0B0C", "6FB4", "2C03", "68C4", "86ED", "DE80", "32BB", "E852", "921D", "F8AD", "6619"
]

uuidMap = [255] * 256


for i in range(0, len(uuids)):
    uuid = uuids[i]
    b = int(uuid[0:2], 16)
    uuidMap[b] = 127-i

for i in range(0, 256):
    print("{:3}, ".format(uuidMap[i]), end='')
    if (i % 16 == 16-1):
        print("")



#### Test data:
# [2020-07-10 10:00:01.961] bg adv: protocol=0 sphereId=100 rssi=-57 payload=[51966 1088] address=47:12:56:4F:F1:77
# [2020-07-10 10:00:02.121] rssi=-56 servicesMask:  19 39 12 2E 6F 86 4E 44 8B 9B E1 93 91 22 E6 F8
# [2020-07-10 10:00:02.124] [ng/cs_BackgroundAdvHandler.cpp : 121  ] left=0x1939122E6F864E44 right=0x8B9BE1939122E6F8
# [2020-07-10 10:00:02.129] [ng/cs_BackgroundAdvHandler.cpp : 142  ] part1=0x64E448B9BE part2=0x64E448B9BE part3=0x64E448B9BE result=0x64E448B9BE
#
#
#
#
#
#
#
# 0000 1000 0000 0111
# 0000 0110 0000 0101
# 0000 0100 0000 0011
# 0000 0010 0000 0001
#
# 0001 0000 0000 1111
# 0000 1110 0000 1101
# 0000 1100 0000 1011
# 0000 1010 0000 1001
#
# Payload as HEX string 0x01 0807060504030201 100F0E0D0C0B0A09
# advertising [4382, 4F02, DDC3, 77EA, B5BB, 8AE4, 2A9C, DBB5, 1135, 6B07, 20F8, AB5D, 2B63, E29E, 21C2, 19BB, D0EB, 4021, 3D92, 885C, 89C4, 1FBB, CE5C, 712F, 2412, 26FE, 9770, A9D8, 9AF2, 4ADF, 6FB4, E852, 6619]
#
#
#
# nrf app:
# 	correct:
# 		len: 11, type: 0xFF, data: 0x4C0010065B1E526676E9
# 		len: 20, type: 0xFF, data: 0x4C00010807060504030201100F0E0D0C0B0A09 --> 0807060504030201 100F0E0D0C0B0A09
#
# 	with incomplete list:
# 		uuids: 4382, 4F02, DDC3, 77EA, B5BB, 8AE4, 2A9C, DBB5, 1135, 6B07, 20F8, AB5D, 2B63
# 			43 -> 4
# 			4F -> 13
# 			DD -> 14
# 			77 -> 15
# 			B5 -> 21
# 			8A -> 22
# 			2A -> 29
# 			DB -> 31
# 			11 -> 37
# 			6B -> 46
# 			20 -> 47
# 			AB -> 54
# 			2B -> 63
# 				--> 8040C020A060E010
# 1000 0000 0100 0000
# 1100 0000 0010 0000
# 1010 0000 0110 0000
# 1110 0000 0001 0000
#
# 		len: 27, type: 0x02, data: 0x8243024FC3DDEA77BBB5E48A9C2AB5DB3511076BF8205DAB632B
# 		len: 20, type: 0xFF, data: 0x4C00010000000000000000100F0E0D0C0B0A09 --> 0x0000000000000000100F0E0D0C0B0A09

u = [0x4382, 0x4F02, 0xDDC3, 0x77EA, 0xB5BB, 0x8AE4, 0x2A9C, 0xDBB5, 0x1135, 0x6B07, 0x20F8, 0xAB5D, 0x2B63]
b = [0, 0]
for i in range(0, len(u)):
    index = u[i] >> 8
    bitpos = uuidMap[index]
    b[int(bitpos / 64)] |= (1 << bitpos % 64)
    print("index", index, "bitpos", bitpos)

print("{:X} {:X}".format(b[0], b[1]))
