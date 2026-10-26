import importlib.util, pathlib, unittest
path=pathlib.Path(__file__).resolve().parents[1]/"scripts"/"send.py"
spec=importlib.util.spec_from_file_location("discord_feed",path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SplitTests(unittest.TestCase):
 def test_emoji_and_exact_reconstruction(self):
  text=("한국어 🧪 테스트 문장입니다.\n\n"*400)
  parts=mod.chunks(text,1900)
  self.assertEqual("".join(parts),text)
  self.assertTrue(all(mod.units(p)<=1900 for p in parts))
 def test_unbroken_long_token(self):
  text="x"*5500
  parts=mod.chunks(text)
  self.assertEqual("".join(parts),text)
  self.assertEqual(len(parts),3)
 def test_empty_rejected(self):
  with self.assertRaises(ValueError):mod.chunks("   ")
 def test_multiline_markdown(self):
  text="# 제목\n\n"+("- **항목** [링크](https://example.com)\n"*200)
  self.assertEqual("".join(mod.chunks(text)),text)
if __name__=="__main__":unittest.main()
