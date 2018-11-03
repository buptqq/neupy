import numpy as np

from neupy import plots, layers
from neupy.exceptions import InvalidConnection

from base import BaseTestCase


class SaliencyMapTestCase(BaseTestCase):
    single_thread = True

    def test_invalid_arguments_exceptions(self):
        network = layers.join(
            layers.Input((28, 28, 3)),
            layers.Convolution((3, 3, 8), name='conv') > layers.Relu(),
            layers.Reshape(),
            layers.Softmax(10),
        )
        image = np.ones((28, 28, 3))

        with self.assertRaisesRegexp(ValueError, 'Invalid image shape'):
            plots.saliency_map(network, np.ones((28, 28)))

        with self.assertRaisesRegexp(ValueError, 'invalid value'):
            plots.saliency_map(network, image, mode='invalid-mode')

        with self.assertRaises(InvalidConnection):
            new_network = network > [
                layers.Sigmoid(1), layers.Sigmoid(2)
            ]
            plots.saliency_map(new_network, image)

        with self.assertRaises(InvalidConnection):
            new_network = [
                layers.Input((28, 28, 3)), layers.Input((28, 28, 3))
            ] > network.start('conv')
            plots.saliency_map(new_network, image)

        with self.assertRaisesRegexp(InvalidConnection, 'invalid input shape'):
            plots.saliency_map(layers.Input(10) > layers.Relu(), image)
