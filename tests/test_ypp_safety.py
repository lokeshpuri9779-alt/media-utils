import unittest
from ypp_safety import evaluate, disclosure_required

class YPPSafetyTests(unittest.TestCase):
    def test_duplicate_blocks(self):
        p={"videos":{"v1":{"title":"Why Venus is the hottest planet","script":"thick atmosphere traps heat"}}}
        r=evaluate("Why Venus is the hottest planet","",{"script":"thick atmosphere traps heat","genre":"space"},p)
        self.assertEqual(r["decision"],"block")
    def test_original_allows(self):
        r=evaluate("A new original story","",{"script":"An original narrative about a distant signal","genre":"fiction"},{"videos":{}})
        self.assertEqual(r["decision"],"allow")
    def test_realistic_synthetic_requires_disclosure(self):
        self.assertTrue(disclosure_required({"realistic_synthetic":True}))
    def test_unlicensed_blocks(self):
        r=evaluate("x","",{"script":"original words","genre":"tech","copyright_unlicensed":True},{"videos":{}})
        self.assertEqual(r["decision"],"block")

if __name__=="__main__": unittest.main()
