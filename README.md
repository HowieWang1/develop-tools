## myown-tools
The python_tools dir contains the tools developed by me during my stay in seagate.

Details:
# Power:
![image](https://user-images.githubusercontent.com/41529162/122524051-46dd5600-d04a-11eb-8282-0a168022030d.png)

# found_drives:
     will show the drive relationship in the 2U/4U chassis.
     

# vpd_verify:
     will dump the VPD info, and show all the info to production line engineer to double check the VPD info.
     

# get_serial_port_to_ctrls:
     read the UUT configuration file, and then return dict like follows:
     {'uut0': {'ctrlA': {'uut0': {'ctrlA':{'MC':ttyUSB*, 'SC':ttyUSB*, 'EC':ttyUSB*, 'dev_num': '/dev/sg*'}}},
               'ctrlB': {'uut0': {'ctrlB':{'MC':ttyUSB*, 'SC':ttyUSB*, 'EC':ttyUSB*, 'dev_num': '/dev/sg*'}}}
              }
       ......
     }
