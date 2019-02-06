from tensorflow.keras.layers import Layer
from tensorflow.keras.layers import InputSpec
from tensorflow.keras.utils import get_custom_objects
from tensorflow.keras import initializers
from tensorflow.keras import backend as K
from tensorflow.python.framework import tensor_shape


class SReLU(Layer):
    """S-shaped Rectified Linear Unit.
    It follows:
    `f(x) = t^r + a^r(x - t^r) for x >= t^r`,
    `f(x) = x for t^r > x > t^l`,
    `f(x) = t^l + a^l(x - t^l) for x <= t^l`.
    # Input shape
        Arbitrary. Use the keyword argument `input_shape`
        (tuple of integers, does not include the samples axis)
        when using this layer as the first layer in a model.
    # Output shape
        Same shape as the input.
    # Arguments
        t_left_initializer: initializer function for the left part intercept
        a_left_initializer: initializer function for the left part slope
        t_right_initializer: initializer function for the right part intercept
        a_right_initializer: initializer function for the right part slope
        shared_axes: the axes along which to share learnable
            parameters for the activation function.
            For example, if the incoming feature maps
            are from a 2D convolution
            with output shape `(batch, height, width, channels)`,
            and you wish to share parameters across space
            so that each filter only has one set of parameters,
            set `shared_axes=[1, 2]`.
    # References
        - [Deep Learning with S-shaped Rectified Linear Activation Units](
           http://arxiv.org/abs/1512.07030)
    """

    def __init__(self, t_left_initializer='zeros',
                 a_left_initializer=initializers.RandomUniform(minval=0, maxval=1),
                 t_right_initializer=initializers.RandomUniform(minval=0, maxval=5),
                 a_right_initializer='ones',
                 shared_axes=None,
                 **kwargs):
        super(SReLU, self).__init__(**kwargs)
        self.supports_masking = True
        self.t_left_initializer = initializers.get(t_left_initializer)
        self.a_left_initializer = initializers.get(a_left_initializer)
        self.t_right_initializer = initializers.get(t_right_initializer)
        self.a_right_initializer = initializers.get(a_right_initializer)
        if shared_axes is None:
            self.shared_axes = None
        elif not isinstance(shared_axes, (list, tuple)):
            self.shared_axes = [shared_axes]
        else:
            self.shared_axes = list(shared_axes)

    def build(self, input_shape):
        param_shape = input_shape[1:].as_list()
        self.param_broadcast = [False] * len(param_shape)
        if self.shared_axes is not None:
            for i in self.shared_axes:
                param_shape[i - 1] = 1
                self.param_broadcast[i - 1] = True

        param_shape = tuple(param_shape)

        self.t_left = self.add_weight(shape=param_shape,
                                      name='t_left',
                                      initializer=self.t_left_initializer)

        self.a_left = self.add_weight(shape=param_shape,
                                      name='a_left',
                                      initializer=self.a_left_initializer)

        self.t_right = self.add_weight(shape=param_shape,
                                       name='t_right',
                                       initializer=self.t_right_initializer)

        self.a_right = self.add_weight(shape=param_shape,
                                       name='a_right',
                                       initializer=self.a_right_initializer)

        # Set input spec
        axes = {}
        if self.shared_axes:
            for i in range(1, len(input_shape)):
                if i not in self.shared_axes:
                    axes[i] = input_shape[i]
        self.input_spec = InputSpec(ndim=len(input_shape), axes=axes)
        self.built = True

    def call(self, x, mask=None):
        # ensure the the right part is always to the right of the left
        t_right_actual = self.t_left + K.abs(self.t_right)

        t_left = self.t_left
        a_left = self.a_left
        a_right = self.a_right

        y_left_and_center = t_left + K.relu(x - t_left,
                                            a_left,
                                            t_right_actual - t_left)
        y_right = K.relu(x - t_right_actual) * a_right
        return y_left_and_center + y_right

    def get_config(self):
        config = {
            't_left_initializer': self.t_left_initializer,
            'a_left_initializer': self.a_left_initializer,
            't_right_initializer': self.t_right_initializer,
            'a_right_initializer': self.a_right_initializer,
            'shared_axes': self.shared_axes
        }
        base_config = super(SReLU, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))

get_custom_objects().update({'SReLU': SReLU})