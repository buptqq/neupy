from __future__ import division

import math
import collections

import six
import tensorflow as tf

from neupy.utils import as_tuple
from neupy.exceptions import LayerConnectionError
from neupy.core.properties import TypedListProperty, Property
from .base import ParameterBasedLayer


__all__ = ('Convolution',)


class StrideProperty(TypedListProperty):
    """
    Stride property.

    Parameters
    ----------
    {BaseProperty.Parameters}
    """
    expected_type = (list, tuple, int)

    def __init__(self, *args, **kwargs):
        kwargs['element_type'] = int
        super(StrideProperty, self).__init__(*args, **kwargs)

    def __set__(self, instance, value):
        if isinstance(value, collections.Iterable) and len(value) == 1:
            value = (value[0], 1)

        if isinstance(value, int):
            value = (value, value)

        super(StrideProperty, self).__set__(instance, value)

    def validate(self, value):
        super(StrideProperty, self).validate(value)

        if len(value) > 2:
            raise ValueError("Stide can have only one or two elements "
                             "in the list. Got {}".format(len(value)))

        if any(element <= 0 for element in value):
            raise ValueError(
                "Stride size should contain only values greater than zero")


def conv_output_shape(dimension_size, filter_size, padding, stride):
    """
    Computes convolution's output shape.

    Parameters
    ----------
    dimension_size : int
        Size of the dimension. Typically it's image's
        weight or height.

    filter_size : int
        Size of the convolution filter.

    padding : {``valid``, ``full``, ``half``} or int
        Type or size of the zero-padding.

    stride : int
        Stride size.

    Returns
    -------
    int
        Dimension size after applying convolution
        operation with specified configurations.
    """
    if dimension_size is None:
        return None

    if not isinstance(stride, int):
        raise ValueError("Stride needs to be an integer, got {} (value {!r})"
                         "".format(type(stride), stride))

    if not isinstance(filter_size, int):
        raise ValueError("Filter size needs to be an integer, got {} "
                         "(value {!r})".format(type(filter_size),
                                               filter_size))

    if padding == 'VALID':
        return math.ceil((dimension_size - filter_size + 1) / stride)

    elif padding == 'SAME':
        return math.ceil(dimension_size / stride)

    elif isinstance(padding, int):
        return math.ceil(
            (dimension_size + 2 * padding - filter_size + 1) / stride)

    raise ValueError("`{!r}` is unknown convolution's padding value"
                     "".format(padding))


class PaddingProperty(Property):
    """
    Border mode property identifies border for the
    convolution operation.
    Parameters
    ----------
    {Property.Parameters}
    """
    expected_type = (six.string_types, int, tuple)
    valid_string_choices = ('VALID', 'SAME')

    def __set__(self, instance, value):
        if isinstance(value, int):
            if value < 0:
                raise ValueError(
                    "Integer border mode value needs to be "
                    "greater or equal to zero, got {}".format(value)
                )

            value = (value, value)

        if isinstance(value, six.string_types):
            value = value.upper()

        super(PaddingProperty, self).__set__(instance, value)

    def validate(self, value):
        super(PaddingProperty, self).validate(value)

        if isinstance(value, tuple) and len(value) != 2:
            raise ValueError(
                "Border mode property suppose to get a tuple that "
                "contains two elements, got {} elements"
                "".format(len(value))
            )

        is_invalid_string = (
            isinstance(value, six.string_types) and
            value not in self.valid_string_choices
        )

        if is_invalid_string:
            valid_choices = ', '.join(self.valid_string_choices)
            raise ValueError("`{}` is invalid string value. Available: {}"
                             "".format(value, valid_choices))

        if isinstance(value, tuple) and any(element < 0 for element in value):
            raise ValueError("Tuple border mode value needs to contain "
                             "only elements that greater or equal to zero, "
                             "got {}".format(value))


class Convolution(ParameterBasedLayer):
    """
    Convolutional layer.

    Parameters
    ----------
    size : tuple of int
        Filter shape. In should be defined as a tuple with three
        integers ``(filter rows, filter columns, output channels)``.

    padding : {{``VALID``, ``SAME``}}
        Defaults to ``VALID``.

    stride : tuple with 1 or 2 integers or integer.
        Stride size. Defaults to ``(1, 1)``

    {ParameterBasedLayer.weight}

    {ParameterBasedLayer.bias}

    {BaseLayer.Parameters}

    Examples
    --------
    2D Convolution

    >>> from neupy import layers
    >>>
    >>> layers.join(
    ...     layers.Input((28, 28, 3)),
    ...     layers.Convolution((3, 3, 16)),
    ... )

    1D Convolution

    >>> from neupy import layers
    >>>
    >>> layers.join(
    ...     layers.Input((30, 10)),
    ...     layers.Reshape((30, 1, 10)),
    ...     layers.Convolution((3, 1, 16)),
    ... )

    Methods
    -------
    {ParameterBasedLayer.Methods}

    Attributes
    ----------
    {ParameterBasedLayer.Attributes}
    """
    size = TypedListProperty(required=True, element_type=int)
    padding = PaddingProperty(default='valid')
    stride = StrideProperty(default=(1, 1))

    def validate(self, input_shape):
        if len(input_shape) != 3:
            raise LayerConnectionError(
                "Convolutional layer expects an input with 3 "
                "dimensions, got {} with shape {}"
                "".format(len(input_shape), input_shape))

    @property
    def output_shape(self):
        if self.input_shape is None:
            return None

        padding = self.padding
        rows, cols, _ = self.input_shape
        row_filter_size, col_filter_size, n_kernels = self.size

        row_stride, col_stride = self.stride

        if isinstance(padding, (list, tuple)):
            row_padding, col_padding = padding
        else:
            row_padding, col_padding = padding, padding

        output_rows = conv_output_shape(
            rows, row_filter_size, row_padding, row_stride)

        output_cols = conv_output_shape(
            cols, col_filter_size, col_padding, col_stride)

        # In python 2, we can get float number after rounding procedure
        # and it might break processing in the subsequent layers.
        return (int(output_rows), int(output_cols), n_kernels)

    @property
    def weight_shape(self):
        n_channels = self.input_shape[-1]
        n_rows, n_cols, n_filters = self.size
        return (n_rows, n_cols, n_channels, n_filters)

    @property
    def bias_shape(self):
        return as_tuple(self.size[-1])

    def output(self, input_value):
        padding = self.padding

        if not isinstance(padding, six.string_types):
            height_pad, weight_pad = padding
            input_value = tf.pad(input_value, [
                [0, 0],
                [height_pad, height_pad],
                [weight_pad, weight_pad],
                [0, 0],
            ])
            # We will need to make sure that convolution operation
            # won't add any paddings.
            padding = 'VALID'

        output = tf.nn.convolution(
            input_value,
            self.weight,
            padding,
            self.stride,
            data_format="NHWC"
        )

        if self.bias is not None:
            bias = tf.reshape(self.bias, (1, 1, 1, -1))
            output += bias

        return output
