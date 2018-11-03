import numpy as np

from neupy.utils import asfloat
from neupy import architectures

from base import BaseTestCase


class SqueezenetTestCase(BaseTestCase):
    def test_squeezenet_architecture(self):
        squeezenet = architectures.squeezenet()
        self.assertEqual(squeezenet.input_shape, (227, 227, 3))
        self.assertEqual(squeezenet.output_shape, (1000,))

        random_input = asfloat(np.random.random((7, 227, 227, 3)))
        prediction = self.eval(squeezenet.output(random_input))
        self.assertEqual(prediction.shape, (7, 1000))
