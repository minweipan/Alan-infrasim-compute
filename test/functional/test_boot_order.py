'''
*********************************************************
Copyright @ 2015 EMC Corporation All Rights Reserved
*********************************************************
'''
import unittest
from infrasim import model
from test import fixtures
import subprocess
import time
import re
import os

class test_boot_order(unittest.TestCase):

    def setUp(self):
        fake_config = fixtures.FakeConfig()
        self.conf = fake_config.get_node_info()
        os.system("touch /tmp/test.iso")
        self.conf['compute']['cdrom'] = "/tmp/test.iso"
        self.conf['compute']['boot_order'] = 'ncd'
        node = model.CNode(self.conf)
        node.init()
        node.precheck()
        node.start()
        time.sleep(3)

        # Start sol in a subprocess
        self.fw = open('/tmp/test_sol', 'wb')
        self.fr = open('/tmp/test_sol', 'r')
        self.p_sol = subprocess.Popen("ipmitool -I lanplus -U admin -P admin "
                                      "-H 127.0.0.1 sol activate",
                                      shell=True,
                                      stdin=subprocess.PIPE,
                                      stdout=self.fw,
                                      stderr=self.fw,
                                      bufsize=0)

    def tearDown(self):
        self.fw.close()
        self.fr.close()
        self.p_sol.stdin.write("~.")
        self.p_sol.kill()
        node = model.CNode(self.conf)
        node.init()
        node.stop()
        node.terminate_workspace()
        os.remove("/tmp/test_sol")
        os.remove("/tmp/test.iso")
        self.conf = None

    def test_boot_order_ncd(self):
        p_power = subprocess.Popen("ipmitool -I lanplus -H admin -P admin "
                                   "-H 127.0.0.1 chassis power reset",
                                   shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        p_power.communicate()
        p_power_ret = p_power.returncode
        if p_power_ret != 1:
            raise self.fail("Fail to send chassis power reset command")

        # Check if sol session has get something
        time.sleep(16)
        sol_out = self.fr.read()
        # SOL will print a hint at first
        # After this hint message, any ASCII char indicates
        # the SOL receives something and it means SOL is alive
        p = re.compile(r'\[\d+;\d+H')
        sol_out = re.sub(p, '', sol_out)
        p = re.compile(r'\[m')
        sol_out = re.sub(p, '', sol_out)
        p = re.compile(r'\[\d+;\d+;lm')
        sol_out = re.sub(p, '', sol_out)
        p = re.compile(r'[^A-Za-z0-9 ():/\n.)]')
        sol_out = re.sub(p, '', sol_out)
        network_index = sol_out.find('iPXE')
        disk_index = sol_out.find('Disk')
        cdrom_index = sol_out.find('DVD/CD')
        boot_order = True if network_index < disk_index < cdrom_index else False

        assert network_index is not -1
        assert disk_index is not -1
        assert cdrom_index is not -1
        assert boot_order is True