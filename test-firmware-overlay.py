"""Verify installable all-platform wizard and restricted x86 disk automation."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('overlay','firmware-overlay.py')
overlay=importlib.util.module_from_spec(spec);spec.loader.exec_module(overlay)

class OverlayTests(unittest.TestCase):
    def test_all_platforms_get_wizard_and_fresh_install_address(self):
        for platform in ('x86','rockchip','filogic','qualcommax-ipq807x'):
            with self.subTest(platform=platform), tempfile.TemporaryDirectory() as temp:
                p=pathlib.Path(temp)
                overlay.install(p,'25.12.2',platform,'lite')
                self.assertIn('BE FREE AND UNAFRAID',(p/'etc/banner').read_text())
                self.assertIn('192.168.11.1',(p/'etc/board.d/99-xzt8wrt-address').read_text())
                self.assertTrue((p/'www/luci-static/resources/view/xzt8wrt/setup.js').is_file())
                acl=json.loads((p/'usr/share/rpcd/acl.d/luci-app-xzt8wrt-setup.json').read_text())
                self.assertEqual(acl['luci-app-xzt8wrt-setup']['write']['uci'],['network','dhcp','firewall'])
                self.assertNotIn('file',acl['luci-app-xzt8wrt-setup']['write'])
                self.assertEqual((p/'usr/sbin/xzt8wrt-expand-root').exists(),platform=='x86')
                if platform=='x86':self.assertTrue((p/'etc/rc.d/S19xzt8wrt-expand-root').is_symlink())

if __name__=='__main__':unittest.main()
