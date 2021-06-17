#! /usr/bin/env python3
'''
purpose: read the serial port(ttyUSB*), then, find the corresponding controllers
'''

from ctp.uut.uut_config_mapping import UUTConfigMap
def find_ctrl_serial_mapping(test_name:str)->dict:
    '''
        inputs:  test_name                  : string       : test_name, such as: chassis_generic, rbod_fw,...
        Raise :  None
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
            uut_boj = UUT_resource_config.UUTs[uut_num]
            if 'jbod' in UUT_CONFIG_NAME:
                uut_info = {f'uut{uut_num}': {'ctrlA':{'MC':uut_boj.enclosures[0].cntrlr_A.MC, 'SC':uut_boj.enclosures[0].cntrlr_A.SC},
                                              'ctrlB':{'MC':uut_boj.enclosures[0].cntrlr_B.MC, 'SC':uut_boj.enclosures[0].cntrlr_B.SC}
                                             }
                           }
            elif 'rbod' in UUT_CONFIG_NAME:
                uut_info = {f'uut{uut_num}': {'ctrlA':{'EC':uut_boj.enclosures[0].cntrlr_A.EC}, 
                                              'ctrlB':{'EC':uut_boj.enclosures[0].cntrlr_B.EC}
                                             }
                           }
            elif 'chassis_generic' in UUT_CONFIG_NAME:
                uut_info = {f'uut{uut_num}': {'ctrlA':{'EC':uut_boj.enclosures[0].cntrlr_A.EC, 'MC':uut_boj.enclosures[0].cntrlr_A.MC, 'SC':uut_boj.enclosures[0].cntrlr_A.SC},
                                              'ctrlB':{'EC':uut_boj.enclosures[0].cntrlr_B.EC, 'MC':uut_boj.enclosures[0].cntrlr_B.MC, 'SC':uut_boj.enclosures[0].cntrlr_B.SC}
                                             }                 
                           }
            else: 
                raise Exception
            ctrl_serial_dict.update(uut_info)
        except Exception:
            print("only found {} uut configuration info in {}".format(uut_num, UUT_CONFIG_NAME))
            break
    return ctrl_serial_dict


if __name__ == "__main__":
    import sys
    from pprint import pprint
    
    pprint(find_ctrl_serial_mapping(sys.argv[1]))

