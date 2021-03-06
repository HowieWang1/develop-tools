# this program contains the following functions:
#    1. find the mapping relationship between ctrl and drives.
#    2. check each device by command sg_inq
#    3. use FIO to write/read data
#    4. check the PHY counter by GEM command
# when should we run this program:
#    1. sometimes, one drive goes wrong but we get more than one (106,100, 84,24,12) installed in the chassis
#       so, this may be the fast way to locate the failed drive/channel.
'''
just for play around
'''

import os
import logging
import re
import socket
import tkinter as tk
from pprint import pprint

import ctp.utils.common_devices_functions as comm_dev_funs
import ctp.common.ctperrors as ctper
import ctp.common.ctpexception as ctpex
from ctp.gem.gemcli import AccessMode, GemCli
from ctp.utils.execcmd import execcmd, execcmd_remote
from ctp.pcd.pcd_unitconfig import PcdUnitConfig
from ctp.common.ctpconfig import get_ctp_config

log = logging.getLogger()
cconfig = get_ctp_config()
access_mode = AccessMode.WBCLI

class find_check_devcie():

    def __init__(self):
        self.encl_devs = comm_dev_funs.get_available_ses_devs(wwn=None)
        self.attach_expander_disk = []
        self.same_wwn_disk = {}
        self.disk_mapping_index = {}

        if len(self.encl_devs) > 2:
            error_msg = "detected Multi-uut, not support Multi-uut."
            log.warning(error_msg)
            raise ctpex.CTPException(ctper.INVALID_INPUT, error_msg)
        elif len(self.encl_devs) == 2:
            log.info("detected uut device: {}.".format(self.encl_devs))
        elif len(self.encl_devs) == 1:
            log.warning("detected one encl device: {}.".format(self.encl_devs))
        elif len(self.encl_devs) == 0:
            log.error("no devices detected")
            error_msg = "no encl device detected"
            raise ctpex.CTPException(ctper.INVALID_INPUT, error_msg)

        self.host_port_info = comm_dev_funs.get_attached_expander_and_disk(self.encl_devs)
        self.attach_expander_disk = self.host_port_info['disk']
        # return value: {'expander':[], 'disk':[('/dev/sdal', '/dev/sg1'),...]}
    
    def run(self):
        disk_mapping_result = self.update_sas_dev()
        #print(disk_mapping_result)
        return disk_mapping_result
        #log.info("{}".format('#'*10))
        #log.info("the mapping relationship is {}".format(disk_mapping_result))
        #print(disk_mapping_result)
        #log.info("{}".format('#'*10))


        sorted_same_wwn_disk = self.sort_devices_by_wwn()
        log.info("{}".format('#'*10))
        log.info("the disk list with the same wwn is {}".format(sorted_same_wwn_disk))
        print(sorted_same_wwn_disk)
        log.info("{}".format('#'*10))


    def sort_devices_by_wwn(self):
        # this function will use sg_inq command to read the wwn of each disk,
        # why will use this command to read the wwn again?
            # to make sure the /dev/sg* is uniquely.
            # then, make sure each drive can be available.

        disk_expander_wwn = {}
        for dev_component in self.attach_expander_disk:
            try:
                cmd = 'sudo sg_inq {}'.format(dev_component[-1])
                sg_inq_info, err = execcmd([cmd], timeout=30, shell=True)
            except Exception:
                err_device_index = [self.disk_mapping_index.get(dev_index, None) for dev_index in self.disk_mapping_index.keys if dev_component[-1] in dev_index]
                log.error('device un-reachable: {}/{}'.fomrmat(dev_component[-1], err_device_index))
                return None
            dev_sas = sg_inq_info.splitlines()[-1].split(' ')[-1]                    # parse the wwn from the data got by sg_inq /dev/sg*
            disk_expander_wwn.update({dev_component[-1]:dev_sas})
            # self.disk_expander_wwn = {'/dev/sg*:sasaddress', ...}

        # we just need to focus on disk, so will discard the enxpander/ctrl
        keys = list(disk_expander_wwn.keys())
        while keys:
            dev_component = keys.pop()
            for key in keys:
                if disk_expander_wwn.get(dev_component) == disk_expander_wwn.get(key):
                    self.same_wwn_disk.update({str([dev_component, key]):disk_expander_wwn.get(key)})
                    # self.same_wwn_disk = {'['/dev/sg*', '/dev/sg*']':['wwn']}
        return self.same_wwn_disk        

        '''
        valuelist_same_wwn = list(self.same_wwn_disk.keys())
        valuelist_disk_mapping = list(self.disk_mapping_index.keys())
        mapping_relationship = True
        for num in range(len(valuelist_disk_mapping)):
            if valuelist_same_wwn[num] not in valuelist_disk_mapping:
                mapping_relationship = False
                break
        if mapping_relationship:
            for value in valuelist_disk_mapping:
                self.disk_mapping_index[value] += self.same_wwn_disk[value]
            return self.disk_mapping_index
        else:
            log.warning('map relationship is mismatch.\n info got from sg_inq is: {},\n while got from lsscsi is: {} \
                        '.format(self.same_wwn_disk, self.disk_mapping_index))
            return self.same_wwn_disk
        '''


    def update_sas_dev(self):
        # this function will use the "lsscsi -gt" command to get the sas transport information for device
        
        cmd = 'lsscsi -gt'
        lsscsi_gt, err = execcmd([cmd], timeout=30, shell=True)
        devs_info = lsscsi_gt.splitlines()
        tmp_dev_sas_info = {}
        for _dev_info in devs_info:
            if 'sas' not in _dev_info:
                continue
            sas_info = re.search(r"sas:0x(\w{16})", _dev_info).group(0).split(':')[-1]
            dev_num = re.search(r"/dev/sg(\d+)", _dev_info).group(0)
            tmp_dev_sas_info.update({dev_num:sas_info})
            # tmp_dev_sas = {'/dev/sg*': 0x******, ...}
        
            '''
            for key in self.same_wwn_disk.keys():
                if r"'{}'".format(dev_num) in key:
                    self.same_wwn_disk[key] += ('+' + sas_info)
            '''

        similar_wwn_disk = {}
        keys = list(tmp_dev_sas_info.keys())
        while len(keys):
            tmp_key = keys.pop()
            for key in keys:
                if abs(int(tmp_dev_sas_info[key], 16) - int(tmp_dev_sas_info[tmp_key], 16)) == 1:
                    similar_wwn_disk.update({str([key, tmp_key]):tmp_dev_sas_info[key] + '+' + tmp_dev_sas_info[tmp_key]})
                    # simlilar_wwn_disk = {'/dev/sg*+/dev/sg*':'0x******+0x*****'}
        log.info("silimary wwn disk: {}.".format(similar_wwn_disk))
        
        # use GEM command to mark the drive num and status.
        for _dev in self.encl_devs:
            if 'master' in access_mode.send_cmd("getboardid", _dev, bus='', pass_through='')[0]:
                master_dev = _dev
        gem_cli = GemCli(master_dev, access_mode=access_mode, CLI='', bus='', pass_through='')
        for num in range(106):                                                        # for now, just focus on Cobra+
            recv_data = gem_cli.send_cmd("getdrivestatus {}".format(num))[0]
            if "invalid" in recv_data.lower():
                break                                                                 # no enough drives
            recv_data = recv_data.splitlines()
            for info_line in recv_data:
                if info_line == '':
                    continue
                sas_re = re.search(r"\w{16}", info_line)
                if sas_re:
                    sas_address = '0x' + sas_re.group(0)
            for key, value in similar_wwn_disk.items():
                if sas_address.lower() in value:
                        self.disk_mapping_index.update({key:int(num)})

        return self.disk_mapping_index
        # return value: {'['/dev/sg*', '/dev/sg*']':[num]}, usually, the first one would be connected to ctrlA,
        #                                                          the second one would be connected to ctrlB.


    def print_drives_info(self, chassis_type, input_info):
        if chassis_type.lower() == '4u106':
            #########################
            # 4U106 chassis
            #########################

            # exchange the key and value
            output_info = {}
            for key, value in input_info.items():
                output_info[value] = key
    
            print("-"*232)
            for row in range(14):                           # 96HDD baseplane
                for col in range(8):
                    print("|", end="")
                    if row <= 11:
                        output_value = output_info.get((95 - row) - col*12, '')
                    else:
                        output_value = output_info.get((111 - row + 12) - col*2, '')
                    if output_value:
                        print(eval(output_value), end="")
                        print(" " * (28 - len(output_value)), end="")
                    else:
                        print(' '*28, end="")
                print("|")
 
        elif chassis_type.lower() == '2u12':
            #########################
            # 2U12 chassis
            #########################
            output_info = {}
            for key, value in input_info.items():
                output_info[value] = key
            print("-"*175)
        
            for row in range(2):
                for col in range(6):
                    print("|", end='')
                    output_value = output_info.get(6 - 6*row + col, '')
                    if output_value:
                        print(eval(output_value), end='')
                        print(" " * (28 - len(output_value)), end='')
                    else:
                        print(' '*28, end='')
                print("|", end='')
                print("\n")
        
        elif chassis_type.lower() == '2u24':
            #########################
            # 2U24 chassis
            #########################
            output_info = {}
            for key, value in input_info.items():
                output_info[value] = key
    
            print("-"*50)
            for row in range(4):
                for col in range(6):
                    print("|", end="")
                    output_value = output_info.get(6*row + col, '')
                    if output_value:
                        print(eval(output_value), end="")
                        print(" " * (28 - len(output_value)), end="")
                    else:
                        print(' '*28, end="")
                print("|")
    
        # print the info line by line
        for key, value in output_info.items():
            print(f"Drive Slot {key}: {value}")

    def get_device_host_port(self):
        # get the host, port, expander num
        # initial the dicts
        address_dict = dict()
        expander_dict = dict()
        drive_dict = dict()
        encl_dict = dict()
        
        for dev_name, dev_num in self.host_port_info.items():
            if dev_name == 'expander' and self.host_port_info[dev_name] and isinstance(self.host_port_info[dev_name], list):
                # get the info of expander
                for dev_exp in self.host_port_info[dev_name[4:]]:
                    file_path = f"/sys/class/scsi_generic/{dev_exp}"
                    recv_info = os.readlink(file_path)
                    re_host_port_info = re.search(r"/host\w+/port-\w+:\w+/expander-\w+:\w+", recv_info)
                    re_end_device_info = re.search(r"/end_device-\w+:\w+:\w+/target\w+:\w+:\w+", recv_info)
                    expander_dict.update({dev_exp:{}})
                    if re_host_port_info.group(0):
                        tmp_data = re_host_port_info.group(0)
                        tmp_data = tmp_data.split(r"/")
                        for i in tmp_data:
                            if "host" in i:
                                expander_dict[dev_exp].update({"host":i[4:]})  # 
                            elif "port" in i:
                                expander_dict[dev_exp].update({"port":i[5:]})  # skip "-"
                            elif "expander" in i:
                                expander_dict[dev_exp].update({"expander":i[9:]})
                    if re_end_device_info.group(0):
                        tmp_data = re_end_device_info.group(0)
                        tmp_data.split(r"/")
                        for i in tmp_data:
                            if "end_device" in i:
                                expander_dict[dev_exp].update({"end_device":i[11:]})
                            elif "target" in i:
                                expander_dict[dev_exp].update({"target":i[10:]})
            if dev_name == 'disk' and self.host_port_info[dev_name] and isinstance(self.host_port_info[dev_name], list):
                # get the info of disks
                for dev_exp in self.host_port_info[dev_name]:
                    file_path = f"/sys/class/scsi_generic/{dev_exp[1][4:]}"
                    recv_info = os.readlink(file_path)
                    re_host_port_info = re.search(r"/host\w+/port-\w+:\w+/expander-\w+:\w+", recv_info)
                    re_end_device_info = re.search(r"/end_device-\w+:\w+:\w+/target\w+:\w+:\w+", recv_info)
                    drive_dict.update({dev_exp[1]:{}})
                    if re_host_port_info.group(0):
                        tmp_data = re_host_port_info.group(0)
                        tmp_data = tmp_data.split(r"/")
                        for i in tmp_data:
                            if "host" in i:
                                drive_dict[dev_exp[1]].update({"host":i[4:]})
                            elif "port" in i:
                                drive_dict[dev_exp[1]].update({"port":i[5:]}) # skip "-"
                            elif "expander" in i:
                                drive_dict[dev_exp[1]].update({"expander":i[9:]})
                    if re_end_device_info.group(0):
                        tmp_data = re_end_device_info.group(0)
                        tmp_data = tmp_data.split(r"/")
                        for i in tmp_data:
                            if "end_device" in i:
                                drive_dict[dev_exp[1]].update({"end_device":i[11:]})
                            elif "target" in i:
                                drive_dict[dev_exp[1]].update({"target":i[7:]})
            if self.encl_devs:
                # get the info of ctrls
                for encl in self.encl_devs:
                    file_path = f"/sys/class/scsi_generic/{encl[4:]}"
                    recv_info = os.readlink(file_path)
                    re_host_port_info = re.search(r"/host\w+/port-\w+:\w+/expander-\w+:\w+", recv_info)
                    re_end_device_info = re.search(r"/end_device-\w+:\w+:\w+/target\w+:\w+:\w+", recv_info)
                    encl_dict.update({encl:{}})
                    if re_host_port_info.group(0):
                        tmp_data = re_host_port_info.group(0)
                        tmp_data = tmp_data.split(r"/")
                        for i in tmp_data:
                            if "host" in i:
                                encl_dict[encl].update({"host":i[4:]})
                            elif "port" in i:
                                encl_dict[encl].update({"port":i[5:]}) # skip "-"
                            elif "expander" in i:
                                encl_dict[encl].update({"expander":i[9:]})
                    if re_end_device_info.group(0):
                        tmp_data = re_end_device_info.group(0)
                        tmp_data = tmp_data.split(r"/")
                        for i in tmp_data:
                            if "end_device" in i:
                                encl_dict[encl].update({"end_device":i[11:]})
                            elif "target" in i:
                                encl_dict[encl].update({"target":i[7:]})
                
        if expander_dict:
            address_dict.update(expander_dict)
        if drive_dict:
            address_dict.update(drive_dict)
        if encl_dict:
            address_dict.update(encl_dict)
        return address_dict



def main():
    func = find_check_devcie()
    result = func.run()
    for _dev in func.encl_devs:
        if 'master' in access_mode.send_cmd("getboardid", _dev, bus='', pass_through='')[0]:
            master_dev = _dev
    gem_cli = GemCli(master_dev, access_mode=access_mode, CLI='', bus='', pass_through='')
    recv_data = gem_cli.send_cmd("getdrivebaycount")[0]
    drive_bay_count = int(recv_data.split(' ')[1])
    if drive_bay_count == 106:
        func.print_drives_info('4U106', result)
    elif drive_bay_count == 12:
        func.print_drives_info('2U12', result)
    elif drive_bay_count == 24:
        func.print_drives_info('2U24', result)
    pprint(func.get_device_host_port())

    



if __name__ == "__main__":
    main()
