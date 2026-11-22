import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from audio_mixing_claim_audit.audit import audit, evidence, paragraphs, pattern
from audio_mixing_claim_audit.phrases import AUDIOMIXING, NOAUDIOMIXING, GENERIC_NAMES


class AuditTests(unittest.TestCase):
    def test_phrases(self):
        self.assertEqual(tuple(map(lambda x: len(set(x)), (AUDIOMIXING, NOAUDIOMIXING, GENERIC_NAMES))), (50, 24, 24))
        yes, no = pattern(AUDIOMIXING), pattern(NOAUDIOMIXING)
        for phrase in NOAUDIOMIXING:
            with self.subTest(phrase=phrase):
                self.assertIsNotNone(yes.search(phrase))
                self.assertIsNone(yes.search(no.sub(' ', phrase)))
        self.assertEqual(paragraphs('a\n```\nmix audio\n```\nb'), ['a', 'b'])

    def test_routes(self):
        cases = ['import pydub as p\np.AudioSegment()\nx.overlay()', 'from pydub import AudioSegment as A\ns=A.from_file()\ns.overlay()', 'import sox as s\ns.Combiner("mix")', 'from sox import Combiner as C\nC()\nx.build(combine_type="mix-power")', 'import ffmpeg\nffmpeg.filter(x, "amix")', 'from ffmpeg import filter_ as f\nf(x, kind="amix")', 'import moviepy\nmoviepy.CompositeAudioClip()', 'from moviepy.audio.AudioClip import CompositeAudioClip as C\nC()', 'from other import mix_audio as m\nm()']
        cases += ['x.' + name + '()' for name in GENERIC_NAMES]
        cases += ['from pydub import AudioSegment as A\nA.' + name + '()\nx.overlay()' for name in ('from_file','from_mp3','from_ogg','from_wav','silent','empty')]
        for case in cases:
            with self.subTest(case=case): self.assertTrue(evidence(case))

    def test_non_evidence(self):
        cases = ['import pydub', 'from pydub import AudioSegment\nAudioSegment()', 'x.overlay()', 'from pydub import AudioSegment\nAudioSegment().append(x)', 'import sox\nsox.Combiner()', 'x.build("mix")', 'import sox\nsox.Transformer().build("mix")', 'x.filter("amerge")', 'x.filter_("concat")', 'x.filter()', 'filter("amix")', 'import moviepy\nmoviepy.concatenate_audioclips()', 'import moviepy\nmoviepy.CompositeVideoClip()', 'x.demix()', 'x.split_stems()', 'x.separate_audio()', 'x.extract_stems()', 'x.generate_audio()', 'x.recognize_speech()', 'x + y', 'import subprocess\nsubprocess.run("ffmpeg -filter amix")', '"mix audio"', 'x.mix_audio', 'invalid !!!', 'def mix_audio(): pass\nx.mix_audio()', 'import pydub\npydub = 1\npydub.AudioSegment()\nx.overlay()', 'from pydub import AudioSegment as A\nwith x as A: A()\nx.overlay()']
        cases += ['import sox\nsox.Combiner()\nx.build(combine_type="' + x + '")' for x in ('concatenate', 'merge', 'multiply')]
        cases += ['x.' + x + '()' for x in ('overlay','amix','build','filter','filter_','from_file','from_mp3','from_ogg','from_wav','silent','empty','AudioSegment','Combiner')]
        for case in cases:
            with self.subTest(case=case): self.assertFalse(evidence(case))

    def test_findings_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'README.md').write_text('mix audio')
            self.assertEqual(audit(root)['findings'][0]['severity'], 'HIGH')
            (root/'tests').mkdir()
            (root/'tests/test_x.py').write_text('x.mix_audio()')
            self.assertEqual(audit(root)['findings'][0]['severity'], 'MEDIUM')
            self.assertEqual(audit(root, fail_on='medium')['verdict'], 'FAIL')
            (root/'a.py').write_text('from pydub import AudioSegment\nAudioSegment()')
            (root/'b.py').write_text('x.overlay()')
            self.assertEqual(audit(root)['findings'][0]['severity'], 'MEDIUM')
            (root/'a.py').write_text('from pydub import AudioSegment\nAudioSegment()\nx.overlay()')
            self.assertEqual(audit(root)['verdict'], 'PASS')
            (root/'README.md').write_text('does not mix audio')
            self.assertEqual(audit(root)['findings'][0]['rule'], 'documented-no-audio-mixing-claim-false')
            self.assertEqual(audit(root, ignore=['a.py'])['verdict'], 'PASS')

    def test_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, 'README.md').write_text('mix audio')
            result = subprocess.run([sys.executable, '-m', 'audio_mixing_claim_audit', 'audit', temp, '--json'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['findings'][0]['severity'], 'HIGH')
            self.assertEqual(subprocess.run([sys.executable, '-m', 'audio_mixing_claim_audit', 'audit', '--fail-on', 'bad'], capture_output=True).returncode, 1)
            self.assertEqual(subprocess.run([sys.executable, '-m', 'audio_mixing_claim_audit', '--version'], capture_output=True, text=True).stdout.strip(), '0.1.0')

    def test_self_audit(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(audit(root)['verdict'], 'PASS')
        self.assertFalse(any(pattern(AUDIOMIXING).search(p) or pattern(NOAUDIOMIXING).search(p) for p in paragraphs((root/'README.md').read_text())))


if __name__ == '__main__': unittest.main()
