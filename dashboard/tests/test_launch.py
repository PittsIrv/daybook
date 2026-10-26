import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from launch import probe

class LaunchTests(unittest.TestCase):
    def test_reuses_only_matching_mode(self):
        with patch('launch.urllib.request.urlopen',return_value=io.BytesIO(b'{"application":"daybook","demo":false}')):
            self.assertEqual(probe(8765,False),'running')
        with patch('launch.urllib.request.urlopen',return_value=io.BytesIO(b'{"application":"daybook","demo":false}')):
            self.assertEqual(probe(8765,True),'occupied')

    def test_does_not_claim_another_service(self):
        with patch('launch.urllib.request.urlopen',return_value=io.BytesIO(b'{"application":"other"}')):
            self.assertEqual(probe(8765,False),'occupied')
        with patch('launch.urllib.request.urlopen',side_effect=HTTPError('url',404,'Not found',{},None)):
            self.assertEqual(probe(8765,False),'occupied')
        with patch('launch.urllib.request.urlopen',side_effect=URLError('Connection refused')):
            self.assertEqual(probe(8765,False),'stopped')

if __name__=='__main__':unittest.main()
