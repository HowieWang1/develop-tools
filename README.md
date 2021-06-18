# myown-tools
This dir contains the tools developed by me during my stay in seagate.

Details:
Power:

found_drives:
     will show the drive relationship in the 2U/4U chassis.
vpd_verify:
     will dump the VPD info, and show all the info to production line engineer to double check the VPD info.
get_serial_port_to_ctrls:
     read the UUT configuration file, and then return dict like follows:
     {'uut0': {'ctrlA': {'uut0': {'ctrlA':{'MC':ttyUSB*, 'SC':ttyUSB*, 'EC':ttyUSB*, 'dev_num': '/dev/sg*'}}},
               'ctrlB': {'uut0': {'ctrlB':{'MC':ttyUSB*, 'SC':ttyUSB*, 'EC':ttyUSB*, 'dev_num': '/dev/sg*'}}}
              }
       ......
     }
