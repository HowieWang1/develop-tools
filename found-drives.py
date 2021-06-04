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

        self.attach_expander_disk = comm_dev_funs.get_attached_expander_and_disk(self.encl_devs)['disk'] 
        # return value: {'expander':[], 'disk':[('/dev/sdal', '/dev/sg1'),...]}
    
    def run(self):
        disk_mapping_result = self.update_sas_dev()
        log.info("{}".format('#'*10))
        log.info("the mapping relationship is {}".format(disk_mapping_result))
        print(disk_mapping_result)
        log.info("{}".format('#'*10))


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
        for dev_component in self.attach_expander_disk:              # for each device /dev/sg
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
        for num in range(106):    # for now, just focus on Cobra+
            recv_data = gem_cli.send_cmd("getdrivestatus {}".format(num))[0]
            if "invalid" in recv_data.lower():
                break                               # no enough drives
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
    
    #def check_PHY_counter(self):
        # in this function, will use fio command to write/read some data to the devices, then check the PHY_counter.
        



def main():
    func = find_check_devcie()
    func.run()



if __name__ == "__main__":
    main()
