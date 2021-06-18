#! /usr/bin/env python3


import sys
import os
import re
import subprocess


ANY = ".*"


cust_vpd_templates = {
    'rss_2x': {0: 'FRUID Ver', 2: 'OEM ID', 5: 'Config Selector', 7: 'Reserved',
               8: 'Seagete PN', 0x28: 'Seagate SN', 0x48: 'Revision',
               0x58: 'Customer/FRU PN', 0x78: 'Customer/FRU SN', 0x98: 'FRU Rev', 0xa8: 'CRC 32',
               0x300: 'TLA PN', 0x320: 'TLA SN', 0x340: 'TLA PID', 0x360: 'FRU Description'},
    'hpe_ct': {0: 'Saleable SN', 0x16: 'Saleable PN', 0x25: 'Serial Number', 0x3a: 'Part Number',
               0x4b: 'Spare PN', 0x5a: 'Model Name', 0x72: 'Revision', 0x7a: 'Checksum'},
    'ibm_chs': {0: 'VPD Version', 1: 'MTM', 8: 'System (1S) SN', 15: 'FRU (11S) SN', 37: 'All Zeros'},
    'ibm_ctrl': {0: 'VPD Version', 1: 'FRU (11S) SN', 23: 'All Zeros'}
}



def execCommand(command, expected=None, retries=0):
    #print("execCommand command = ", command)

    proc = subprocess.Popen([b'/bin/bash'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    bStdout, bStderr = proc.communicate(bytes(command, 'ascii'))
    stdout = bStdout.decode('utf-8')
    stderr = bStderr.decode('utf-8')

    if expected is None:
        isExpected = True
    else:
        isExpected = False
        if not isinstance(expected, list):
            isExpected = (expected in stdout)
        else:
            for expectedString in expected:
                if expectedString in stdout:
                    isExpected = True
                    break

    if proc.returncode or stderr or (not isExpected):
        if retries > 0:
            execCommand(command, expected, retries-1)
        else:
            if proc.returncode or stderr:
                errorMessage = "subprocess.Popen returncode=%s - stderr=%s" % (proc.returncode, stderr)
                raise Exception(errorMessage)
            else:
                errorMessage = "Command: %s - Expected: %s is not in Return Data: %s" % (command, expected, stdout)
                raise Exception(errorMessage)

    return stdout, stderr


def send_cmd(device, cmd, expected=None):
    command = "sudo /usr/local/bin/wbcli {} -pt:0:127 '{}'".format(device, cmd)
    return execCommand(command, expected)


def send_save_cmd(file_name, device, cmd, expected=None):
    stdout, stderror = send_cmd(device, cmd, expected)

    command = "sudo /usr/local/bin/wbcli {} '{}'".format(device, cmd)
    File = open(file_name, 'a+')
    File.write("\n{}\n".format(command))
    File.write(stdout)
    File.write("\n")
    File.flush()   
    os.fsync(File.fileno())         # Block till data is actually written
    File.close()




def list_devices(dev_type_pat=ANY, vendor_id_pat=ANY, prod_id_pat=ANY, sd_pat=ANY, sg_pat=ANY,
                     timeout=30, ap_controller_ip=None, username=None, password=None):
        """
        List devices based on re-based patterns on device type, vendor id, product id,
        sd_path and sg_path patterns. List all the devices by default.

        Args:
            dev_type_pat         : String    : Device type pattern
            vendor_id_pat        : String    : Vendor ID pattern
            prod_id_pat          : String    : Product ID pattern
            sd_pat               : String    : SD path pattern
            sg_pat               : String    : SG path pattern
            ap_controller_ip     : String    : IP address of AP controller on which command needs to be sent
                                           (None in case of JBOD controller)
            username             : String    : AP controller host username
            password             : String    : AP controller host password

        Returns:
            devs                 : List      : Device list with devices satisfying given pattern in parameters

        Raises:
            None
        """
        out, err = execCommand('sudo lsscsi -g', dev_type_pat)

        lines = re.split("\n", out.strip())

        devs = []
        for line in lines:
            parts = re.split(r"[\s|\]]+", line.strip())
            host_id = parts[0].strip(" []")
            dev_type = parts[1].strip()
            vendor_id = parts[2].strip()
            prod_id = ' '.join(parts[3:-3])
            prod_rev = parts[-3].strip()
            sd_path = parts[-2].strip()
            sg_path = parts[-1].strip()
            if re.search(dev_type_pat, dev_type) and re.search(vendor_id_pat, vendor_id) and \
                re.search(prod_id_pat, prod_id) and re.search(sd_pat, sd_path) and \
                    re.search(sg_pat, sg_path):
                devs.append((host_id, dev_type, vendor_id, prod_id, prod_rev, sd_path, sg_path))

        return devs


def getboardid(device):
        """
        This function sends GEM command: getboardid and return (ID, Mode)
        """
        stdout, stderror = send_cmd(device, "getboardid", "Mode: ")
        if stderror:
            err_msg = "error getting board mode"
            raise Exception(err_msg)

        # Board ID: 0, Mode: master
        mode = stdout.strip().split()[-1]
        board_id = stdout.strip().split(',')[0][-1]

        return board_id, mode


def vpd_hex_dump(device, page, expected=None):
    command = "vpd {}".format(page)
    stdout, stderr = send_cmd(device, command)

    lines = stdout.splitlines()

    header = ''
    size = -1
    addr_last = -2

    for line in lines:
        if re.search(r'VPD.*off=\d+\s+size=(\d+)', line):
            header = line
            size = int(re.search(r'VPD.*off=\d+\s+size=(\d+)', line).group(1))
        elif re.match(r'[0-9a-f]{4}:\s\w\w\s\w\w\s\w\w', line):
            addr_last = int(re.split(r':\s', line)[0], 16)

    if (size != 0) and (addr_last + 16 != size):
        raise Exception("Size is wrong")

    header = ''
    data = []
    for line in lines:
        line = line.strip()
        if re.search(r'VPD.*off=\d+\s+size=(\d+)', line):
            header = line
            size = int(re.search(r'VPD.*off=\d+\s+size=(\d+)', line).group(1))
        elif re.match(r'[0-9a-f]{4}:\s\w\w\s\w\w\s\w\w', line):
            addr_header, bytes_str = re.split(r':\s', line)
            data.extend(re.split(r'\s', bytes_str))

    return header, data


def print_vpd_hex_ascii(vpd_list, display=True):
    """
    Add ASCII string to the VPD dump list
    Input:
    ['0000: 02 01 00 00 00 00 00 00 30 39 39 32 38 38 36 2d',
     '0010: 30 38 00 00 00 00 00 00 00 00 00 00 00 00 00 00']
    Returns:
    ['0000: 02 01 00 00 00 00 00 00 30 39 39 32 38 38 36 2d  ........0992886-',
     '0010: 30 38 00 00 00 00 00 00 00 00 00 00 00 00 00 00  08..............']
    """
    dump_lines = []
    hex_str = ''
    string = ''
    addr_header = ''
    for i in range(len(vpd_list)):
        if i % 16 == 0:
            addr_header = "%04x"%(i)
        v = vpd_list[i]
        v_d = v_h = v
        if isinstance(v, int):
            v_d = v
            v_h = "%02x" % v
        elif isinstance(v, str):
            v_h = v
            v_d = int(v, 16)

        c = "."
        if v_d >= 32 and v_d <= 126:
            c = chr(v_d)
        hex_str += v_h + ' '
        string += c

        if i % 16 == 15 or i == (len(vpd_list) - 1):
            line = addr_header + ": " + hex_str + " " + string
            hex_str = ''
            string = ''
            dump_lines.append(line)

    return dump_lines


def print_vpd_comparison(file_name, data_before, data_after, header_before='', header_after='', headers=[]):
    '''
    Print and compare the VPD data after and before VPD write
    with '+' as delimiter if the data are different, example:
    Addr  AFTER VPD PROGRAMMING                                               BEFORE VPD PROGRAMMING                                           
    ----  -----------------------------------------------------------------   -----------------------------------------------------------------
    0000: 02 01 00 00 00 00 00 00 30 39 39 32 38 38 36 2d  ........0992886- | 02 01 00 00 00 00 00 00 30 39 39 32 38 38 36 2d  ........0992886-
    0010: 30 39 00 00 00 00 00 00 00 00 00 00 00 00 00 00  09.............. + 30 38 00 00 00 00 00 00 00 00 00 00 00 00 00 00  08..............
    0020: 00 00 00 00 00 00 00 00 50 4d 46 30 39 39 32 38  ........PMF09928 | 00 00 00 00 00 00 00 00 50 4d 46 30 39 39 32 38  ........PMF09928
    0030: 38 36 47 33 39 43 4e 00 00 00 00 00 00 00 00 00  86G39CN......... + 38 36 47 33 39 43 58 00 00 00 00 00 00 00 00 00  86G39CX.........
    '''
    vpd_str_b = print_vpd_hex_ascii(data_before, display=False)
    vpd_str_a = print_vpd_hex_ascii(data_after, display=False)
    len_a = len(vpd_str_a)
    len_b = len(vpd_str_b)
    len_max = len_a
    len_min = len_b
    if len_a < len_b:
        len_max = len_b
        len_min = len_a

    lines2print = [""]
    if headers:
        lines2print.append("{:4s}  {:70s}      {:70s}".format("Addr", headers[0], headers[1]))
    else:
        lines2print.append("{:4s}  {:65s}           {:65s}".format("Addr", "AFTER VPD PROGRAMMING", "BEFORE VPD PROGRAMMING"))
    lines2print.append("{:4s}  {:65s}           {:65s}".format("-"*4, "-"*65, "-"*65))
    if header_before or header_after:
        if header_before == header_after:
            delimiter = '|'
        else:
            delimiter = '+'
        lines2print.append("{:71s}     {}     {:65s}".format(header_after, delimiter, header_before))

    for i in range(len_min):
        if vpd_str_a[i] == vpd_str_b[i]:
            delimiter = '     |     '
            if vpd_str_b[i][6:] != "ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff  ................":
                lines2print.append(vpd_str_a[i] + delimiter + vpd_str_b[i][6:])
        else:
            delimiter = '     +     '
            lines2print.append(vpd_str_a[i] + delimiter + vpd_str_b[i][6:])

    if len_a > len_b:
        for i in range(len_min, len_max):
            if vpd_str_a[i][6:] != "ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff  ................":
                lines2print.append(vpd_str_a[i] + '     +     ')
    if len_a < len_b:
        for i in range(len_min, len_max):
            lines2print.append("{:5s} {:65s}     +     {}".format(vpd_str_b[i][0:5], " ", vpd_str_b[i][6:]))


    File = open(file_name, 'a+')
    File.write("\n".join(lines2print))
    File.write("\n")
    File.flush()   
    os.fsync(File.fileno())         # Block till data is actually written
    File.close()





def verify_vpd_16(file_name, device):
    stdout, stderr = send_cmd(device, "set_midplanevpd")
    File = open(file_name, 'a+')
    File.write("\n")
    File.write(stdout)
    File.write("\n")

    lines=stdout.split('\n')

    vpd_dict  = {}
    vpd_index = []
    for line in lines:
        re_result = re.search(r"=*(\d+):", line)
        if re_result:
            index = int(re_result.groups()[0])
            vpd_dict[index] = line
            vpd_index.append(index)

    for index in vpd_index:
        stdout, stderr = send_cmd(device, "set_midplanevpd {}".format(index))
        File.write("{} = {}\n".format(vpd_dict[index], stdout))

    File.flush()   
    os.fsync(File.fileno())         # Block till data is actually written
    File.close()


def verify_vpd_48(file_name, device):
    """    
    DH-2RY9V
    vpd:
    ctrl:
        ebod_vendor_id: [5, 8, 'DellEMC ', 'Ascii']
        ebod_product_id: [6, 8, 'EMM     ', 'Ascii']
        ethernet_flags: [13, 1, '00', 'Hex']

    1026666-03
    vpd:
    ctrl:
        black_list: [12]
        gray_list: [1, 2, 3, 4]
        manufacturing_datetime: [1, 3, 'RENDER', 'Hex']
        expander_sas_address: [2, 8, 'RENDER', 'Ascii']
        ebod_serial_number: [3, 0, 'RENDER:PCBA-SN', 'Ascii']
        ebod_part_number: [4, 10, '1026666-03', 'Ascii']
        ebod_vendor_id: [5, 8, 'SEAGATE ', 'Ascii']
        ebod_product_id: [6, 8, '-E12EBD ', 'Ascii']
        ebod_mac_address: [7, 6, 'RENDER', 'Hex']
        cid: [8, 24, '00000000000000000000000000000000', 'Ascii'] # 8 bytes of string + 16 Bytes of 0x00 (if string = NULL = 0 is not displayed)
        canister_id_vendor_id: [9, 8, 'SEAGATE ', 'Ascii']
        canister_id_family_id: [10, 2, '00', 'Ascii']
        canister_id_family_member_id: [11, 2, '13', 'Ascii']
        #canister_id_vendor_specific should be 12 bytes of 0x00 per ND,
        #but it's a known issue that the "set_ebodvpd 12" command doesn’t provide a mechanism to write binary data to this field
        canister_id_vendor_specific: [12, 12, '00 00 00 00 00 00 00 00 00 00 00 00', 'Hex'] 
        ethernet_flags: [13, 1, '07', 'Hex']
    """

    stdout, stderr = send_cmd(device, "set_ebodvpd")
    File = open(file_name, 'a+')
    File.write("\n")
    File.write("VPD 48 for Device: {}\n\n".format(device))

    lines=stdout.split('\n')

    vpd_dict  = {}
    vpd_index = []
    for line in lines:
        re_result = re.search(r"=*(\d+):", line)
        if re_result:
            index = int(re_result.groups()[0])
            vpd_dict[index] = line
            vpd_index.append(index)

    for index in vpd_index:
        stdout, stderr = send_cmd(device, "set_ebodvpd {}".format(index))
        File.write("{} = {}".format(vpd_dict[index], stdout))

    File.flush()   
    os.fsync(File.fileno())         # Block till data is actually written
    File.close()


def verify_vpd_49(file_name, device, header_49, data_49):
    File = open(file_name, 'a+')
    File.write("\nheader_49 = \n")
    File.write(header_49)
    File.write("\n")

        

    PVD_49_Table = {
                       "vpd_major_ver"   : [0,    1,  '02',                       'Hex'],
                       "vpd_minor_ver"   : [1,    1,  '01',                       'Hex'],
                       "oem_id"          : [2,    3,  '00 00 00',                 'Hex'],
                       "config_selector" : [5,    2,  '00 00',                    'Hex'],
                       "reserved"        : [7,    1,  '00',                       'Hex'],

                       "part_number"     : [8,    32, '81-00000123-00-01',        'Ascii'],
                       "serial_number"   : [40,   32, 'RENDER:ISA-SN',            'Ascii'],
                       "revision"        : [72,   16, 'RENDER:ISA-REV',           'Ascii'],

                       "customer_pn"     : [88,   32, '2RY9V',                    'Ascii'],
                       "customer_sn"     : [120,  32, 'RENDER:CUST-SN',           'Ascii'],
                       "customer_rev"    : [152,  16, 'RENDER:CUST-REV',          'Ascii'],
                       "crc"             : [168,  4,  'RENDER',                   'Hex'],

                       "fru_description" : [864,  64, 'ASSY,ENCL,IOM,ME4,2U',     'Ascii'],
                   }

    for name in PVD_49_Table:
        offset, length, value, value_type = PVD_49_Table[name]
        vpd_value = ''
        if value_type == 'Ascii':
            for index in range(length):
               hex_value = int(data_49[offset+index], 16)
               if hex_value > 0:
                   vpd_value += chr(hex_value)
        else:
            vpd_value = ' '.join(data_49[offset:offset+length])
            vpd_value = vpd_value.upper()

        if vpd_value == value:
            File.write("\n{} : {} ==== {}".format(name, vpd_value, value))
        else:
            File.write("\n{} : {} !!!! {}".format(name, vpd_value, value))

    File.write("\n")
    File.flush()   
    os.fsync(File.fileno())         # Block till data is actually written
    File.close()


def verify_vpd_18(file_name, device, header_18, data_18):
    File = open(file_name, 'a+')
    File.write("\nheader_18 = \n")
    File.write(header_18)
    File.write("\n")

    PVD_18_Table = {
                       "vpd_major_ver"   : [0,    1,  '02',                       'Hex'],
                       "vpd_minor_ver"   : [1,    1,  '01',                       'Hex'],
                       "oem_id"          : [2,    3,  'BC 30 5B',                 'Hex'],
                       "config_selector" : [5,    2,  '20 00',                    'Hex'],
                       "reserved"        : [7,    1,  '00',                       'Hex'],
                       "part_number"     : [8,    32, 'RENDER:FRU-PN',            'Ascii'],
                       "serial_number"   : [40,   32, 'RENDER:FRU-SN',            'Ascii'],
                       "revision"        : [72,   16, 'RENDER:FRU-REV',           'Ascii'],
                       "customer_pn"     : [88,   32, 'H8X8M',                    'Ascii'],
                       "customer_sn"     : [120,  32, 'RENDER:CUST-SN',           'Ascii'],
                       "customer_rev"    : [152,  16, 'RENDER:CUST-REV',          'Ascii'],
                       "crc"             : [168,  4,  'RENDER',                   'Hex'],
                       "tla_pn"          : [768,  32, '00',                       'Hex'],
                       "tla_sn"          : [800,  32, '00',                       'Hex'],
                       "tla_pid"         : [832,  32, '00',                       'Hex'],
                       "fru_description" : [864,  64, 'ASSY,CHAS,RKMNT,2U12NPCM', 'Ascii'],
                       "ip_data"         : [2624, 128, '01 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 0a 00 00 02 00 00 00 00 00 00 00 00 00 00 00 00 ff ff ff 00 00 00 00 00 00 00 00 00 00 00 00 00 0a 00 00 01 04 00 00 00 00 00 00 00 00 00 8d 6e 01 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 0a 00 00 03 00 00 00 00 00 00 00 00 00 00 00 00 ff ff ff 00 00 00 00 00 00 00 00 00 00 00 00 00 0a 00 00 01 04 00 00 00 00 00 00 00 00 00 07 04', 'Hex'],
                   }

    for name in PVD_18_Table:
        offset, length, value, value_type = PVD_18_Table[name]
        vpd_value = ''
        if value_type == 'Ascii':
            for index in range(length):
               hex_value = int(data_18[offset+index], 16)
               if hex_value > 0:
                   vpd_value += chr(hex_value)
        else:
            vpd_value = ' '.join(data_18[offset:offset+length])
            vpd_value = vpd_value.upper()

        if vpd_value == value:
            File.write("\n{} : {} ==== {}".format(name, vpd_value, value))
        else:
            File.write("\n{} : {} !!!! {}".format(name, vpd_value, value))

    File.write("\n")
    File.flush()   
    os.fsync(File.fileno())         # Block till data is actually written
    File.close()

def verify_vpd_pcm_custom(file_name, device, header_60, data_60, header_61, data_61):
    File = open(file_name, 'a+')
    File.write("\nheader_60 = ")
    File.write(header_60)
    #File.write("\n")
    File.write("\nheader_61 = ")
    File.write(header_61)
    File.write("\n")

    PVD_PCM_CUSTOM_Table = {
                       "vpd_major_ver"   : [0,    1,  '02',                       'Hex'],
                       "vpd_minor_ver"   : [1,    1,  '01',                       'Hex'],
                       "oem_id"          : [2,    3,  '00 00 00',                 'Hex'],
                       "config_selector" : [5,    2,  '00 00',                    'Hex'],
                       "reserved"        : [7,    1,  '00',                       'Hex'],
                       "part_number"     : [8,    32, '00',                       'Ascii'],
                       "serial_number"   : [40,   32, '00',                       'Ascii'],
                       "revision"        : [72,   16, '00',                       'Ascii'],
                       "customer_pn"     : [88,   32, '3PD98',                    'Ascii'],
                       "customer_sn"     : [120,  32, 'RENDER',                   'Ascii'],
                       "customer_rev"    : [152,  16, 'RENDER',                   'Ascii'],
                       "crc"             : [168,  4,  'RENDER',                   'Hex'],
                       "fru_description" : [864,  64, 'PWR SPLY,2U,ME4',          'Ascii'],
                   }

    for name in PVD_PCM_CUSTOM_Table:
        offset, length, value, value_type = PVD_PCM_CUSTOM_Table[name]
        vpd_value_60 = ''
        vpd_value_61 = ''
        if value_type == 'Ascii':
            for index in range(length):
               hex_value = int(data_60[offset+index], 16)
               if hex_value > 0:
                   vpd_value_60 += chr(hex_value)

               hex_value = int(data_61[offset+index], 16)
               if hex_value > 0:
                   vpd_value_61 += chr(hex_value)
        else:
            vpd_value_60 = ' '.join(data_60[offset:offset+length])
            vpd_value_60 = vpd_value_60.upper()

            vpd_value_61 = ' '.join(data_61[offset:offset+length])
            vpd_value_61 = vpd_value_61.upper()


        if (vpd_value_60 == value) and (vpd_value_61 == value):
            File.write("\n{} : {} ==== {} ==== {}".format(name, vpd_value_60, vpd_value_61, value))
        else:
            File.write("\n{} : {} !!!! {} !!!! {}".format(name, vpd_value_60, vpd_value_61, value))

    File.write("\n")
    File.flush()   
    os.fsync(File.fileno())         # Block till data is actually written
    File.close()


def verify_vpd_pcm(file_name, device):
    """    
    1001661-08
    vpd:
    pcm:
        gray_list: [1, 2, 3, 5]
        pcm_vendor_name: [1, 8, "FLEX    ", "Ascii"]
        pcm_product_name: [2, 16, "SP-PCM2-HE580-AC", "Ascii"]
        pcm_part_number: [3, 10, "1001661-08", "Ascii"]
        pcm_serial_number: [5, 15, "RENDER", "Ascii"]
    """

    stdout, stderr = send_cmd(device, "set_pcmvpd")
    File = open(file_name, 'a+')
    File.write("\n")
    File.write("VPD PCM for Device: {}\n\n".format(device))

    lines=stdout.split('\n')
    #print(lines)

    vpd_dict  = {}
    vpd_index = []
    for line in lines:
        re_result = re.search(r"= (\d+) ", line)
        if re_result:
            index = int(re_result.groups()[0])
            vpd_dict[index] = line
            vpd_index.append(index)
    #print(vpd_dict)
    #print(vpd_index)


    for index in vpd_index:
        stdout_40, stderr_40 = send_cmd(device, "set_pcmvpd 1 {}".format(index))
        #print(stdout_40)
        stdout_41, stderr_41 = send_cmd(device, "set_pcmvpd 2 {}".format(index))
        #print(stdout_41)
        if stdout_40 == stdout_41:
            File.write("{} == {} == {}\n".format(vpd_dict[index], stdout_40.strip(), stdout_41.strip()))
        else:
            File.write("{} !! {} !! {}\n".format(vpd_dict[index], stdout_40.strip(), stdout_41.strip()))

    File.flush()   
    os.fsync(File.fileno())         # Block till data is actually written
    File.close()



#------------------------------------------------------------------------------
if __name__ == '__main__':
    print ("This is the name of the script: ", sys.argv[0])
    print ("Number of arguments: ", len(sys.argv))
    print ("The arguments are: " ,  str(sys.argv))

    if len(sys.argv) > 1:
        VERIFY_LOG = '{}_vpd_verify.txt'.format(sys.argv[1])
    else:
        VERIFY_LOG = 'vpd_verify.txt'
    print ("Save Verification Result to -> {}".format(VERIFY_LOG))

    File = open(VERIFY_LOG, 'w')
    File.flush()   
    os.fsync(File.fileno())         # Block till data is actually written
    File.close()



    all_ses_devs = list_devices(dev_type_pat="encl")
    print("all_ses_devs = %s\n" % (all_ses_devs,))

    for ses_dev_list in all_ses_devs:
        device = ses_dev_list[-1]

        board_id, mode = getboardid(device)
        print("board_id = %s\n" % (board_id,))
        print("%s device = %s\n" % (mode, device))

        header_48, data_48 = vpd_hex_dump(device, 48)                                     # ctrl
        header_49, data_49 = vpd_hex_dump(device, 49)                                     # ctrl customer
        print_vpd_comparison(VERIFY_LOG, data_48, data_49, headers=[header_49, header_48])
        verify_vpd_48(VERIFY_LOG, device)
        verify_vpd_49(VERIFY_LOG, device, header_49, data_49)

        if mode == "master":
            master_device = device
            print("master device = %s\n" % (master_device,))


    device = master_device


    
    send_save_cmd(VERIFY_LOG, device, "ver",    "Battery 2")
    send_save_cmd(VERIFY_LOG, device, "getvpd", "PCM 2")

    header_16, data_16 = vpd_hex_dump(device, 16)                                         # Midplane A
    header_17, data_17 = vpd_hex_dump(device, 17)                                         # Midplane B
    print_vpd_comparison(VERIFY_LOG, data_16, data_17, headers=[header_17, header_16])

    verify_vpd_16(VERIFY_LOG, device)

    header_18, data_18 = vpd_hex_dump(device, 18)                                         # Midplane Customer A
    header_19, data_19 = vpd_hex_dump(device, 19)                                         # Midplane Customer B
    print_vpd_comparison(VERIFY_LOG, data_18, data_19, headers=[header_19, header_18])

    verify_vpd_18(VERIFY_LOG, device, header_19, data_19)
    

    header_40, data_40 = vpd_hex_dump(device, 40)                                         # PCM 1
    header_41, data_41 = vpd_hex_dump(device, 41)                                         # PCM 2
    print_vpd_comparison(VERIFY_LOG, data_41, data_40, headers=[header_40, header_41])

    verify_vpd_pcm(VERIFY_LOG, device)

    
    header_42, data_42 = vpd_hex_dump(device, 42)                                         # PCM 3
    header_43, data_43 = vpd_hex_dump(device, 43)                                         # PCM 4
    print_vpd_comparison(VERIFY_LOG, data_43, data_42, headers=[header_42, header_43])

    header_60, data_60 = vpd_hex_dump(device, 60)                                         # PCM 1 Customer
    header_61, data_61 = vpd_hex_dump(device, 61)                                         # PCM 2 Customer
    print_vpd_comparison(VERIFY_LOG, data_61, data_60, headers=[header_60, header_61])

    verify_vpd_pcm_custom(VERIFY_LOG, device, header_60, data_60, header_61, data_61)

    header_62, data_62 = vpd_hex_dump(device, 62)                                         # PCM 3 Customer
    header_63, data_63 = vpd_hex_dump(device, 63)                                         # PCM 4 Customer
    print_vpd_comparison(VERIFY_LOG, data_63, data_62, headers=[header_62, header_63])
    

