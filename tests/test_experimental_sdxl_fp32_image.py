import contextlib
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np
from tools import experimental_sdxl_fp32_image as image
from tools import experimental_sdxl_decode_review as review


class Tensor(np.ndarray):
    def detach(self): return self
    def cpu(self): return self
    def numpy(self): return np.asarray(self)


class FP32ImageTests(unittest.TestCase):
    def test_cached_step_then_nineteen_live_pairs_and_twenty_scheduler_updates(self):
        tensor = lambda x: np.asarray(x).view(Tensor)
        initial = np.zeros((1,4,128,128),np.float32)
        first = np.concatenate([initial + 2, initial + 4])
        digest = hashlib.sha256(np.concatenate([initial,initial]).tobytes()).hexdigest()
        updates, scales, records = [], [], {}
        class Scheduler:
            timesteps = list(range(951,0,-50))
            def scale_model_input(self,sample,t):
                scales.append(t)
                return sample
            def step(self,guided,t,latent,return_dict):
                updates.append((t,guided.copy()))
                return (latent + 1,)
        def predict(model,sample,t,pack,torch,on_row):
            on_row('negative',None,0.1); on_row('positive',None,0.1)
            return first
        torch = SimpleNamespace(from_numpy=tensor,cat=lambda values:tensor(np.concatenate(values)))
        with mock.patch.object(image,'SAMPLE_SHA',digest), mock.patch.object(image,'predict_rows',side_effect=predict) as run, \
             contextlib.redirect_stdout(io.StringIO()):
            result=image.denoise(None,Scheduler(),{},initial,first,torch,
                                  lambda k,v:records.update({k:v}),clock=lambda:0)
        self.assertEqual(run.call_count,19)
        self.assertEqual(scales,list(range(951,0,-50)))
        self.assertEqual(len(updates),20)
        np.testing.assert_array_equal(updates[0][1],17)  # 2 + 7.5 * (4 - 2)
        np.testing.assert_array_equal(result,20)
        np.testing.assert_array_equal(initial,0)
        self.assertEqual(records['trajectory.json']['live_forward_calls'],38)

    def test_bad_first_sample_never_advances_scheduler(self):
        tensor=lambda x:np.asarray(x).view(Tensor)
        scheduler=SimpleNamespace(timesteps=list(range(951,0,-50)),
            scale_model_input=lambda x,t:x,step=mock.Mock())
        torch=SimpleNamespace(from_numpy=tensor,cat=lambda x:tensor(np.concatenate(x)))
        with self.assertRaisesRegex(ValueError,'input mismatch'):
            image.denoise(None,scheduler,{},np.zeros((1,4,128,128),np.float32),None,torch,mock.Mock())
        scheduler.step.assert_not_called()

    def test_altered_fp32_checkpoint_stops_before_runtime_import_or_download(self):
        with TemporaryDirectory() as tmp, mock.patch.object(image,'OUT',Path(tmp)), \
             mock.patch.object(image,'sources',side_effect=ValueError('hash mismatch')), \
             mock.patch.object(image,'download_one') as download:
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                image.worker()
            download.assert_not_called()

    def test_invalid_latent_cannot_reach_decoder_import(self):
        with self.assertRaisesRegex(ValueError,'Invalid source latent'):
            image.original_decode(None,np.zeros((1,4,64,64),np.float32),None)

    def test_slow_worker_keeps_memory_cap_and_decode_deadline(self):
        import sys
        process=mock.Mock(pid=123,poll=mock.Mock(side_effect=[None,None,None]),wait=mock.Mock(return_value=-9))
        root=mock.Mock();root.children.return_value=[];root.is_running.return_value=True
        root.memory_info.return_value=SimpleNamespace(rss=review.GIB)
        psutil=SimpleNamespace(Process=lambda _:root,NoSuchProcess=ProcessLookupError)
        with TemporaryDirectory() as tmp:
            out=Path(tmp);(out/'stage.json').write_text('{"stage":"inference"}')
            def enter_decode(_): (out/'stage.json').write_text('{"stage":"decode"}')
            with mock.patch.dict(sys.modules,{'psutil':psutil}), \
                 mock.patch.object(review.subprocess,'Popen',return_value=process), \
                 mock.patch.object(review,'available_memory',return_value=5*review.GIB), \
                 mock.patch.object(review.time,'monotonic',side_effect=[0,10,1000,2410,2411]), \
                 mock.patch.object(review.time,'sleep',side_effect=enter_decode), \
                 mock.patch.object(review.os,'killpg') as kill:
                code,reason,elapsed,peaks=review.run_bounded_worker(out,'example','inference',slow_review=True)
            self.assertEqual(reason,'inference_timeout')
            self.assertEqual(code,-9)
            kill.assert_called_once_with(123,review.signal.SIGKILL)

    def test_image_record_cannot_enable_release(self):
        with TemporaryDirectory() as tmp,mock.patch.object(image,'OUT',Path(tmp)):
            image.save('review.json',{'approved':True,'production_ready':True,'published':True})
            record=json.loads((Path(tmp)/'review.json').read_text())
            self.assertFalse(record['approved']);self.assertFalse(record['production_ready']);self.assertFalse(record['published'])
