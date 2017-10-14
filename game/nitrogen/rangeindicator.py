import math

import panda3d.core as p3d


_SDF_SIZE = 64


def _lin_remap(value, low1, high1, low2, high2):
    return low2 + (value - low1) * (high2 - low2) / (high1 - low1)


def _make_sdf_circle():
    sdfimg = p3d.PNMImage(_SDF_SIZE, _SDF_SIZE)
    maxneg = -math.sqrt(2) + 1

    for imgx in range(_SDF_SIZE):
        normx = (imgx / (_SDF_SIZE - 1)) * 2.0 - 1.0
        for imgy in range(_SDF_SIZE):
            normy = (imgy / (_SDF_SIZE - 1)) * 2.0 - 1.0

            length = normx ** 2 + normy ** 2
            if length < 1.0:
                dist = _lin_remap(1 - length, 0, 1, 0.5, 1)
            else:
                dist = _lin_remap(-length + 1, maxneg, 0, 0, 0.5)

            sdfimg.setXel(imgx, imgy, dist)

    sdftex = p3d.Texture()
    sdftex.load(sdfimg)
    return sdftex


def _make_sdf_box():
    sdfimg = p3d.PNMImage(_SDF_SIZE, _SDF_SIZE)

    for imgx in range(_SDF_SIZE):
        normx = abs((imgx / _SDF_SIZE) * 2.0 - 1.0)
        for imgy in range(_SDF_SIZE):
            normy = abs((imgy / _SDF_SIZE) * 2.0 - 1.0)

            dist = _lin_remap(1 - max(normx, normy), 0, 1, 0.5, 1)
            sdfimg.setXel(imgx, imgy, dist)

    sdftex = p3d.Texture()
    sdftex.load(sdfimg)
    return sdftex


_SDF_CIRCLE = _make_sdf_circle()
_SDF_BOX = _make_sdf_box()


_RI_VERT = """
#version 130
uniform mat4 p3d_ModelViewProjectionMatrix;

in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;

out vec2 texcoord;

void main() {
    texcoord = p3d_MultiTexCoord0;
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
}
"""


_RI_FRAG = """
#version 130
uniform sampler2D sdftex;
uniform vec4 ricolor;
uniform vec4 outline_color;

in vec2 texcoord;

out vec4 o_color;

const float outline_size = 0.05;
const float smoothing = 0.005;

void main() {
    float dist = texture(sdftex, texcoord).r;
    float outline_dist = 0.5 + outline_size;

    float outline_factor = smoothstep(outline_dist - smoothing, outline_dist + smoothing, dist);
    vec4 color = mix(outline_color, ricolor, outline_factor);
    float alpha = smoothstep(0.5 - smoothing, 0.5 + smoothing, dist);

    o_color = vec4(color.rgb, color.a * alpha);
}
"""


_SHADER = p3d.Shader.make(p3d.Shader.SL_GLSL, _RI_VERT, _RI_FRAG)


class RangeIndicator:
    def __init__(self, shape, **kwargs):
        sdftex = None
        frame = p3d.LVector4(-1, 1, -1, 1)
        scale = p3d.LVector3(1, 1, 1)
        offset = p3d.LVector3(0, 0, 0)

        if shape == 'circle':
            sdftex = _SDF_CIRCLE
            scale *= kwargs['radius']
        elif shape == 'box':
            sdftex = _SDF_BOX
            scale = p3d.LVector3(kwargs['width'] / 2.0, 1, kwargs['length'] / 2.0)
            offset = p3d.LVector3(0, kwargs['length'] / 2.0, 0)
        else:
            raise ValueError("Unknown shape for RangeIndicator: {}".format(shape))

        cardmaker = p3d.CardMaker('RI_' + shape)
        cardmaker.set_frame(frame)

        card = p3d.NodePath(cardmaker.generate())
        card.set_p(-90)
        card.set_scale(scale)
        card.set_pos(offset)
        card.set_transparency(p3d.TransparencyAttrib.MAlpha)

        card.set_texture(sdftex)

        card.set_shader(_SHADER)
        card.set_shader_input('sdftex', sdftex)
        card.set_shader_input('ricolor', p3d.LVector4(0.8, 0.0, 0.0, 0.3))
        card.set_shader_input('outline_color', p3d.LVector4(0.0, 0.0, 0.0, 0.8))

        self.graphics = card

    @property
    def visible(self):
        return not self.graphics.is_hidden()

    @visible.setter
    def visible(self, value):
        if value:
            self.graphics.show()
        else:
            self.graphics.hide()
