from itertools import product
from collections import namedtuple

import numpy as np
import tensorflow as tf

from neupy import layers
from neupy.utils import asfloat, as_tuple
from neupy.layers.convolutions import conv_output_shape
from neupy.exceptions import LayerConnectionError

from base import BaseTestCase


class ConvLayersTestCase(BaseTestCase):
    def get_shape(self, value):
        shape = self.eval(tf.shape(value))
        return tuple(shape)

    def test_convolution_params(self):
        weight_shape = (2, 2, 1, 6)
        bias_shape = (6,)

        input_layer = layers.Input((5, 5, 1))
        conv_layer = layers.Convolution((2, 2, 6))

        self.assertEqual(conv_layer.output_shape, None)

        layers.join(input_layer, conv_layer)
        conv_layer.initialize()

        self.assertEqual(weight_shape, self.get_shape(conv_layer.weight))
        self.assertEqual(bias_shape, self.get_shape(conv_layer.bias))

    def test_conv_shapes(self):
        paddings = ['VALID', 'SAME']
        strides = [(1, 1), (2, 1), (2, 2)]
        x = asfloat(np.random.random((20, 12, 11, 2)))

        for stride, padding in product(strides, paddings):
            input_layer = layers.Input((12, 11, 2))
            conv_layer = layers.Convolution(
                (3, 4, 5), padding=padding, stride=stride)

            layers.join(input_layer, conv_layer)
            conv_layer.initialize()

            y = self.eval(conv_layer.output(x))
            actual_output_shape = as_tuple(y.shape[1:])

            self.assertEqual(
                actual_output_shape, conv_layer.output_shape,
                msg='padding={} and stride={}'.format(padding, stride),
            )

    def test_valid_strides(self):
        Case = namedtuple("Case", "stride expected_output")
        testcases = (
            Case(stride=(4, 4), expected_output=(4, 4)),
            Case(stride=(4,), expected_output=(4, 1)),
            Case(stride=4, expected_output=(4, 4)),
        )

        for testcase in testcases:
            conv_layer = layers.Convolution(
                (2, 3, 1), stride=testcase.stride)

            msg = "Input stride size: {}".format(testcase.stride)
            self.assertEqual(
                testcase.expected_output, conv_layer.stride, msg=msg)

    def test_conv_invalid_strides(self):
        invalid_strides = (
            (4, 4, 4),
            -10,
            (-5, -5),
            (-5, 5),
            (-5, 0),
        )

        for stride in invalid_strides:
            msg = "Input stride size: {}".format(stride)
            with self.assertRaises(ValueError, msg=msg):
                layers.Convolution((2, 3, 1), stride=stride)

    def test_valid_padding(self):
        valid_paddings = ('VALID', 'SAME')
        for padding in valid_paddings:
            layers.Convolution((2, 3, 1), padding=padding)

    def test_invalid_padding(self):
        invalid_paddings = ('invalid mode', -10, (10, -5))

        for padding in invalid_paddings:
            msg = "Padding: {}".format(padding)

            with self.assertRaises(ValueError, msg=msg):
                layers.Convolution((2, 3, 1), padding=padding)

    def test_conv_output_shape_func_exceptions(self):
        with self.assertRaises(ValueError):
            # Wrong stride value
            conv_output_shape(
                dimension_size=5, filter_size=5,
                padding='VALID', stride='not int')

        with self.assertRaises(ValueError):
            # Wrong filter size value
            conv_output_shape(
                dimension_size=5, filter_size='not int',
                padding='SAME', stride=5)

        with self.assertRaisesRegexp(ValueError, "unknown \S+ padding value"):
            # Wrong padding value
            conv_output_shape(
                dimension_size=5, filter_size=5,
                padding=1.5, stride=5,
            )

    def test_conv_output_shape_int_padding(self):
        output_shape = conv_output_shape(
            dimension_size=10,
            padding=3,
            filter_size=5,
            stride=5,
        )
        self.assertEqual(output_shape, 3)

    def test_conv_unknown_dim_size(self):
        shape = conv_output_shape(
            dimension_size=None, filter_size=5,
            padding='VALID', stride=5,
        )
        self.assertEqual(shape, None)

    def test_conv_invalid_padding_exception(self):
        error_msg = "greater or equal to zero"
        with self.assertRaisesRegexp(ValueError, error_msg):
            layers.Convolution((1, 3, 3), padding=-1)

        error_msg = "Tuple .+ greater or equal to zero"
        with self.assertRaisesRegexp(ValueError, error_msg):
            layers.Convolution((1, 3, 3), padding=(2, -1))

        with self.assertRaisesRegexp(ValueError, "invalid string value"):
            layers.Convolution((1, 3, 3), padding='NOT_SAME')

        with self.assertRaisesRegexp(ValueError, "contains two elements"):
            layers.Convolution((1, 3, 3), padding=(3, 3, 3))

    def test_conv_invalid_input_shape(self):
        conv = layers.Convolution((1, 3, 3))

        with self.assertRaises(LayerConnectionError):
            layers.join(layers.Input(10), conv)

    def test_conv_with_custom_int_padding(self):
        input_layer = layers.Input((5, 5, 1))
        conv = layers.Convolution((3, 3, 1), bias=0, weight=1, padding=2)

        connection = input_layer > conv
        connection.initialize()

        x = asfloat(np.ones((1, 5, 5, 1)))
        expected_output = np.array([
            [1, 2, 3, 3, 3, 2, 1],
            [2, 4, 6, 6, 6, 4, 2],
            [3, 6, 9, 9, 9, 6, 3],
            [3, 6, 9, 9, 9, 6, 3],
            [3, 6, 9, 9, 9, 6, 3],
            [2, 4, 6, 6, 6, 4, 2],
            [1, 2, 3, 3, 3, 2, 1],
        ]).reshape((1, 7, 7, 1))

        actual_output = self.eval(connection.output(x))
        np.testing.assert_array_almost_equal(expected_output, actual_output)

    def test_conv_with_custom_tuple_padding(self):
        input_layer = layers.Input((5, 5, 1))
        conv = layers.Convolution((3, 3, 1), bias=0, weight=1, padding=(0, 2))

        connection = input_layer > conv
        connection.initialize()

        x = asfloat(np.ones((1, 5, 5, 1)))
        expected_output = np.array([
            [3, 6, 9, 9, 9, 6, 3],
            [3, 6, 9, 9, 9, 6, 3],
            [3, 6, 9, 9, 9, 6, 3],
        ]).reshape((1, 3, 7, 1))
        actual_output = self.eval(connection.output(x))

        np.testing.assert_array_almost_equal(expected_output, actual_output)
        self.assertEqual(conv.output_shape, (3, 7, 1))

    def test_conv_without_bias(self):
        input_layer = layers.Input((5, 5, 1))
        conv = layers.Convolution((3, 3, 1), bias=None, weight=1)

        connection = input_layer > conv
        connection.initialize()

        x = asfloat(np.ones((1, 5, 5, 1)))
        expected_output = 9 * np.ones((1, 3, 3, 1))
        actual_output = self.eval(connection.output(x))

        np.testing.assert_array_almost_equal(expected_output, actual_output)
