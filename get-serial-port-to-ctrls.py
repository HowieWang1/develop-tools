#! /usr/bin/env python3
'''
purpose: read the serial port(ttyUSB*), then, find the corresponding controllers
'''

from ctp.uut.uut_config_mapping import UUTConfigMap
def find_ctrl_serial_mapping(test_name:str)->dict:
    '''
        inputs:  test_name                  : string       : test_name, such as: chassis_generic, rbod_fw,...
        Raise :  Exception
        return:  ctrl_serial_dict           : dict         : {'uut0': {'ctrlA':{'MC':ttyUSB*, 'SC':ttyUSB*, 'EC':ttyUSB*}},
                                                              'uut1': {'ctrlB':{'MC':ttyUSB*, 'SC':ttyUSB*, 'EC':ttyUSB*}},
                                                               ..........
                                                             }
    '''
    ctrl_serial_dict = dict()
    uut_list = list()
    MAX_UUT_NUM = 8
    
    UUT_CONFIG_PATH = '/CTP/tests/mfg-test/config/'
    if 'rbod' in test_name:
        test_name += '_sas'  # for FC/i-SCSI, need to input the parameter to determine which type interface do we need to use
    UUT_CONFIG_NAME = '{}_uut.yaml'.format(UUT_CONFIG_PATH + test_name)
    UUT_resource_config = UUTConfigMap(UUT_CONFIG_NAME)
    for uut_num in range(MAX_UUT_NUM):
        try:
            # get MC/SC/EC info
            uut_boj = UUT_resource_config.UUTs[uut_num]
            ctrl_A_obj = uut_boj.enclosures[0].cntrlr_A
            ctrl_B_obj = uut_boj.enclosures[0].cntrlr_B
            if 'rbod' in UUT_CONFIG_NAME:
                uut_info = {f'uut{uut_num}': {'ctrlA':{'MC':ctrl_A_obj.MC, 'SC':ctrl_A_obj.SC},
                                              'ctrlB':{'MC':ctrl_B_obj.MC, 'SC':ctrl_B_obj.SC}
                                             }
                           }
            elif 'jbod' in UUT_CONFIG_NAME:
                uut_info = {f'uut{uut_num}': {'ctrlA':{'EC':ctrl_A_obj.EC}, 
                                              'ctrlB':{'EC':ctrl_B_obj.EC}
                                             }
                           }
            elif 'chassis_generic' in UUT_CONFIG_NAME:
                uut_info = {f'uut{uut_num}': {'ctrlA':{'EC':ctrl_A_obj.EC, 'MC':ctrl_A_obj.MC, 'SC':ctrl_A_obj.SC},
                                              'ctrlB':{'EC':ctrl_B_obj.EC, 'MC':ctrl_B_obj.MC, 'SC':ctrl_B_obj.SC}
                                             }
                           }
            else: 
                raise Exception
            
            # get /dev/sg* info
            ses_device_A = ctrl_A_obj.get_ses_devices()
            ses_device_B = ctrl_B_obj.get_ses_devices()
            encl_num = None
            for ses_device_list in [ses_device_A, ses_device_B]:
                for encl in ses_device_list:
                    if len(encl):
                        encl_num = encl[0]
                        if ses_device_list == ses_device_A:
                            uut_info[f'uut{uut_num}']['ctrlA'].update({'dev_num':'/dev/' + encl_num})
                        else:
                            uut_info[f'uut{uut_num}']['ctrlB'].update({'dev_num':'/dev/' + encl_num})
            ctrl_serial_dict.update(uut_info)
        except Exception:
            print("only found {} uut configuration info in {}".format(uut_num, UUT_CONFIG_NAME))
            break
    return ctrl_serial_dict



if __name__ == "__main__":
    import sys
    from pprint import pprint
    
    pprint(find_ctrl_serial_mapping(sys.argv[1]))

